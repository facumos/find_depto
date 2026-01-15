import re
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

BASE_URL = "https://inmuebles.mercadolibre.com.ar"
SEARCH_BASE = "https://inmuebles.mercadolibre.com.ar/departamentos/alquiler/la-plata"


def parse_price(text):
    """Parse price from text like '$ 450.000' or '450000'"""
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


def parse_expensas(text):
    """Try to find expensas in text"""
    match = re.search(r'expensas[:\s]*\$?\s*([\d\.]+)', text.lower())
    if match:
        try:
            return int(match.group(1).replace(".", ""))
        except ValueError:
            pass
    return None


def scrape_mercadolibre(max_pages=3, delay=2):
    """
    Scrape apartment listings from MercadoLibre Inmuebles using Playwright.

    Args:
        max_pages: Maximum number of pages to scrape
        delay: Delay between actions in seconds

    Returns:
        list: List of apartment listing dictionaries
    """
    listings = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            for page_num in range(1, max_pages + 1):
                offset = (page_num - 1) * 48
                url = SEARCH_BASE if page_num == 1 else f"{SEARCH_BASE}_Desde_{offset + 1}"
                logger.debug(f"Scraping MercadoLibre page {page_num}: {url}")

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(delay * 1000)

                    # Wait for listings to load - try multiple selectors
                    try:
                        page.wait_for_selector('li.ui-search-layout__item, .poly-card, .ui-search-result', timeout=10000)
                    except PlaywrightTimeout:
                        logger.info(f"No MercadoLibre listings found on page {page_num}")
                        break

                    # Get all listing cards - try multiple selectors
                    cards = page.query_selector_all('li.ui-search-layout__item')
                    if not cards:
                        cards = page.query_selector_all('.poly-card')
                    if not cards:
                        cards = page.query_selector_all('.ui-search-result')

                    if not cards:
                        logger.info(f"No MercadoLibre listings found on page {page_num}, stopping")
                        break

                    logger.debug(f"Found {len(cards)} MercadoLibre listings on page {page_num}")

                    for card in cards:
                        try:
                            # Get link
                            link_elem = card.query_selector('a[href*="departamento"]') or card.query_selector('a')
                            if not link_elem:
                                continue

                            full_url = link_elem.get_attribute("href")
                            if not full_url or "mercadolibre" not in full_url:
                                continue

                            # Get price - try multiple selectors
                            price_elem = card.query_selector('.andes-money-amount__fraction')
                            if not price_elem:
                                price_elem = card.query_selector('[class*="price"]')

                            if not price_elem:
                                continue

                            price = parse_price(price_elem.inner_text())
                            if price is None:
                                continue

                            # Get rooms from attributes
                            rooms = None
                            card_text = card.inner_text()
                            rooms = parse_rooms(card_text)

                            # Get expensas (usually not in card, but try)
                            expensas = parse_expensas(card_text)

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
                            logger.warning(f"Error parsing MercadoLibre card: {e}")
                            continue

                except PlaywrightTimeout:
                    logger.warning(f"Timeout on MercadoLibre page {page_num}")
                    break
                except Exception as e:
                    logger.error(f"Error on MercadoLibre page {page_num}: {e}")
                    break

            browser.close()

    except Exception as e:
        logger.error(f"Failed to initialize Playwright for MercadoLibre: {e}")

    logger.info(f"Successfully scraped {len(listings)} listings from MercadoLibre")
    return listings
