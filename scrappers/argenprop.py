import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://www.argenprop.com"
SEARCH_BASE = "https://www.argenprop.com/departamentos/alquiler/la-plata"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def parse_price_and_expensas(text):
    """
    Parse price and expensas from combined text like:
    '$510.000+ $70.000 expensas'
    
    Returns:
        tuple: (price, expensas) or (None, None)
    """
    # Remove $ signs and split by '+'
    text = text.replace("$", "").replace("\n", " ").strip()
    
    # Pattern: number + optional space + '+' + optional space + number + 'expensas'
    match = re.search(r'([\d\.]+)\s*\+\s*([\d\.]+)', text)
    
    if match:
        try:
            # First number is rent, second is expensas
            price_str = match.group(1).replace(".", "")
            expensas_str = match.group(2).replace(".", "")
            
            price = int(price_str) if price_str else None
            expensas = int(expensas_str) if expensas_str else None
            
            return price, expensas
        except (ValueError, AttributeError):
            pass
    
    # Fallback: just try to get the first number as price
    numbers = re.findall(r"[\d\.]+", text)
    if numbers:
        try:
            price = int(numbers[0].replace(".", ""))
            return price, None
        except ValueError:
            pass
    
    return None, None

def parse_rooms(text):
    """
    Parse number of rooms from text.
    Looks for patterns like '2 amb', '3 ambientes', '2 dorm', '1 dormitorio'
    
    Since listings show dormitorios (bedrooms), we convert:
    - 1 dorm = 2 ambientes (1 bedroom + living)
    - 2 dorm = 3 ambientes (2 bedrooms + living)
    - etc.
    """
    # First try 'ambientes' or 'amb'
    match = re.search(r'(\d+)\s*amb(?:iente)?s?', text.lower())
    if match:
        return int(match.group(1))
    
    # Try dormitorios/dorm (bedrooms)
    match = re.search(r'(\d+)\s*dorm(?:itorio)?s?', text.lower())
    if match:
        bedrooms = int(match.group(1))
        # Convert bedrooms to ambientes: bedrooms + 1 (for living room)
        return bedrooms + 1
    
    return None

def scrape_argenprop(max_pages=5, delay=2, max_retries=3):
    """
    Scrape apartment listings from ArgenProp.
    
    Args:
        max_pages: Maximum number of pages to scrape
        delay: Delay between page requests in seconds
        max_retries: Maximum retry attempts for failed requests
    
    Returns:
        list: List of apartment listing dictionaries
    """
    listings = []

    for page in range(1, max_pages + 1):
        url = SEARCH_BASE if page == 1 else f"{SEARCH_BASE}-pagina-{page}"
        logger.debug(f"Scraping page {page}: {url}")
        
        # Retry logic for page requests
        r = None
        for retry in range(max_retries):
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if retry == max_retries - 1:
                    logger.error(f"Failed to fetch page {page} after {max_retries} attempts: {e}")
                    return listings  # Return what we have so far
                logger.warning(f"Page {page} request failed (attempt {retry + 1}/{max_retries}), retrying...")
                time.sleep(delay * (retry + 1))

        if r is None or r.status_code != 200:
            logger.warning(f"Page {page} returned status {r.status_code if r else 'None'}, stopping")
            break

        try:
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("div.listing__item")

            if not cards:
                logger.info(f"No listings found on page {page}, stopping")
                break  # no more results

            logger.debug(f"Found {len(cards)} listings on page {page}")

            for card in cards:
                try:
                    link_elem = card.select_one("a")
                    if not link_elem or "href" not in link_elem.attrs:
                        logger.warning("Listing card missing link, skipping")
                        continue
                    
                    link = link_elem["href"]
                    full_url = BASE_URL + link if link.startswith("/") else link

                    # Get the price element (contains both rent and expensas)
                    price_elem = card.select_one(".card__price")
                    if not price_elem:
                        logger.warning(f"Listing {full_url} missing price, skipping")
                        continue
                    
                    # Parse price and expensas together
                    price_text = price_elem.get_text(strip=True)
                    price, expensas = parse_price_and_expensas(price_text)
                    
                    if price is None:
                        logger.warning(f"Could not parse price from: {price_text}")
                        continue

                    # Get full text for rooms
                    full_text = card.get_text(" ", strip=True)

                    # Parse rooms (handles both 'amb' and 'dorm')
                    rooms = parse_rooms(full_text)

                    listing = {
                        "id": full_url,
                        "price": price,
                        "rooms": rooms,
                        "expensas": expensas,
                        "url": full_url,
                        "source": "argenprop"
                    }
                    
                    listings.append(listing)
                    
                    # Log parsed data
                    exp_str = f"${expensas:,}" if expensas else "N/A"
                    rooms_str = f"{rooms} amb" if rooms else "N/A"
                    logger.debug(f"✓ ${price:,} + {exp_str} | {rooms_str}")

                except Exception as e:
                    logger.warning(f"Error parsing listing card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing page {page}: {e}")
            break

        time.sleep(delay)  # be polite

    logger.info(f"Successfully scraped {len(listings)} listings from {min(page, max_pages)} pages")
    return listings