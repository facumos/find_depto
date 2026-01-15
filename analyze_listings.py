import os
import logging
from scrappers.argenprop import scrape_argenprop
from filters import matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your current criteria
CRITERIA = {
    "max_price": 600000,
    "min_rooms": 2,
    "max_expensas": 100000
}

def analyze_listings():
    """Analyze scraped listings to understand why nothing matches."""
    
    print("\n" + "="*70)
    print("📊 ANALYZING ARGENPROP LISTINGS")
    print("="*70)
    
    print("\n🔍 Your current criteria:")
    print(f"   • Max Price: ${CRITERIA['max_price']:,}")
    print(f"   • Min Rooms: {CRITERIA['min_rooms']}")
    print(f"   • Max Expensas: ${CRITERIA['max_expensas']:,}")
    
    print("\n⏳ Scraping first 2 pages (this may take a moment)...")
    listings = scrape_argenprop(max_pages=2)
    
    print(f"\n✅ Found {len(listings)} total listings\n")
    
    # Filter out listings with missing data
    complete = [l for l in listings if l['price'] and l['rooms'] and l['expensas']]
    incomplete = len(listings) - len(complete)
    
    print(f"📋 Listings with complete data: {len(complete)}")
    print(f"⚠️  Listings with missing data: {incomplete}")
    
    if not complete:
        print("\n❌ No listings with complete data found!")
        print("   Try scraping more pages or check the scraper.")
        return
    
    # Statistics
    prices = [l['price'] for l in complete]
    expensas = [l['expensas'] for l in complete]
    rooms = [l['rooms'] for l in complete]
    
    print("\n" + "="*70)
    print("📈 PRICE ANALYSIS")
    print("="*70)
    print(f"   Min Price:     ${min(prices):,}")
    print(f"   Max Price:     ${max(prices):,}")
    print(f"   Average Price: ${int(sum(prices)/len(prices)):,}")
    print(f"   Median Price:  ${sorted(prices)[len(prices)//2]:,}")
    
    print("\n" + "="*70)
    print("💰 EXPENSAS ANALYSIS")
    print("="*70)
    print(f"   Min Expensas:     ${min(expensas):,}")
    print(f"   Max Expensas:     ${max(expensas):,}")
    print(f"   Average Expensas: ${int(sum(expensas)/len(expensas)):,}")
    print(f"   Median Expensas:  ${sorted(expensas)[len(expensas)//2]:,}")
    
    print("\n" + "="*70)
    print("🛏️  ROOMS DISTRIBUTION")
    print("="*70)
    from collections import Counter
    room_counts = Counter(rooms)
    for room, count in sorted(room_counts.items()):
        bar = "█" * (count * 30 // max(room_counts.values()))
        print(f"   {room} amb: {bar} ({count} listings)")
    
    # Check how many would match with different criteria
    print("\n" + "="*70)
    print("🎯 CRITERIA TESTING")
    print("="*70)
    
    scenarios = [
        {"max_price": 600000, "min_rooms": 2, "max_expensas": 100000, "name": "Current (very strict)"},
        {"max_price": 800000, "min_rooms": 2, "max_expensas": 150000, "name": "Relaxed"},
        {"max_price": 1000000, "min_rooms": 2, "max_expensas": 200000, "name": "More relaxed"},
        {"max_price": 600000, "min_rooms": 1, "max_expensas": 100000, "name": "Current but 1+ rooms"},
        {"max_price": 800000, "min_rooms": 1, "max_expensas": 100000, "name": "Higher price, same expensas"},
    ]
    
    for scenario in scenarios:
        matched = [l for l in complete if matches(l, scenario)]
        print(f"\n   {scenario['name']}:")
        print(f"      Price ≤ ${scenario['max_price']:,}, Rooms ≥ {scenario['min_rooms']}, Expensas ≤ ${scenario['max_expensas']:,}")
        print(f"      ✓ Matches: {len(matched)} listings")
    
    # Show some example listings
    print("\n" + "="*70)
    print("📋 SAMPLE LISTINGS (showing 10 cheapest)")
    print("="*70)
    
    sorted_by_price = sorted(complete, key=lambda x: x['price'])[:10]
    
    for i, ap in enumerate(sorted_by_price, 1):
        total = ap['price'] + ap['expensas']
        match = "✅" if matches(ap, CRITERIA) else "❌"
        print(f"\n{i}. {match} ${ap['price']:,} + ${ap['expensas']:,} = ${total:,} | {ap['rooms']} amb")
        print(f"   {ap['url']}")
        
        # Explain why it doesn't match
        if not matches(ap, CRITERIA):
            reasons = []
            if ap['price'] > CRITERIA['max_price']:
                reasons.append(f"Price too high (${ap['price']:,} > ${CRITERIA['max_price']:,})")
            if ap['rooms'] < CRITERIA['min_rooms']:
                reasons.append(f"Too few rooms ({ap['rooms']} < {CRITERIA['min_rooms']})")
            if ap['expensas'] > CRITERIA['max_expensas']:
                reasons.append(f"Expensas too high (${ap['expensas']:,} > ${CRITERIA['max_expensas']:,})")
            print(f"   Why: {', '.join(reasons)}")
    
    # Recommendations
    print("\n" + "="*70)
    print("💡 RECOMMENDATIONS")
    print("="*70)
    
    # Find a reasonable criteria that would match some listings
    median_price = sorted(prices)[len(prices)//2]
    median_expensas = sorted(expensas)[len(expensas)//2]
    
    print(f"\n   Based on the market, consider:")
    print(f"   • Max Price: ${int(median_price * 1.2):,} (current: ${CRITERIA['max_price']:,})")
    print(f"   • Max Expensas: ${int(median_expensas * 1.2):,} (current: ${CRITERIA['max_expensas']:,})")
    print(f"   • Min Rooms: {CRITERIA['min_rooms']} (keep as is)")
    
    suggested = {
        "max_price": int(median_price * 1.2),
        "min_rooms": CRITERIA['min_rooms'],
        "max_expensas": int(median_expensas * 1.2)
    }
    
    suggested_matches = [l for l in complete if matches(l, suggested)]
    print(f"\n   This would match: {len(suggested_matches)} listings")
    
    print("\n" + "="*70)
    print("\n✅ Analysis complete! Update your criteria in main.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    analyze_listings()