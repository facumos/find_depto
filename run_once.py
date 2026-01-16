#!/usr/bin/env python3
"""Run the apartment bot once (for cron usage)."""

import os
import sys
import asyncio
import logging

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from scrappers.argenprop import scrape_argenprop
from scrappers.zonaprop import scrape_zonaprop
from scrappers.mercadolibre import scrape_mercadolibre
from scrappers.browser_manager import close_browser
from filters import matches
from notifier import send_message
from storage import load_sent, save_sent
from user_config import get_user_config, get_all_user_ids

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def check_and_notify_sync():
    """Synchronous version of check_and_notify for cron usage."""
    from datetime import datetime

    try:
        logger.info("=" * 50)
        logger.info(f"Starting apartment check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        sent = load_sent()
        logger.info(f"Loaded {len(sent)} previously sent listings")

        # Scrape all sources
        listings = []

        logger.info("Scraping ArgenProp...")
        listings.extend(scrape_argenprop(max_pages=5))

        logger.info("Scraping ZonaProp...")
        listings.extend(scrape_zonaprop(max_pages=5))

        logger.info("Scraping MercadoLibre...")
        listings.extend(scrape_mercadolibre(max_pages=5))

        logger.info(f"Found {len(listings)} total listings from all sources")

        # Get all registered users
        user_ids = get_all_user_ids()
        logger.info(f"Checking for {len(user_ids)} registered users")

        new_count = 0
        for ap in listings:
            if ap["id"] in sent:
                continue

            # Check each user's criteria
            for user_id in user_ids:
                config = get_user_config(user_id)
                if not config.get("active", True):
                    continue

                if matches(ap, config):
                    logger.info(f"Sending to user {user_id}: {ap['url']}")
                    try:
                        send_message(TOKEN, user_id, ap)
                        new_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send to user {user_id}: {e}")

            sent.add(ap["id"])

        save_sent(sent)
        logger.info(f"Sent {new_count} new listings")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error in check_and_notify_sync: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        check_and_notify_sync()
    finally:
        # Cleanup browser
        close_browser()
