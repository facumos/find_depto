#!/usr/bin/env python3
"""
Pre-flight check script for the apartment bot.
Run this before deploying to production to verify everything works.

Usage:
    python preflight.py           # Run all checks
    python preflight.py --quick   # Skip scraping test (faster)
    python preflight.py --scrape  # Only test scraping
"""

import os
import sys
import argparse

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def ok(msg):
    print(f"  {Colors.GREEN}[OK]{Colors.RESET} {msg}")


def fail(msg):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET} {msg}")


def warn(msg):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def info(msg):
    print(f"  {Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def header(msg):
    print(f"\n{Colors.BOLD}=== {msg} ==={Colors.RESET}")


def check_dependencies():
    """Check that all required Python packages are installed."""
    header("Checking Dependencies")

    all_ok = True
    dependencies = [
        ("dotenv", "python-dotenv"),
        ("requests", "requests"),
        ("bs4", "beautifulsoup4"),
        ("lxml", "lxml"),
        ("telegram", "python-telegram-bot"),
        ("playwright.sync_api", "playwright"),
    ]

    for module, package in dependencies:
        try:
            __import__(module)
            ok(f"{package}")
        except ImportError:
            fail(f"{package} - run: pip install {package}")
            all_ok = False

    return all_ok


def check_playwright_browsers():
    """Check that Playwright browsers are installed."""
    header("Checking Playwright Browsers")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Try to get browser path
            browser = p.chromium.launch(headless=True)
            browser.close()
            ok("Chromium browser installed and working")
            return True
    except Exception as e:
        fail(f"Playwright browser error: {e}")
        info("Run: playwright install chromium")
        return False


def check_env_variables():
    """Check that required environment variables are set."""
    header("Checking Environment Variables")

    from dotenv import load_dotenv
    load_dotenv()

    all_ok = True

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        # Mask the token for security
        masked = token[:10] + "..." + token[-5:] if len(token) > 15 else "***"
        ok(f"TELEGRAM_BOT_TOKEN is set ({masked})")
    else:
        fail("TELEGRAM_BOT_TOKEN not set")
        all_ok = False

    # Check for hardcoded token in main.py (security issue)
    try:
        with open("main.py", "r") as f:
            content = f.read()
            if "8515341054:AAG" in content:
                warn("Hardcoded token found in main.py - consider removing fallback")
    except:
        pass

    return all_ok


def check_data_files():
    """Check data files exist and are valid."""
    header("Checking Data Files")

    all_ok = True

    # Check sent.json
    try:
        from storage import load_sent
        sent = load_sent()
        ok(f"sent.json - {len(sent)} previously sent listings")
    except Exception as e:
        warn(f"sent.json issue: {e} (will be created on first run)")

    # Check user_configs.json
    try:
        from user_config import get_all_user_ids
        users = get_all_user_ids()
        if users:
            ok(f"user_configs.json - {len(users)} registered users")
        else:
            warn("user_configs.json - no users registered yet")
    except Exception as e:
        warn(f"user_configs.json issue: {e}")

    return all_ok


def check_imports():
    """Check that all project modules can be imported."""
    header("Checking Project Imports")

    all_ok = True
    modules = [
        "scrappers.argenprop",
        "scrappers.zonaprop",
        "scrappers.mercadolibre",
        "filters",
        "notifier",
        "storage",
        "user_config",
    ]

    for module in modules:
        try:
            __import__(module)
            ok(module)
        except Exception as e:
            fail(f"{module}: {e}")
            all_ok = False

    return all_ok


def test_scraping(max_pages=1):
    """Test that scrapers can fetch real data."""
    header("Testing Scrapers (this may take a minute)")

    all_ok = True
    results = {}

    # Test ArgenpProp (HTTP-based, fast)
    try:
        from scrappers.argenprop import scrape_argenprop
        listings = scrape_argenprop(max_pages=max_pages)
        results["argenprop"] = len(listings)
        if listings:
            ok(f"ArgenProp: {len(listings)} listings found")
        else:
            warn("ArgenProp: 0 listings (might be temporary)")
    except Exception as e:
        fail(f"ArgenProp: {e}")
        all_ok = False

    # Test ZonaProp (Playwright-based)
    try:
        from scrappers.zonaprop import scrape_zonaprop
        listings = scrape_zonaprop(max_pages=max_pages)
        results["zonaprop"] = len(listings)
        if listings:
            ok(f"ZonaProp: {len(listings)} listings found")
        else:
            warn("ZonaProp: 0 listings (might be blocked or temporary)")
    except Exception as e:
        fail(f"ZonaProp: {e}")
        all_ok = False

    # Test MercadoLibre (Playwright-based)
    try:
        from scrappers.mercadolibre import scrape_mercadolibre
        listings = scrape_mercadolibre(max_pages=max_pages)
        results["mercadolibre"] = len(listings)
        if listings:
            ok(f"MercadoLibre: {len(listings)} listings found")
        else:
            warn("MercadoLibre: 0 listings (might be blocked or temporary)")
    except Exception as e:
        fail(f"MercadoLibre: {e}")
        all_ok = False

    total = sum(results.values())
    info(f"Total listings found: {total}")

    return all_ok


def test_telegram_connection():
    """Test that we can connect to Telegram API."""
    header("Testing Telegram Connection")

    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        fail("No token available")
        return False

    try:
        import requests
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10
        )
        data = response.json()

        if data.get("ok"):
            bot_info = data.get("result", {})
            ok(f"Connected as @{bot_info.get('username', 'unknown')}")
            return True
        else:
            fail(f"Telegram API error: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        fail(f"Connection error: {e}")
        return False


def check_memory_usage():
    """Check current memory usage of Python process."""
    header("Memory Check")

    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_mb = usage.ru_maxrss / 1024  # Convert KB to MB (on Linux)
        ok(f"Current memory usage: {mem_mb:.1f} MB")

        if mem_mb > 500:
            warn("High memory usage detected")

        return True
    except:
        info("Memory check not available on this platform")
        return True


def run_tests():
    """Run the test suite."""
    header("Running Test Suite")

    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Count passed tests
            lines = result.stdout.split('\n')
            for line in lines:
                if 'passed' in line:
                    ok(line.strip())
                    break
            return True
        else:
            fail("Some tests failed")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return False
    except subprocess.TimeoutExpired:
        fail("Test suite timed out")
        return False
    except Exception as e:
        warn(f"Could not run tests: {e}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Pre-flight checks for apartment bot")
    parser.add_argument("--quick", action="store_true", help="Skip slow checks (scraping)")
    parser.add_argument("--scrape", action="store_true", help="Only test scraping")
    args = parser.parse_args()

    print(f"{Colors.BOLD}Apartment Bot Pre-flight Check{Colors.RESET}")
    print("=" * 40)

    all_passed = True

    if args.scrape:
        # Only run scraping tests
        all_passed &= check_playwright_browsers()
        all_passed &= test_scraping(max_pages=2)
    else:
        # Run all checks
        all_passed &= check_dependencies()
        all_passed &= check_env_variables()
        all_passed &= check_imports()
        all_passed &= check_data_files()
        all_passed &= test_telegram_connection()

        if not args.quick:
            all_passed &= check_playwright_browsers()
            all_passed &= test_scraping(max_pages=1)
        else:
            info("Skipping scraping tests (--quick mode)")

        all_passed &= check_memory_usage()
        all_passed &= run_tests()

    # Summary
    print("\n" + "=" * 40)
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}All checks passed! Ready for deployment.{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}Some checks failed. Please fix before deploying.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
