import logging
from typing import ClassVar

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


class Authenticator:
    """
    Handles authentication to the CRM system.

    Manages login process including form filling and verification.
    """

    # Selectors discovered via automated inspection
    SELECTORS: ClassVar[dict[str, str]] = {
        "username_field": 'input[placeholder*="Login" i]',  # Login field with placeholder
        "password_field": 'input[type="password"]',  # Password field
        "submit_button": 'button:has-text("Login")',  # Login button
        "logged_in_indicator": 'a[href*="/activities"]',  # Activities link visible when logged in
    }

    def __init__(self, page: Page, login: str, password: str, logger: logging.Logger):
        """
        Initialize authenticator.

        Args:
            page: Playwright Page object
            login: Login username/email
            password: Login password
            logger: Logger instance
        """
        self.page = page
        self._login = login
        self.password = password
        self.logger = logger

    async def login(self, accounts_url: str, timeout: int = 60000) -> bool:
        """
        Perform login to CRM system.

        Args:
            accounts_url: URL of the login/accounts page
            timeout: Timeout for login operations in milliseconds

        Returns:
            True if login successful, False otherwise
        """
        try:
            self.logger.info(f"Navigating to login page: {accounts_url}")
            await self.page.goto(accounts_url, wait_until="domcontentloaded", timeout=timeout)

            # Check if already logged in
            if await self.is_logged_in():
                self.logger.info("Already logged in")
                return True

            self.logger.debug("Waiting for login form")
            # Wait for username field to appear
            await self.page.wait_for_selector(
                self.SELECTORS["username_field"], state="visible", timeout=timeout
            )

            self.logger.debug("Filling username field")
            await self.page.fill(self.SELECTORS["username_field"], self._login)

            self.logger.debug("Filling password field")
            await self.page.fill(self.SELECTORS["password_field"], self.password)

            self.logger.debug("Clicking submit button")
            # Click submit and wait for navigation
            await self.page.click(self.SELECTORS["submit_button"])

            # Wait for page to load (use domcontentloaded instead of networkidle to avoid timeouts)
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            await self.page.wait_for_timeout(3000)  # Brief wait for page to settle

            if await self.is_logged_in():
                self.logger.info("Login successful")
                return True
            else:
                self.logger.error("Login failed: Unable to verify login status")
                return False

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Login timeout error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Login error: {e}", exc_info=True)
            return False

    async def is_logged_in(self) -> bool:
        """
        Check if user is already logged in.

        Returns:
            True if logged in, False otherwise
        """
        try:
            # Check for element that only appears when logged in
            element = self.page.locator(self.SELECTORS["logged_in_indicator"])
            return await element.count() > 0
        except Exception:
            return False

    async def logout(self, logout_url: str | None = None) -> bool:
        """
        Perform logout (optional functionality).

        Args:
            logout_url: URL of the logout endpoint

        Returns:
            True if logout successful
        """
        try:
            if logout_url:
                await self.page.goto(logout_url)
                self.logger.info("Logged out successfully")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return False
