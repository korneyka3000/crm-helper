import logging
from typing import Optional
from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

from src.date_distributor import DateDistributor
from src.models.user import UserResult


class UserProcessor:
    """
    Processes individual users and their planned activities.

    Handles opening user details, finding planned activities,
    marking them as HELD, copying them with new dates.
    """

    # TODO: Update these selectors using playwright codegen
    # Run: playwright codegen https://mysigma.support/activities/
    SELECTORS = {
        # User selection
        "user_row": 'tr.user-row, .user-item, [data-user-row]',

        # Activities table
        "activities_table": 'table.activities, .activities-table, #activities-table',
        "activity_row": 'tr.activity-row, tbody tr',
        "status_column": 'td.status, td[data-column="status"]',
        "status_planned": 'td:has-text("Planned")',

        # Action buttons in activity row
        "mark_held_button": 'button.mark-held, .checkmark-green, button[title="Mark as HELD"]',
        "copy_button": 'button.copy, button:has-text("Copy"), button[title="Copy"]',

        # Modal selectors
        "modal": '.modal, .dialog, [role="dialog"]',
        "modal_description_field": 'input[name="description"], textarea[name="description"], #description',
        "modal_start_field": 'input[name="start"], input[name="start_date"], #start',
        "modal_save_button": 'button:has-text("Save"), button.save, button[type="submit"]',
        "modal_close_button": 'button.close, button[aria-label="Close"], .modal-close',

        # Detail window/modal (if user details open in a modal)
        "detail_window": '.detail-modal, .user-detail, [data-detail-modal]',
        "detail_close_button": 'button.close-detail, button[aria-label="Close detail"]',
    }

    def __init__(
        self,
        page: Page,
        date_distributor: DateDistributor,
        logger: logging.Logger,
        timeout_default: int = 30000,
        timeout_modal: int = 10000,
    ):
        """
        Initialize UserProcessor.

        Args:
            page: Playwright Page object
            date_distributor: DateDistributor for assigning dates
            logger: Logger instance
            timeout_default: Default timeout in milliseconds
            timeout_modal: Modal timeout in milliseconds
        """
        self.page = page
        self.date_distributor = date_distributor
        self.logger = logger
        self.timeout_default = timeout_default
        self.timeout_modal = timeout_modal

    async def process_user(self, user_index: int) -> UserResult:
        """
        Process a single user by clicking on them and handling their activities.

        Args:
            user_index: Zero-based index of the user in the list

        Returns:
            UserResult with processing details
        """
        result = UserResult(user_index=user_index)

        try:
            self.logger.info(f"Processing user at index {user_index}")

            # Click on user to open detail view
            await self._open_user_detail(user_index)

            # Brief wait for detail to load
            await self.page.wait_for_timeout(2000)

            # Process planned activities
            activities_count = await self._process_planned_activities()

            result.activities_processed = activities_count
            result.has_planned_activities = activities_count > 0
            result.success = True

            self.logger.info(
                f"User {user_index}: Processed {activities_count} planned activities"
            )

        except Exception as e:
            self.logger.error(f"Error processing user {user_index}: {e}", exc_info=True)
            result.success = False
            result.error_message = str(e)

        finally:
            # Try to close detail window if open
            try:
                await self._close_user_detail()
            except Exception as e:
                self.logger.debug(f"Could not close user detail: {e}")

        return result

    async def _open_user_detail(self, user_index: int) -> None:
        """
        Click on user row to open detail view.

        Args:
            user_index: Index of the user
        """
        try:
            user_rows = self.page.locator(self.SELECTORS["user_row"])
            user_row = user_rows.nth(user_index)

            self.logger.debug(f"Clicking user row at index {user_index}")
            await user_row.click()

            # Wait for detail window or activities table to appear
            await self.page.wait_for_timeout(1000)

        except Exception as e:
            self.logger.error(f"Error opening user detail: {e}")
            raise

    async def _close_user_detail(self) -> None:
        """Close user detail window/modal if it exists."""
        try:
            close_button = self.page.locator(self.SELECTORS["detail_close_button"])
            if await close_button.count() > 0:
                await close_button.first.click()
                await self.page.wait_for_timeout(500)

        except Exception as e:
            self.logger.debug(f"Detail close error (may not exist): {e}")

    async def _process_planned_activities(self) -> int:
        """
        Find and process all activities with "Planned" status.

        Returns:
            Number of activities processed
        """
        processed_count = 0

        try:
            # Find all activity rows with "Planned" status
            # This is tricky - we need to find rows that contain "Planned" in status column
            activity_rows = self.page.locator(self.SELECTORS["activity_row"])
            total_rows = await activity_rows.count()

            self.logger.debug(f"Found {total_rows} activity rows")

            for i in range(total_rows):
                try:
                    row = activity_rows.nth(i)

                    # Check if this row has "Planned" status
                    status_text = await row.locator(self.SELECTORS["status_column"]).text_content()

                    if status_text and "Planned" in status_text:
                        self.logger.debug(f"Found Planned activity at row {i}")

                        # Process this planned activity
                        if await self._process_single_activity(row):
                            processed_count += 1

                        # Wait a bit between activities
                        await self.page.wait_for_timeout(1000)

                except Exception as e:
                    self.logger.warning(f"Error processing activity row {i}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error in _process_planned_activities: {e}")

        return processed_count

    async def _process_single_activity(self, activity_row: Locator) -> bool:
        """
        Process a single planned activity: Mark as HELD and Copy.

        Args:
            activity_row: Locator for the activity row

        Returns:
            True if successfully processed, False otherwise
        """
        try:
            # Step 1: Click "Mark as HELD" button (green checkmark)
            self.logger.debug("Clicking Mark as HELD button")
            mark_held_button = activity_row.locator(self.SELECTORS["mark_held_button"]).first
            await mark_held_button.click()

            # Wait for status to change
            await self.page.wait_for_timeout(2000)

            # Step 2: Click "Copy" button
            self.logger.debug("Clicking Copy button")
            copy_button = activity_row.locator(self.SELECTORS["copy_button"]).first
            await copy_button.click()

            # Step 3: Wait for modal to appear
            await self.page.wait_for_selector(
                self.SELECTORS["modal"],
                state="visible",
                timeout=self.timeout_modal
            )

            # Step 4: Fill the copy modal form
            await self._fill_copy_modal()

            return True

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout processing activity: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error processing activity: {e}", exc_info=True)
            return False

    async def _fill_copy_modal(self) -> None:
        """Fill the copy modal form with description and date, then save."""
        try:
            self.logger.debug("Filling copy modal form")

            # Fill Description field with "!!!"
            description_field = self.page.locator(self.SELECTORS["modal_description_field"])
            await description_field.fill("!!!")
            self.logger.debug("Filled description: !!!")

            # Get next date from distributor
            next_date = self.date_distributor.get_next_date()
            self.logger.debug(f"Assigning date: {next_date}")

            # Fill Start date field
            start_field = self.page.locator(self.SELECTORS["modal_start_field"])
            await start_field.fill(next_date)

            # Wait a moment for form to process
            await self.page.wait_for_timeout(500)

            # Click Save button
            self.logger.debug("Clicking Save button")
            save_button = self.page.locator(self.SELECTORS["modal_save_button"])
            await save_button.click()

            # Wait for modal to close
            await self.page.wait_for_selector(
                self.SELECTORS["modal"],
                state="hidden",
                timeout=self.timeout_modal
            )

            self.logger.debug("Modal closed successfully")

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout filling modal: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error filling modal: {e}", exc_info=True)
            raise
