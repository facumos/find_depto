#!/usr/bin/env python3
"""Debug script to test scrappers and see what's happening."""

import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HEADERS_BASIC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

HEADERS_FULL = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Linux"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def test_zonaprop():
    """Test ZonaProp scraping."""
    print("\n" + "=" * 60)
    print("Testing ZonaProp")
    print("=" * 60)

    url = "https://www.zonaprop.com.ar/departamentos-alquiler-la-plata.html"

    try:
        r = requests.get(url, headers=HEADERS_FULL, timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Response length: {len(r.text)}")

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")

            # Try different selectors
            selectors = [
                '[data-qa="posting"]',
                '.postingCard',
                'div[data-posting-type]',
                '.posting-card',
                'article',
                '.CardContainer',
            ]

            for sel in selectors:
                cards = soup.select(sel)
                print(f"Selector '{sel}': {len(cards)} elements")

            # Print a sample of the HTML structure
            print("\nFirst 2000 chars of body:")
            body = soup.find('body')
            if body:
                print(body.get_text()[:2000])
        else:
            print(f"Response text: {r.text[:1000]}")

    except Exception as e:
        print(f"Error: {e}")


def test_mercadolibre():
    """Test MercadoLibre scraping."""
    print("\n" + "=" * 60)
    print("Testing MercadoLibre")
    print("=" * 60)

    url = "https://inmuebles.mercadolibre.com.ar/departamentos/alquiler/la-plata"

    try:
        r = requests.get(url, headers=HEADERS_FULL, timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Response length: {len(r.text)}")

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")

            # Try different selectors
            selectors = [
                'li.ui-search-layout__item',
                '.poly-card',
                '[data-testid="result-item"]',
                '.ui-search-result',
                'article',
                '.ui-search-layout__item',
                'ol.ui-search-layout li',
            ]

            for sel in selectors:
                cards = soup.select(sel)
                print(f"Selector '{sel}': {len(cards)} elements")

            # Look for any listing-like structure
            print("\nSearching for links with 'departamento':")
            links = soup.find_all('a', href=lambda h: h and 'departamento' in h.lower() if h else False)
            print(f"Found {len(links)} links")
            for link in links[:5]:
                print(f"  - {link.get('href', '')[:80]}")

            # Print sample HTML
            print("\nFirst 3000 chars of HTML:")
            print(r.text[:3000])

    except Exception as e:
        print(f"Error: {e}")


def test_argenprop():
    """Test ArgenProp scraping (reference - should work)."""
    print("\n" + "=" * 60)
    print("Testing ArgenProp (reference)")
    print("=" * 60)

    url = "https://www.argenprop.com/departamentos/alquiler/la-plata"

    try:
        r = requests.get(url, headers=HEADERS_BASIC, timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Response length: {len(r.text)}")

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("div.listing__item")
            print(f"Found {len(cards)} listings")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_argenprop()
    test_zonaprop()
    test_mercadolibre()
