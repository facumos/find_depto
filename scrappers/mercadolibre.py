import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://inmuebles.mercadolibre.com.ar"
SEARCH_BASE = "https://inmuebles.mercadolibre.com.ar/departamentos/alquiler/la-plata"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}


def parse_price(text):
    """Parse price from text like '$ 450.000' or '450000'"""
    # Remove currency symbols and dots (thousand separators)
    text = re.sub(r'[^\d]', '', text)
    try:
        return int(text) if text else None
    except ValueError:
        return None


def parse_rooms(text):
    """Parse number of rooms from text like '2 amb' or '3 ambientes'"""
    match = re.search(r'(\d+)\s*amb', text.lower())
    if match:
        return int(match.group(1))
    return None


def parse_expensas_from_text(text):
    """Try to find expensas in listing text"""
    match = re.search(r'expensas[:\s]*\$?\s*([\d\.]+)', text.lower().replace(".", ""))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def scrape_mercadolibre(max_pages=5, delay=3, max_retries=3):
    """
    Scrape apartment listings from MercadoLibre Inmuebles.

    Args:
        max_pages: Maximum number of pages to scrape
        delay: Delay between page requests in seconds
        max_retries: Maximum retry attempts for failed requests

    Returns:
        list: List of apartment listing dictionaries
    """
    listings = []

    for page in range(1, max_pages + 1):
        # MercadoLibre uses _Desde_X for pagination (48 items per page)
        offset = (page - 1) * 48
        url = SEARCH_BASE if page == 1 else f"{SEARCH_BASE}_Desde_{offset + 1}"
        logger.debug(f"Scraping MercadoLibre page {page}: {url}")

        r = None
        for retry in range(max_retries):
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if retry == max_retries - 1:
                    logger.error(f"Failed to fetch MercadoLibre page {page} after {max_retries} attempts: {e}")
                    return listings
                logger.warning(f"MercadoLibre page {page} request failed (attempt {retry + 1}/{max_retries}), retrying...")
                time.sleep(delay * (retry + 1))

        if r is None or r.status_code != 200:
            logger.warning(f"MercadoLibre page {page} returned status {r.status_code if r else 'None'}, stopping")
            break

        try:
            soup = BeautifulSoup(r.text, "lxml")

            # MercadoLibre uses different selectors - try multiple
            cards = soup.select('li.ui-search-layout__item')

            if not cards:
                # Fallback selectors
                cards = soup.select('.poly-card') or soup.select('[data-testid="result-item"]')

            if not cards:
                logger.info(f"No MercadoLibre listings found on page {page}, stopping")
                break

            logger.debug(f"Found {len(cards)} MercadoLibre listings on page {page}")

            for card in cards:
                try:
                    # Get link - usually in h2 > a or direct a tag
                    link_elem = card.select_one('a.ui-search-link') or card.select_one('h2 a') or card.select_one('a[href*="departamento"]')
                    if not link_elem or "href" not in link_elem.attrs:
                        continue

                    full_url = link_elem["href"]

                    # Skip if not a real listing URL
                    if "mercadolibre" not in full_url and "meli" not in full_url:
                        continue

                    # Get price
                    price_elem = card.select_one('.poly-price__current .andes-money-amount__fraction') or \
                                 card.select_one('.ui-search-price__second-line .andes-money-amount__fraction') or \
                                 card.select_one('[class*="price"] .andes-money-amount__fraction')

                    if not price_elem:
                        # Try alternative price selector
                        price_elem = card.select_one('.andes-money-amount__fraction')

                    if not price_elem:
                        continue

                    price = parse_price(price_elem.get_text(strip=True))
                    if price is None:
                        continue

                    # Get rooms from attributes/features
                    rooms = None
                    features = card.select('.poly-attributes-list__item') or card.select('.ui-search-card-attributes__attribute')
                    for feature in features:
                        text = feature.get_text(strip=True)
                        if 'amb' in text.lower():
                            rooms = parse_rooms(text)
                            break

                    # Fallback: search in full card text
                    if rooms is None:
                        rooms = parse_rooms(card.get_text(" ", strip=True))

                    # MercadoLibre doesn't always show expensas in the card
                    expensas = parse_expensas_from_text(card.get_text(" ", strip=True))

                    listing = {
                        "id": full_url,
                        "price": price,
                        "rooms": rooms,
                        "expensas": expensas,
                        "url": full_url,
                        "source": "mercadolibre"
                    }

                    listings.append(listing)

                except Exception as e:
                    logger.warning(f"Error parsing MercadoLibre listing card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing MercadoLibre page {page}: {e}")
            break

        time.sleep(delay)

    logger.info(f"Successfully scraped {len(listings)} listings from MercadoLibre")
    return listings
