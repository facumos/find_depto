import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://www.zonaprop.com.ar"
SEARCH_BASE = "https://www.zonaprop.com.ar/departamentos-alquiler-la-plata"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def parse_price(text):
    """Parse price from text like '$ 450.000'"""
    text = text.replace("$", "").replace(".", "").replace(" ", "").strip()
    try:
        return int(text)
    except ValueError:
        return None


def parse_expensas(text):
    """Parse expensas from text like '+ $ 50.000 Expensas'"""
    match = re.search(r'\+?\s*\$?\s*([\d\.]+)', text.replace(".", ""))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def parse_rooms(text):
    """Parse number of rooms from text like '2 amb.' or '3 ambientes'"""
    match = re.search(r'(\d+)\s*amb', text.lower())
    if match:
        return int(match.group(1))
    return None


def scrape_zonaprop(max_pages=5, delay=3, max_retries=3):
    """
    Scrape apartment listings from ZonaProp.

    Args:
        max_pages: Maximum number of pages to scrape
        delay: Delay between page requests in seconds
        max_retries: Maximum retry attempts for failed requests

    Returns:
        list: List of apartment listing dictionaries
    """
    listings = []

    for page in range(1, max_pages + 1):
        url = f"{SEARCH_BASE}.html" if page == 1 else f"{SEARCH_BASE}-pagina-{page}.html"
        logger.debug(f"Scraping ZonaProp page {page}: {url}")

        r = None
        for retry in range(max_retries):
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if retry == max_retries - 1:
                    logger.error(f"Failed to fetch ZonaProp page {page} after {max_retries} attempts: {e}")
                    return listings
                logger.warning(f"ZonaProp page {page} request failed (attempt {retry + 1}/{max_retries}), retrying...")
                time.sleep(delay * (retry + 1))

        if r is None or r.status_code != 200:
            logger.warning(f"ZonaProp page {page} returned status {r.status_code if r else 'None'}, stopping")
            break

        try:
            soup = BeautifulSoup(r.text, "lxml")

            # ZonaProp uses data-qa="posting" for listing cards
            cards = soup.select('[data-qa="posting"]')

            if not cards:
                # Fallback selectors
                cards = soup.select('.postingCard') or soup.select('div[data-posting-type]')

            if not cards:
                logger.info(f"No ZonaProp listings found on page {page}, stopping")
                break

            logger.debug(f"Found {len(cards)} ZonaProp listings on page {page}")

            for card in cards:
                try:
                    # Get link
                    link_elem = card.select_one('a[data-qa="posting-url"]') or card.select_one('a')
                    if not link_elem or "href" not in link_elem.attrs:
                        continue

                    link = link_elem["href"]
                    full_url = BASE_URL + link if link.startswith("/") else link

                    # Get price
                    price_elem = card.select_one('[data-qa="POSTING_CARD_PRICE"]') or card.select_one('.firstPrice')
                    if not price_elem:
                        continue

                    price = parse_price(price_elem.get_text(strip=True))
                    if price is None:
                        continue

                    # Get expensas
                    expensas = None
                    expensas_elem = card.select_one('[data-qa="POSTING_CARD_EXPENSES"]') or card.select_one('.postingCardExpenses')
                    if expensas_elem:
                        expensas = parse_expensas(expensas_elem.get_text(strip=True))

                    # Get rooms from features
                    rooms = None
                    features_elem = card.select_one('[data-qa="POSTING_CARD_FEATURES"]') or card.select_one('.postingCardMainFeatures')
                    if features_elem:
                        rooms = parse_rooms(features_elem.get_text(strip=True))

                    # Fallback: search in full card text
                    if rooms is None:
                        rooms = parse_rooms(card.get_text(" ", strip=True))

                    listing = {
                        "id": full_url,
                        "price": price,
                        "rooms": rooms,
                        "expensas": expensas,
                        "url": full_url,
                        "source": "zonaprop"
                    }

                    listings.append(listing)

                except Exception as e:
                    logger.warning(f"Error parsing ZonaProp listing card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing ZonaProp page {page}: {e}")
            break

        time.sleep(delay)

    logger.info(f"Successfully scraped {len(listings)} listings from ZonaProp")
    return listings
