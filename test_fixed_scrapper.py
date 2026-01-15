import logging
import sys
import os

# Add parent directory to path so we can import the scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Import from the fixed scraper in scrappers folder
# You need to replace the argenprop.py file with the fixed version
from scrappers.argenprop import scrape_argenprop

print("="*70)
print("🧪 TESTING FIXED SCRAPER")
print("="*70)

print("\n⏳ Scraping first page...")
listings = scrape_argenprop(max_pages=1)

print(f"\n✅ Found {len(listings)} listings\n")
print("="*70)
print("📋 FIRST 5 LISTINGS")
print("="*70)

for i, ap in enumerate(listings[:5], 1):
    price_str = f"${ap['price']:,}" if ap['price'] else "N/A"
    exp_str = f"${ap['expensas']:,}" if ap['expensas'] else "N/A"
    rooms_str = f"{ap['rooms']} amb" if ap['rooms'] else "N/A"
    total = ap['price'] + ap['expensas'] if (ap['price'] and ap['expensas']) else None
    total_str = f"${total:,}" if total else "N/A"
    
    print(f"\n{i}. 💰 Rent: {price_str} | Expensas: {exp_str} | Total: {total_str}")
    print(f"   🛏️  Rooms: {rooms_str}")
    print(f"   🔗 {ap['url']}")

# Statistics
complete = [l for l in listings if l['price'] and l['rooms'] and l['expensas']]
print("\n" + "="*70)
print(f"📊 STATISTICS")
print("="*70)
print(f"Total listings: {len(listings)}")
print(f"Complete data: {len(complete)}")
print(f"Missing price: {sum(1 for l in listings if not l['price'])}")
print(f"Missing rooms: {sum(1 for l in listings if not l['rooms'])}")
print(f"Missing expensas: {sum(1 for l in listings if not l['expensas'])}")

if complete:
    prices = [l['price'] for l in complete]
    expensas = [l['expensas'] for l in complete]
    totals = [l['price'] + l['expensas'] for l in complete]
    
    print(f"\n💵 Price range: ${min(prices):,} - ${max(prices):,}")
    print(f"💰 Expensas range: ${min(expensas):,} - ${max(expensas):,}")
    print(f"📊 Total cost range: ${min(totals):,} - ${max(totals):,}")
    print(f"📈 Average total: ${sum(totals)//len(totals):,}")

print("\n" + "="*70)
