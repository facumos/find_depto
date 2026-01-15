import os
import time
import logging
import schedule
from datetime import datetime
from scrappers.argenprop import scrape_argenprop
from filters import matches
from notifier import send_message
from storage import load_sent, save_sent

os.chdir(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8515341054:AAGLbPYICYimfzknKl5MaC8QdmfwvevCaXs")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1416589926")

CRITERIA = {
    "max_price": 600000,
    "min_rooms": 2,
    "max_expensas": 100000
}

# 🧪 TEST MODE FLAG - Set to True to test once, False for production
TEST_MODE = True

def check_and_notify():
    """Main function to check for new apartments and send notifications."""
    try:
        logger.info("=" * 50)
        logger.info(f"Starting apartment check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        sent = load_sent()
        logger.info(f"Loaded {len(sent)} previously sent listings")
        
        logger.info("Scraping ArgenProp...")
        listings = scrape_argenprop(max_pages=5)
        logger.info(f"Found {len(listings)} total listings")
        
        new_count = 0
        matched_count = 0
        
        for ap in listings:
            if ap["id"] in sent:
                continue
            
            new_count += 1
            
            if matches(ap, CRITERIA):
                matched_count += 1
                logger.info(f"Sending notification for: {ap['url']}")
                
                try:
                    send_message(TOKEN, CHAT_ID, ap)
                    sent.add(ap["id"])
                    logger.info(f"✓ Successfully sent listing {ap['id']}")
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"✗ Failed to send listing {ap['id']}: {e}")
        
        save_sent(sent)
        
        logger.info(f"Summary: {new_count} new listings, {matched_count} matched criteria and sent")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Error in check_and_notify: {e}", exc_info=True)

def main():
    """Main bot loop with scheduling."""
    logger.info("🤖 Telegram Apartment Bot Started")
    logger.info(f"Chat ID: {CHAT_ID}")
    logger.info(f"Criteria: {CRITERIA}")
    
    if TEST_MODE:
        logger.info("⚠️  TEST MODE: Running once only")
        check_and_notify()
        logger.info("✅ Test complete! Check Telegram for messages.")
        logger.info("💡 If it worked, set TEST_MODE = False in main.py to enable scheduling")
        return
    
    logger.info("Checking every 30 minutes...")
    
    # Run immediately on startup
    check_and_notify()
    
    # Schedule to run every 30 minutes
    schedule.every(30).minutes.do(check_and_notify)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()