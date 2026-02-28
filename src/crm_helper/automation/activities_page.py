import logging
from typing import ClassVar

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class ActivitiesPage:
    """
    Handles navigation and interaction with the Activities page.

    Manages user list, pagination, and page reloading.
    """

    # Updated selectors based on inspection of https://mysigma.support/activities/
    SELECTORS: ClassVar[dict[str, str]] = {
        "user_row": '#activity-table-false tbody tr:not(:has-text("Loading"))',
        "user_list_container": "#activity-table-false",
        "next_page_button": (
            'li.pagination__item:not(.disabled) a:has-text("Next"),'
            ' a.pagination__link:has-text("Next")'
        ),
        "pagination_info": ".pagination-info, .page-info",
        "loading_indicator": ".loading, .spinner, [data-loading]",
    }

    def __init__(self, page: Page, logger: logging.Logger):
        """
        Initialize ActivitiesPage.

        Args:
            page: Playwright Page object
            logger: Logger instance
        """
        self.page = page
        self.logger = logger

    async def navigate(self, activities_url: str, timeout: int = 60000) -> None:
        """
        Navigate to the activities page.

        Args:
            activities_url: URL of the activities page
            timeout: Navigation timeout in milliseconds
        """
        try:
            self.logger.info(f"Navigating to activities page: {activities_url}")
            await self.page.goto(activities_url, wait_until="domcontentloaded", timeout=timeout)

            # Wait for user list to load
            await self.page.wait_for_selector(
                self.SELECTORS["user_row"], state="visible", timeout=timeout
            )
            await self.page.wait_for_timeout(1000)
            self.logger.info("Activities page loaded successfully")

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout navigating to activities page: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error navigating to activities page: {e}", exc_info=True)
            raise

    async def get_user_count(self) -> int:
        """
        Get the number of users on the current page.

        Returns:
            Number of user rows visible on the page
        """
        try:
            user_rows = self.page.locator(self.SELECTORS["user_row"])
            count = await user_rows.count()

            # If 0, maybe it's still loading? Wait a bit and try again
            if count == 0:
                self.logger.debug("0 users found, waiting 2s to double check...")
                await self.page.wait_for_timeout(2000)
                count = await user_rows.count()

            self.logger.debug(f"Found {count} users on current page")
            return count

        except Exception as e:
            self.logger.error(f"Error counting users: {e}")
            return 0

    async def has_next_page(self) -> bool:
        """
        Check if there is a next page available.

        Returns:
            True if next page button exists and is enabled, False otherwise
        """
        try:
            next_button = self.page.locator(self.SELECTORS["next_page_button"])
            count = await next_button.count()

            if count == 0:
                self.logger.debug("No next page button found")
                return False

            # Check if button is disabled
            is_disabled = await next_button.is_disabled()
            has_next = not is_disabled

            self.logger.debug(f"Next page available: {has_next}")
            return has_next

        except Exception as e:
            self.logger.error(f"Error checking for next page: {e}")
            return False

    async def go_to_next_page(self, timeout: int = 30000) -> bool:
        """
        Navigate to the next page.

        Args:
            timeout: Timeout for navigation in milliseconds

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            if not await self.has_next_page():
                self.logger.warning("Attempted to go to next page, but no next page available")
                return False

            self.logger.info("Navigating to next page")
            next_button = self.page.locator(self.SELECTORS["next_page_button"]).first

            # Click and wait for navigation
            await next_button.click()

            # Wait for page to update (use simple timeout instead of networkidle which can hang)
            # 5 seconds is usually enough for AJAX pagination
            await self.page.wait_for_timeout(3000)

            # Wait for rows to be present
            try:
                await self.page.wait_for_selector(
                    self.SELECTORS["user_row"], state="visible", timeout=10000
                )
            except Exception:
                self.logger.warning(
                    "Waited for next page rows but they didn't appear (might be empty page)"
                )

            self.logger.info("Successfully navigated to next page")
            return True

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout going to next page: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error going to next page: {e}", exc_info=True)
            return False

    async def reload(self, timeout: int = 30000) -> None:
        """
        Reload the current page and wait for content to load.

        Args:
            timeout: Timeout for reload in milliseconds
        """
        try:
            self.logger.debug("Reloading page")
            await self.page.reload(wait_until="networkidle", timeout=timeout)

            # Wait for user list to be visible again
            await self.page.wait_for_selector(
                self.SELECTORS["user_row"], state="visible", timeout=timeout
            )

            self.logger.debug("Page reloaded successfully")

        except PlaywrightTimeoutError as e:
            self.logger.warning(f"Timeout during page reload: {e}")
        except Exception as e:
            self.logger.error(f"Error reloading page: {e}", exc_info=True)

    async def get_user_at_index(self, index: int):
        """
        Get user element at specific index.

        Args:
            index: Zero-based index of the user

        Returns:
            Locator for the user row
        """
        try:
            user_rows = self.page.locator(self.SELECTORS["user_row"])
            return user_rows.nth(index)

        except Exception as e:
            self.logger.error(f"Error getting user at index {index}: {e}")
            return None
