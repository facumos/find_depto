"""
Shared browser manager for Playwright-based scrapers.
Reuses a single browser instance to reduce memory usage.
Runs Playwright in a separate thread to avoid asyncio conflicts.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)

# Global browser instance (managed in a separate thread)
_playwright: Playwright = None
_browser: Browser = None
_lock = threading.Lock()

# Thread pool for running Playwright operations - keeps Playwright in same thread
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")


def _get_or_create_browser():
    """Initialize browser (runs in executor thread)."""
    global _playwright, _browser

    if _browser is None or not _browser.is_connected():
        logger.info("Launching shared Chromium browser...")

        if _playwright is None:
            _playwright = sync_playwright().start()

        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
            ]
        )
        logger.info("Browser launched successfully")

    return _browser


def run_in_browser_thread(func, *args, **kwargs):
    """
    Run a function in the Playwright thread pool.
    Use this to wrap entire scraping operations to avoid asyncio conflicts.
    """
    def _wrapper():
        return func(*args, **kwargs)

    future = _executor.submit(_wrapper)
    return future.result(timeout=300)  # 5 minute timeout for scraping


def get_browser() -> Browser:
    """
    Get or create a shared browser instance.
    Must be called from within run_in_browser_thread context.
    """
    global _playwright, _browser

    if _browser is None or not _browser.is_connected():
        logger.info("Launching shared Chromium browser...")

        if _playwright is None:
            _playwright = sync_playwright().start()

        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
            ]
        )
        logger.info("Browser launched successfully")

    return _browser


def create_context() -> BrowserContext:
    """
    Create a new browser context with standard settings.
    Must be called from within run_in_browser_thread context.
    """
    browser = get_browser()
    return browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


def _close_browser_sync():
    """Close browser (runs in executor thread)."""
    global _playwright, _browser

    if _browser is not None:
        try:
            _browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        _browser = None

    if _playwright is not None:
        try:
            _playwright.stop()
            logger.info("Playwright stopped")
        except Exception as e:
            logger.warning(f"Error stopping Playwright: {e}")
        _playwright = None


def close_browser():
    """
    Close the shared browser instance and cleanup resources.
    Call this when the bot is shutting down.
    """
    with _lock:
        future = _executor.submit(_close_browser_sync)
        try:
            future.result(timeout=10)
        except Exception as e:
            logger.warning(f"Error during browser cleanup: {e}")


def is_browser_running() -> bool:
    """Check if the shared browser is currently running."""
    return _browser is not None and _browser.is_connected()
