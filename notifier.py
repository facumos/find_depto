import requests
import logging
import time

logger = logging.getLogger(__name__)

def send_message(token, chat_id, ap, max_retries=3, retry_delay=2):
    """
    Send a message to Telegram with retry logic.
    
    Args:
        token: Telegram bot token
        chat_id: Chat ID to send message to
        ap: Apartment listing dictionary
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Raises:
        Exception: If message sending fails after all retries
    """
    text = (
        "🏠 <b>Nuevo depto en alquiler (La Plata)</b>\n\n"
        f"💲 Alquiler: ${ap.get('price', 'N/A')}\n"
        f"🧾 Expensas: ${ap.get('expensas', 'N/A')}\n"
        f"🛏 {ap.get('rooms', 'N/A')} ambientes\n\n"
        f"🔗 {ap.get('url', '#')}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if not result.get("ok"):
                error_msg = result.get("description", "Unknown error")
                raise Exception(f"Telegram API error: {error_msg}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
                raise
            
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
            time.sleep(retry_delay)
