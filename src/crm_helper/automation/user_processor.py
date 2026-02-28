import logging
from typing import ClassVar

from playwright.async_api import Locator, Page

from crm_helper.date_distributor import DateDistributor
from crm_helper.models.user import UserResult


class UserProcessor:
    """
    Processes individual activities directly from the Activities list.
    If action buttons are missing, falls back to opening details.
    """

    SELECTORS: ClassVar[dict[str, str]] = {
        # Status (in Activities List)
        # Column 11 (index 10) in the dump was Status
        # But let's be safe and use title="PLANNED"
        "status_planned": 'span[title="PLANNED"]',
        # Action buttons in the row
        "mark_held_button": 'a[title="Mark as HELD"]',
        "copy_button": 'a[title="Copy"]',
        # Fallback: Links to details
        # We prefer Leads link, then Accounts link
        "lead_link": 'a[href*="/leads/details/"]',
        "account_link": 'a[href*="/accounts/details/"]',
        # Modal selectors (same as before)
        "modal": '.modal:visible, [role="dialog"]:visible',
        # Inputs don't have names, so we use structural selectors
        "modal_description_field": "textarea.form-control",  # The only textarea in the modal
        "modal_start_field": ".datepicker-div input",  # Input inside datepicker
        "modal_save_button": 'button:has-text("Save")',
        "modal_close_button": "button.close",
        # Details Page Selectors (Fallback)
        "details_activities_table": 'table:has(th:has-text("Title")):has(th:has-text("Status"))',
        "details_status_column": "td:nth-child(9)",
    }

    def __init__(
        self,
        page: Page,
        date_distributor: DateDistributor,
        logger: logging.Logger,
        timeout_default: int = 30000,
        timeout_modal: int = 10000,
    ):
        self.page = page
        self.date_distributor = date_distributor
        self.logger = logger
        self.timeout_default = timeout_default
        self.timeout_modal = timeout_modal

    async def process_user(self, row_index: int) -> UserResult:
        """
        Process a single activity row from the main list.
        """
        result = UserResult(user_index=row_index)

        try:
            # Check for any lingering modals from previous errors and close them
            await self._ensure_modal_closed()

            # Get the row directly by position — O(1) vs O(n) with :not(:has-text) filter
            row = self.page.locator(f"#activity-table-false tbody tr:nth-child({row_index + 1})")

            # Check Status
            # We look for the span with title="PLANNED" anywhere in the row
            planned_indicator = row.locator(self.SELECTORS["status_planned"])

            if await planned_indicator.count() == 0:
                result.has_planned_activities = False
                self.logger.info(f"Row {row_index}: Not PLANNED (Skip)")
                return result

            result.has_planned_activities = True
            self.logger.info(f"Row {row_index}: Found PLANNED activity")

            # Try to process directly in the list
            if await self._process_in_list(row):
                result.activities_processed = 1
                result.success = True
                self.logger.info(f"Row {row_index}: Successfully processed in list")
            else:
                # Fallback: Open details
                self.logger.info(f"Row {row_index}: Action buttons missing, opening details...")
                if await self._process_via_details(row):
                    result.activities_processed = 1
                    result.success = True
                    self.logger.info(f"Row {row_index}: Successfully processed via details")
                else:
                    result.success = False
                    result.error_message = "Failed to process in list and via details"

        except Exception as e:
            self.logger.error(f"Error processing row {row_index}: {e}", exc_info=True)
            result.success = False
            result.error_message = str(e)

            # Attempt recovery
            await self._ensure_modal_closed()

        return result

    async def _ensure_modal_closed(self):
        """Force close any visible modal to prevent blocking."""
        try:
            modal = self.page.locator(self.SELECTORS["modal"])
            if await modal.count() > 0 and await modal.is_visible():
                self.logger.warning("Found stuck modal, forcing close...")

                # Try Cancel button first (often safer)
                cancel_btn = modal.locator('button:has-text("Cancel")')
                if await cancel_btn.count() > 0 and await cancel_btn.is_visible():
                    await cancel_btn.click()
                else:
                    # Try Close (X) button
                    close_btn = modal.locator(self.SELECTORS["modal_close_button"]).first
                    if await close_btn.count() > 0 and await close_btn.is_visible():
                        await close_btn.click()
                    else:
                        # Last resort: Escape key
                        await self.page.keyboard.press("Escape")

                # Wait for it to disappear
                try:
                    await self.page.wait_for_selector(
                        self.SELECTORS["modal"], state="hidden", timeout=2000
                    )
                except Exception:
                    self.logger.error("Modal refused to close")
        except Exception as e:
            self.logger.debug(f"Error closing modal: {e}")

    async def _process_in_list(self, row: Locator) -> bool:
        """Try to click buttons directly in the row."""
        try:
            # Check for buttons
            held_btn = row.locator(self.SELECTORS["mark_held_button"]).first
            copy_btn = row.locator(self.SELECTORS["copy_button"]).first

            if await held_btn.count() == 0 or await copy_btn.count() == 0:
                return False

            # Click buttons
            self.logger.debug("Clicking Mark as HELD (List)")
            await held_btn.click()
            # Reduce wait from 1000 to 200, or remove if confident
            await self.page.wait_for_timeout(200)

            self.logger.debug("Clicking Copy (List)")
            await copy_btn.click()

            # Handle Modal
            await self._handle_modal()
            return True

        except Exception as e:
            self.logger.warning(f"Failed to process in list: {e}")
            return False

    async def _process_via_details(self, row: Locator) -> bool:
        """Open details page and process there."""
        try:
            # Find link to details
            # Priority: Lead Link > Account Link
            lead_link = row.locator(self.SELECTORS["lead_link"]).first
            account_link = row.locator(self.SELECTORS["account_link"]).first

            target_link = None
            if await lead_link.count() > 0:
                target_link = lead_link
            elif await account_link.count() > 0:
                target_link = account_link

            if not target_link:
                self.logger.error("No details link found")
                return False

            # Click and wait for navigation
            self.logger.info("Navigating to details...")
            await target_link.click()
            await self.page.wait_for_load_state("domcontentloaded")
            # Reduced from 3000 to 1000
            await self.page.wait_for_timeout(1000)

            # Find the activity in the details table
            # NOTE: This is tricky because we need to find the SAME activity.
            # For now, let's just find ANY Planned activity in the details table

            table = self.page.locator(self.SELECTORS["details_activities_table"])
            if await table.count() == 0:
                self.logger.warning("No activities table in details")
                await self.page.go_back()
                return False

            # Find Planned row
            planned_row = (
                table.locator("tbody tr")
                .filter(has=self.page.locator(self.SELECTORS["status_planned"]))
                .first
            )

            if await planned_row.count() == 0:
                self.logger.warning("No PLANNED activity found in details table")
                await self.page.go_back()
                return False

            # Process it
            held_btn = planned_row.locator(self.SELECTORS["mark_held_button"]).first
            copy_btn = planned_row.locator(self.SELECTORS["copy_button"]).first

            await held_btn.click()
            await self.page.wait_for_timeout(200)  # Reduced from 1000
            await copy_btn.click()

            await self._handle_modal()

            # Go back
            await self.page.go_back()
            await self.page.wait_for_load_state("domcontentloaded")
            return True

        except Exception as e:
            self.logger.error(f"Error via details: {e}")
            # Ensure we go back if stuck
            if "details" in self.page.url:
                await self.page.go_back()
            return False

    async def _handle_modal(self) -> None:
        """Handle the Copy Modal."""
        self.logger.debug("Waiting for modal...")
        modal = self.page.locator(self.SELECTORS["modal"])
        await modal.wait_for(state="visible", timeout=self.timeout_modal)

        # Fill Form - Scope locators to the modal
        await modal.locator(self.SELECTORS["modal_description_field"]).fill("!!!")

        next_date = self.date_distributor.get_next_date()
        # Use first datepicker in the modal (Start Date)
        await modal.locator(self.SELECTORS["modal_start_field"]).first.fill(next_date)

        await modal.locator(self.SELECTORS["modal_save_button"]).click()

        await modal.wait_for(state="hidden", timeout=self.timeout_modal)
        self.logger.info(f"Copied activity to {next_date}")
