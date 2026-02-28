from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


class BrowserManager:
    """
    Context manager for Playwright browser lifecycle.

    Handles initialization, configuration, and cleanup of browser resources.
    """

    def __init__(self):
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "BrowserManager":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager and cleanup resources."""
        await self.close()

    async def initialize(
        self,
        headless: bool = True,
        timeout_default: int = 30000,
        timeout_navigation: int = 60000,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
    ) -> Page:
        """
        Initialize Playwright browser and create page.

        Args:
            headless: Run browser in headless mode
            timeout_default: Default timeout in milliseconds
            timeout_navigation: Navigation timeout in milliseconds
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height

        Returns:
            Configured Page object
        """
        # Start Playwright
        self.playwright = await async_playwright().start()

        # Launch browser (Chromium)
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],  # Less detectable
        )

        # Create browser context with custom viewport
        self.context = await self.browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Set default timeouts
        self.context.set_default_timeout(timeout_default)
        self.context.set_default_navigation_timeout(timeout_navigation)

        # Create new page
        self.page = await self.context.new_page()

        return self.page

    async def close(self) -> None:
        """Close all browser resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def get_page(self) -> Page:
        """
        Get the current page instance.

        Returns:
            Page object

        Raises:
            RuntimeError: If page is not initialized
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call initialize() first.")
        return self.page
