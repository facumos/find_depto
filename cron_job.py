#!/usr/bin/env python3
"""
Cron job script for apartment notifications.
Designed to run hourly via Railway Cron, GitHub Actions, or system cron.

This script:
1. Scrapes all apartment sources
2. Filters for new apartments matching criteria
3. Sends Telegram notifications
4. Exits (no persistent process)

Usage:
    python cron_job.py
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Change to script directory for relative imports
os.chdir(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cron_job.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import after changing directory
from scrappers.argenprop import scrape_argenprop
from scrappers.zonaprop import scrape_zonaprop
from scrappers.mercadolibre import scrape_mercadolibre
from scrappers.inmobusqueda import scrape_inmobusqueda
from scrappers.browser_manager import close_browser
from filters import matches
from storage import load_sent, save_sent, load_queue, save_queue
from user_config import get_all_user_ids, get_user_config
from notifier import send_message

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MAX_LISTINGS_PER_SOURCE = 2

# Quiet hours - don't send notifications between these hours (0-23)
QUIET_HOURS_START = 0   # midnight
QUIET_HOURS_END = 8     # 8 AM


def is_quiet_hours():
    """Check if current time is within quiet hours."""
    current_hour = datetime.now().hour
    return QUIET_HOURS_START <= current_hour < QUIET_HOURS_END


def main():
    """Main cron job function."""
    logger.info("=" * 50)
    logger.info(f"Cron job started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check quiet hours
    if is_quiet_hours():
        logger.info(f"Quiet hours ({QUIET_HOURS_START}:00-{QUIET_HOURS_END}:00) - skipping")
        logger.info("=" * 50)
        return 0

    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return 1

    try:
        # Load previously sent IDs and queue
        sent = load_sent()
        queue = load_queue()
        logger.info(f"Loaded {len(sent)} previously sent listings")
        logger.info(f"Loaded {len(queue)} apartments in queue")

        # Scrape all sources
        logger.info("Scraping all sources...")
        sources = {}

        logger.info("  - ArgenProp...")
        sources["argenprop"] = scrape_argenprop()

        logger.info("  - ZonaProp...")
        sources["zonaprop"] = scrape_zonaprop()

        logger.info("  - MercadoLibre...")
        sources["mercadolibre"] = scrape_mercadolibre()

        # Close Playwright browser to free memory
        close_browser()

        logger.info("  - Inmobusqueda...")
        sources["inmobusqueda"] = scrape_inmobusqueda()

        total = sum(len(v) for v in sources.values())
        logger.info(f"Found {total} total listings")

        # Find new apartments (not seen before)
        new_apartments = []
        for source_name, listings in sources.items():
            for ap in listings:
                if ap["id"] not in sent:
                    sent.add(ap["id"])
                    new_apartments.append(ap)

        logger.info(f"Found {len(new_apartments)} NEW apartments")

        # Get all registered users
        user_ids = get_all_user_ids()
        logger.info(f"Processing for {len(user_ids)} users")

        # Priority: New apartments first, then queue (LIFO - newest first)
        # 1. Send new apartments (up to 2 per source)
        # 2. Excess new apartments go to FRONT of queue (LIFO)
        # 3. Old queue items that didn't get sent are discarded (too old)

        source_counts = {}
        to_send = []
        new_overflow = []  # New apartments that exceed per-source limit

        # Select from NEW apartments (priority)
        for ap in new_apartments:
            source_name = ap.get("source", "unknown")
            current_count = source_counts.get(source_name, 0)

            if current_count >= MAX_LISTINGS_PER_SOURCE:
                new_overflow.append(ap)
                continue

            to_send.append(ap)
            source_counts[source_name] = current_count + 1

        # New queue is ONLY the overflow from new apartments (LIFO - old queue discarded)
        queue = new_overflow

        if not to_send:
            logger.info("No apartments to send")
            save_sent(sent)
            save_queue(queue)
            logger.info("=" * 50)
            return 0

        logger.info(f"Sending {len(to_send)} apartments to {len(user_ids)} users")

        # Send selected apartments to ALL users
        total_sent = 0
        for user_id in user_ids:
            config = get_user_config(user_id)
            if not config.get("active", True):
                continue

            for ap in to_send:
                if matches(ap, config):
                    logger.info(f"Sending to {user_id}: {ap['url']}")
                    try:
                        send_message(TOKEN, user_id, ap)
                        total_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send to {user_id}: {e}")

        if queue:
            logger.info(f"{len(queue)} apartments queued for next hour")

        # Save updated sent set and queue
        save_sent(sent)
        save_queue(queue)

        logger.info(f"Sent {total_sent} notifications, {len(queue)} in queue")
        logger.info("=" * 50)
        return 0

    except Exception as e:
        logger.error(f"Cron job failed: {e}", exc_info=True)
        return 1
    finally:
        # Ensure browser is closed
        try:
            close_browser()
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())
