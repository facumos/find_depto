import re
import logging
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from .browser_manager import create_context, run_in_browser_thread

logger = logging.getLogger(__name__)

BASE_URL = "https://www.zonaprop.com.ar"
# Order by most recent (orden-publicado-descendente) to get newest listings first
SEARCH_BASE = "https://www.zonaprop.com.ar/departamentos-alquiler-la-plata-orden-publicado-descendente"


def parse_price(text):
    """Parse price from text like '$ 450.000'"""
    # Remove USD prices, keep ARS only
    if "USD" in text.upper() or "U$S" in text.upper():
        return None
    text = text.replace("$", "").replace(".", "").replace(" ", "").strip()
    try:
        return int(re.sub(r'[^\d]', '', text))
    except ValueError:
        return None


def parse_expensas(text):
    """Parse expensas from text like '$ 50.000 Expensas'"""
    match = re.search(r'\$?\s*([\d\.]+)\s*expensas', text.lower())
    if match:
        try:
            return int(match.group(1).replace(".", ""))
        except ValueError:
            pass
    return None


def parse_rooms(text):
    """
    Parse number of rooms from text.
    Looks for patterns like '2 amb', '3 ambientes', '2 dorm', '1 dormitorio'

    Since listings may show dormitorios (bedrooms), we convert:
    - 1 dorm = 2 ambientes (1 bedroom + living)
    - 2 dorm = 3 ambientes (2 bedrooms + living)
    """
    # First try 'ambientes' or 'amb'
    match = re.search(r'(\d+)\s*amb', text.lower())
    if match:
        return int(match.group(1))

    # Try dormitorios/dorm (bedrooms)
    match = re.search(r'(\d+)\s*dorm', text.lower())
    if match:
        bedrooms = int(match.group(1))
        # Convert bedrooms to ambientes: bedrooms + 1 (for living room)
        return bedrooms + 1

    return None


def parse_listing_from_text(card_text, url):
    """Parse listing data from card text content."""
    lines = card_text.strip().split('\n')

    price = None
    expensas = None
    rooms = None
    address = None

    for line in lines:
        line = line.strip()

        # Parse price (usually starts with $)
        if line.startswith('$') and price is None:
            if 'expensas' not in line.lower():
                price = parse_price(line)

        # Parse expensas
        if 'expensas' in line.lower() and expensas is None:
            expensas = parse_expensas(line)

        # Parse rooms
        if 'amb' in line.lower() and rooms is None:
            rooms = parse_rooms(line)

        # Parse address - look for La Plata or street patterns
        if address is None and line and not line.startswith('$'):
            # Address usually contains "La Plata" or street numbers
            if 'la plata' in line.lower() or re.search(r'\b\d{1,2}\b.*\b\d{1,2}\b', line):
                address = line

    return price, expensas, rooms, address


def _scrape_zonaprop_sync(max_pages, delay):
    """
    Internal sync function that runs in the Playwright thread.
    """
    listings = []
    context = None

    try:
        # Use shared browser instance
        context = create_context()
        page = context.new_page()

        for page_num in range(1, max_pages + 1):
            url = f"{SEARCH_BASE}.html" if page_num == 1 else f"{SEARCH_BASE}-pagina-{page_num}.html"
            logger.debug(f"Scraping ZonaProp page {page_num}: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(delay * 1000)

                # Wait for listings to load
                page.wait_for_selector('div[data-posting-type]', timeout=15000)

                # Get all listing cards
                cards = page.query_selector_all('div[data-posting-type]')

                if not cards:
                    logger.info(f"No ZonaProp listings found on page {page_num}, stopping")
                    break

                logger.debug(f"Found {len(cards)} ZonaProp listings on page {page_num}")

                for card in cards:
                    try:
                        # Get link
                        link_elem = card.query_selector('a[href*="/propiedades/"]') or card.query_selector('a')
                        if not link_elem:
                            continue

                        href = link_elem.get_attribute("href")
                        if not href:
                            continue

                        full_url = BASE_URL + href if href.startswith("/") else href

                        # Extract ID from URL (e.g., "58127503" from "...58127503.html")
                        id_match = re.search(r'-(\d+)\.html', full_url)
                        listing_id = id_match.group(1) if id_match else full_url

                        # Parse from card text
                        card_text = card.inner_text()
                        price, expensas, rooms, address = parse_listing_from_text(card_text, full_url)

                        if price is None:
                            continue

                        listing = {
                            "id": f"zonaprop_{listing_id}",
                            "price": price,
                            "rooms": rooms,
                            "expensas": expensas,
                            "address": address or "",
                            "url": full_url,
                            "source": "zonaprop"
                        }

                        listings.append(listing)

                    except Exception as e:
                        logger.warning(f"Error parsing ZonaProp card: {e}")
                        continue

            except PlaywrightTimeout:
                logger.warning(f"Timeout on ZonaProp page {page_num}")
                break
            except Exception as e:
                logger.error(f"Error on ZonaProp page {page_num}: {e}")
                break

    except Exception as e:
        logger.error(f"Failed to initialize Playwright for ZonaProp: {e}")
    finally:
        # Always close the context (but not the browser - it's shared)
        if context:
            try:
                context.close()
            except:
                pass

    logger.info(f"Successfully scraped {len(listings)} listings from ZonaProp")
    return listings


def scrape_zonaprop(max_pages=1, delay=3):
    """
    Scrape apartment listings from ZonaProp using Playwright.
    Runs in a separate thread to avoid asyncio conflicts.

    Args:
        max_pages: Maximum number of pages to scrape
        delay: Delay between actions in seconds

    Returns:
        list: List of apartment listing dictionaries
    """
    return run_in_browser_thread(_scrape_zonaprop_sync, max_pages, delay)
