#!/usr/bin/env python3
"""Test the new Playwright-based scrappers."""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from scrappers.zonaprop import scrape_zonaprop
from scrappers.mercadolibre import scrape_mercadolibre
from scrappers.argenprop import scrape_argenprop


def test_argenprop():
    print("\n" + "=" * 60)
    print("Testing ArgenProp (reference)")
    print("=" * 60)
    listings = scrape_argenprop(max_pages=1)
    print(f"Found {len(listings)} listings")
    if listings:
        print(f"Sample: {listings[0]}")


def test_zonaprop():
    print("\n" + "=" * 60)
    print("Testing ZonaProp (Playwright)")
    print("=" * 60)
    listings = scrape_zonaprop(max_pages=1)
    print(f"Found {len(listings)} listings")
    if listings:
        print(f"Sample: {listings[0]}")


def test_mercadolibre():
    print("\n" + "=" * 60)
    print("Testing MercadoLibre (Playwright)")
    print("=" * 60)
    listings = scrape_mercadolibre(max_pages=1)
    print(f"Found {len(listings)} listings")
    if listings:
        print(f"Sample: {listings[0]}")


if __name__ == "__main__":
    test_argenprop()
    test_zonaprop()
    test_mercadolibre()
