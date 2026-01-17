import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://www.inmobusqueda.com.ar"
# Search in La Plata casco urbano, filtered to listings published in the last 15 days
SEARCH_BASE = "https://www.inmobusqueda.com.ar/departamento-alquiler-la-plata-casco-urbano"
SEARCH_PARAMS = "?publicado=5"  # publicado=5 = last 15 days

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def parse_price_and_expensas(text):
    """
    Parse price and expensas from text like '$ 450.000' or '$300.000  Expensas : $80000'.
    Returns tuple (price, expensas). Returns (None, None) for USD prices.
    """
    if not text:
        return None, None
    if "USD" in text.upper() or "U$S" in text.upper() or "US$" in text.upper():
        return None, None

    expensas = None
    price = None

    # Check if expensas is in the same text
    if "expensas" in text.lower():
        # Split on "expensas" and parse each part
        parts = re.split(r'expensas\s*:?\s*', text, flags=re.IGNORECASE)
        if len(parts) >= 2:
            # First part is price, second part is expensas
            price_text = re.sub(r'[^\d]', '', parts[0])
            expensas_text = re.sub(r'[^\d]', '', parts[1])
            try:
                price = int(price_text) if price_text else None
                expensas = int(expensas_text) if expensas_text else None
            except ValueError:
                pass
    else:
        # No expensas in text, just parse the price
        price_text = re.sub(r'[^\d]', '', text)
        try:
            price = int(price_text) if price_text else None
        except ValueError:
            pass

    return price, expensas


def parse_price(text):
    """Parse price from text like '$ 450.000'. Returns None for USD prices."""
    price, _ = parse_price_and_expensas(text)
    return price


def parse_rooms(text):
    """
    Parse number of rooms from text.
    Handles: Monoambiente, 2 amb, 3 ambientes, 2 dorm, 1 dormitorio
    """
    if not text:
        return None

    text_lower = text.lower()

    # Check for Monoambiente
    if 'monoambiente' in text_lower or 'mono ambiente' in text_lower:
        return 1

    # Try 'ambientes' or 'amb'
    match = re.search(r'(\d+)\s*amb', text_lower)
    if match:
        return int(match.group(1))

    # Try dormitorios/dorm (bedrooms) - convert to ambientes
    match = re.search(r'(\d+)\s*dorm', text_lower)
    if match:
        bedrooms = int(match.group(1))
        return bedrooms + 1  # bedrooms + living room

    return None


def parse_expensas(text):
    """Try to find expensas in text."""
    if not text:
        return None
    match = re.search(r'expensas[:\s]*\$?\s*([\d\.]+)', text.lower())
    if match:
        try:
            return int(match.group(1).replace(".", ""))
        except ValueError:
            pass
    return None


def extract_address(text):
    """Extract address from listing text."""
    if not text:
        return ""

    # Look for street patterns like "40 e/ 14 y 15" or "calle 7 y 45"
    patterns = [
        r'(\d{1,2}\s*(?:e/|entre)\s*\d{1,2}\s*y\s*\d{1,2})',
        r'(\d{1,2}\s*y\s*\d{1,2})',
        r'(calle\s*\d{1,2}[^,]*)',
        r'(av\.?\s*\d{1,2}[^,]*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()[:60]

    return ""


def scrape_inmobusqueda(max_pages=1, delay=2):
    """
    Scrape apartment listings from Inmobusqueda using requests/BeautifulSoup.

    Args:
        max_pages: Maximum number of pages to scrape
        delay: Delay between requests in seconds (unused, kept for API consistency)

    Returns:
        list: List of apartment listing dictionaries
    """
    import time

    listings = []

    for page_num in range(1, max_pages + 1):
        # Page 1 has no suffix, page 2+ has -pagina-N
        # Add SEARCH_PARAMS to filter by recent publications
        if page_num == 1:
            url = f"{SEARCH_BASE}.html{SEARCH_PARAMS}"
        else:
            url = f"{SEARCH_BASE}-pagina-{page_num}.html{SEARCH_PARAMS}"

        logger.debug(f"Scraping Inmobusqueda page {page_num}: {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all listing containers
            cards = soup.select('.resultadoContenedorDatosResultados')

            if not cards:
                logger.info(f"No Inmobusqueda listings found on page {page_num}, stopping")
                break

            logger.debug(f"Found {len(cards)} Inmobusqueda listings on page {page_num}")

            for card in cards:
                try:
                    # Get link
                    link_elem = card.select_one('a[href*="ficha"]')
                    if not link_elem:
                        continue

                    full_url = link_elem.get('href', '')
                    if not full_url:
                        continue

                    # Make URL absolute if needed
                    if full_url.startswith('/'):
                        full_url = BASE_URL + full_url

                    # Extract listing ID for deduplication
                    id_match = re.search(r'id=(\d+)', full_url)
                    listing_id = id_match.group(1) if id_match else full_url

                    # Get price and expensas from price element
                    price_elem = card.select_one('.resultadoPrecio')
                    price_text = price_elem.get_text(strip=True) if price_elem else ""
                    price, expensas_from_price = parse_price_and_expensas(price_text)

                    if price is None:
                        continue

                    # Get full text for parsing rooms and address
                    card_text = card.get_text(' ', strip=True)

                    # Parse rooms
                    rooms = parse_rooms(card_text)

                    # Use expensas from price element if available, otherwise try to parse from card text
                    expensas = expensas_from_price if expensas_from_price else parse_expensas(card_text)

                    # Extract address
                    address = extract_address(card_text)

                    listing = {
                        "id": f"inmobusqueda_{listing_id}",
                        "price": price,
                        "rooms": rooms,
                        "expensas": expensas,
                        "address": address,
                        "url": full_url,
                        "source": "inmobusqueda"
                    }

                    listings.append(listing)

                except Exception as e:
                    logger.warning(f"Error parsing Inmobusqueda card: {e}")
                    continue

            # Small delay between pages
            if page_num < max_pages:
                time.sleep(delay)

        except requests.RequestException as e:
            logger.error(f"Error fetching Inmobusqueda page {page_num}: {e}")
            break
        except Exception as e:
            logger.error(f"Error on Inmobusqueda page {page_num}: {e}")
            break

    logger.info(f"Successfully scraped {len(listings)} listings from Inmobusqueda")
    return listings
