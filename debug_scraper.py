import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.argenprop.com"
SEARCH_BASE = "https://www.argenprop.com/departamentos/alquiler/la-plata"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def debug_first_listing():
    """Debug the HTML structure of the first listing."""
    
    print("="*70)
    print("🔍 DEBUGGING ARGENPROP SCRAPER")
    print("="*70)
    
    print("\n⏳ Fetching first page...")
    r = requests.get(SEARCH_BASE, headers=HEADERS, timeout=15)
    
    if r.status_code != 200:
        print(f"❌ Failed to fetch page: {r.status_code}")
        return
    
    soup = BeautifulSoup(r.text, "lxml")
    cards = soup.select("div.listing__item")
    
    print(f"✅ Found {len(cards)} listings\n")
    
    if not cards:
        print("❌ No listings found!")
        return
    
    # Debug first 3 listings
    for idx, card in enumerate(cards[:3], 1):
        print("="*70)
        print(f"LISTING #{idx}")
        print("="*70)
        
        # Link
        link_elem = card.select_one("a")
        if link_elem:
            link = link_elem.get("href", "N/A")
            print(f"🔗 URL: {BASE_URL + link if link.startswith('/') else link}")
        
        # Price element
        price_elem = card.select_one(".card__price")
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            print(f"\n💲 Raw price text: '{price_text}'")
            
            # Try to parse it
            text = price_text.replace("USD", "").replace("US$", "").replace("$", "").strip()
            numbers = re.findall(r"\d+", text.replace(".", ""))
            parsed_price = int("".join(numbers)) if numbers else None
            print(f"   Parsed price: ${parsed_price:,}" if parsed_price else "   Parsed price: None")
        else:
            print("❌ No price element found")
        
        # Full text (for rooms and expensas)
        full_text = card.get_text(" ", strip=True)
        print(f"\n📝 Full card text (first 300 chars):")
        print(f"   {full_text[:300]}...")
        
        # Parse rooms
        rooms_match = re.search(r"(\d)\s*amb", full_text.lower())
        if rooms_match:
            print(f"\n🛏️  Rooms: {rooms_match.group(1)} ambientes")
        else:
            print("\n🛏️  Rooms: Not found")
        
        # Parse expensas
        exp_match = re.search(r"expensas?\s*[:$]*\s*\$?\s*([\d\.]+)", full_text.lower())
        if exp_match:
            exp_str = exp_match.group(1).replace(".", "")
            print(f"💰 Expensas: ${int(exp_str):,}")
        else:
            print("💰 Expensas: Not found")
        
        print()
    
    print("="*70)
    print("✅ Debug complete!")
    print("="*70)

if __name__ == "__main__":
    debug_first_listing()