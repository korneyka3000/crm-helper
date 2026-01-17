import asyncio
import json
import time
from datetime import datetime

from src.config import Config
from src.logger import setup_logger
from src.date_distributor import DateDistributor
from src.models.user import UserResult, ProcessingReport
from src.automation.browser import BrowserManager
from src.automation.auth import Authenticator
from src.automation.activities_page import ActivitiesPage
from src.automation.user_processor import UserProcessor


async def main():
    """Main execution flow for CRM Helper automation."""

    start_time = time.time()

    # 1. Load configuration
    print("Loading configuration...")
    config = Config()
    config.ensure_directories()

    # 2. Setup logger
    logger = setup_logger(config.log_dir, config.log_level)
    logger.info("=" * 60)
    logger.info("CRM Helper - Starting automation")
    logger.info("=" * 60)

    # 3. Initialize date distributor
    logger.info(f"Date range: {config.start_date} to {config.end_date}")
    date_distributor = DateDistributor(config.start_date, config.end_date)
    logger.info(f"Available weekdays: {date_distributor.get_weekday_count()}")

    # 4. Initialize browser
    browser_mgr = BrowserManager()
    processed_users = []

    try:
        # Initialize browser with config settings
        page = await browser_mgr.initialize(
            headless=config.headless,
            timeout_default=config.timeout_default,
            timeout_navigation=config.timeout_navigation,
        )

        logger.info(f"Browser initialized (headless={config.headless})")

        # 5. Authenticate
        auth = Authenticator(page, config.login, config.password, logger)

        if not await auth.login(config.accounts_url):
            logger.critical("Login failed - aborting execution")
            return

        logger.info("Authentication successful")
        # exit(0)
        # 6. Navigate to activities page
        activities_page = ActivitiesPage(page, logger)
        await activities_page.navigate(config.activities_url)

        # 7. Initialize user processor
        user_processor = UserProcessor(
            page=page,
            date_distributor=date_distributor,
            logger=logger,
            timeout_default=config.timeout_default,
            timeout_modal=config.timeout_modal,
        )

        # 8. Process all users across all pages
        page_num = 1

        while True:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing page {page_num}")
            logger.info(f"{'=' * 60}")

            # Get user count on current page
            user_count = await activities_page.get_user_count()
            logger.info(f"Found {user_count} users on page {page_num}")

            if user_count == 0:
                logger.warning("No users found on page - stopping")
                break

            # Process each user on current page
            for user_idx in range(user_count):
                try:
                    logger.info(f"\nProcessing user {user_idx + 1}/{user_count} on page {page_num}")

                    result = await user_processor.process_user(user_idx)
                    processed_users.append(result)

                    if result.success:
                        if result.has_planned_activities:
                            logger.info(
                                f"✓ User {user_idx}: {result.activities_processed} activities processed"
                            )
                        else:
                            logger.info(f"○ User {user_idx}: No planned activities")
                    else:
                        logger.error(f"✗ User {user_idx}: Failed - {result.error_message}")

                except Exception as e:
                    logger.error(
                        f"✗ User {user_idx} on page {page_num}: Unexpected error - {e}",
                        exc_info=True,
                    )
                    processed_users.append(
                        UserResult(user_index=user_idx, success=False, error_message=str(e))
                    )

                finally:
                    # Do not reload page if successful, as it might shift rows
                    # Only reload if we encountered a major error or need to refresh state
                    # But for list processing, static page is better
                    pass

            # Check for next page
            has_next = await activities_page.has_next_page()

            if has_next:
                logger.info(f"\nNavigating to page {page_num + 1}...")
                if await activities_page.go_to_next_page():
                    page_num += 1
                else:
                    logger.warning("Failed to navigate to next page - stopping")
                    break
            else:
                logger.info("\nNo more pages to process")
                break

        # 9. Generate reports
        logger.info(f"\n{'=' * 60}")
        logger.info("Generating reports...")
        logger.info(f"{'=' * 60}")

        execution_time = time.time() - start_time

        # Find users without planned activities
        users_without_planned = [
            {"user_index": u.user_index}
            for u in processed_users
            if not u.has_planned_activities and u.success
        ]

        # Collect errors
        errors = [
            {"user_index": u.user_index, "message": u.error_message}
            for u in processed_users
            if not u.success and u.error_message
        ]

        # Create processing report
        report = ProcessingReport(
            total_users=len(processed_users),
            successful_users=sum(1 for u in processed_users if u.success),
            failed_users=sum(1 for u in processed_users if not u.success),
            users_without_planned=[u["user_index"] for u in users_without_planned],
            total_activities_processed=sum(u.activities_processed for u in processed_users),
            errors=errors,
            execution_time=execution_time,
        )

        # Save users without planned activities to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = config.output_dir / f"users_without_planned_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(users_without_planned, f, indent=2, ensure_ascii=False)

        logger.info(f"Users without planned activities saved to: {output_file}")

        # Save full report
        report_file = config.output_dir / f"processing_report_{timestamp}.json"
        report.save_to_json(report_file)
        logger.info(f"Processing report saved to: {report_file}")

        # Print summary
        print(report.print_summary())
        logger.info("\nAutomation completed successfully")

    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        raise

    finally:
        # 10. Cleanup
        logger.info("\nClosing browser...")
        await browser_mgr.close()
        logger.info("Browser closed")

        execution_time = time.time() - start_time
        logger.info(
            f"\nTotal execution time: {execution_time:.2f}s ({execution_time / 60:.2f} minutes)"
        )
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
