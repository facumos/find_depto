#!/usr/bin/env python3
"""Debug ZonaProp specifically."""

from playwright.sync_api import sync_playwright

url = "https://www.zonaprop.com.ar/departamentos-alquiler-la-plata.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    print(f"Navigating to {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    print(f"Page title: {page.title()}")
    print(f"URL: {page.url}")

    # Check for captcha or block
    content = page.content()
    if "captcha" in content.lower() or "robot" in content.lower():
        print("CAPTCHA or robot check detected!")

    # Try to find any listings
    selectors_to_try = [
        '[data-qa="posting"]',
        '.postings-container',
        '.postings-wrapper',
        '.CardContainer-sc',
        'div[data-posting-type]',
        'article',
        'div.posting',
    ]

    for sel in selectors_to_try:
        elements = page.query_selector_all(sel)
        print(f"Selector '{sel}': {len(elements)} elements")

    # Print page text sample
    body = page.query_selector('body')
    if body:
        text = body.inner_text()[:2000]
        print(f"\nPage text sample:\n{text}")

    # Save screenshot for debugging
    page.screenshot(path="zonaprop_debug.png")
    print("\nScreenshot saved to zonaprop_debug.png")

    browser.close()
