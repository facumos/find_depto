import requests
import json

TOKEN = "8515341054:AAGLbPYICYimfzknKl5MaC8QdmfwvevCaXs"

print("="*60)
print("🔍 FINDING YOUR TELEGRAM CHAT ID")
print("="*60)

print("\n📱 STEP 1: Send a message to your bot")
print("   - Open Telegram")
print("   - Search for your bot")
print("   - Send it any message (like 'hello')")
print("\n⏸️  Press ENTER after you've sent a message to the bot...")
input()

print("\n🔍 Fetching updates from Telegram...")

try:
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    if not data.get("ok"):
        print(f"❌ Error: {data.get('description', 'Unknown error')}")
        print("\n💡 Make sure your TOKEN is correct")
    else:
        updates = data.get("result", [])
        
        if not updates:
            print("❌ No messages found!")
            print("\n💡 Troubleshooting:")
            print("   1. Make sure you sent a message to your bot")
            print("   2. Try sending another message")
            print("   3. Run this script again")
        else:
            print(f"✅ Found {len(updates)} update(s)!\n")
            
            # Extract all unique chat IDs
            chat_ids = set()
            for update in updates:
                if "message" in update:
                    chat = update["message"].get("chat", {})
                    chat_ids.add((
                        chat.get("id"),
                        chat.get("type"),
                        chat.get("title", chat.get("first_name", "Unknown"))
                    ))
                elif "channel_post" in update:
                    chat = update["channel_post"].get("chat", {})
                    chat_ids.add((
                        chat.get("id"),
                        chat.get("type"),
                        chat.get("title", "Channel")
                    ))
            
            print("📋 AVAILABLE CHAT IDs:")
            print("-" * 60)
            
            for chat_id, chat_type, name in chat_ids:
                print(f"\n💬 {chat_type.upper()}: {name}")
                print(f"   Chat ID: {chat_id}")
                print(f"   Use this in your code: CHAT_ID = \"{chat_id}\"")
            
            print("\n" + "="*60)
            print("✅ INSTRUCTIONS:")
            print("="*60)
            
            # Get the first (most recent) chat ID
            first_id = list(chat_ids)[0][0]
            
            print(f"\n1️⃣  Update your code with:")
            print(f'   CHAT_ID = "{first_id}"')
            print("\n2️⃣  Or set environment variable:")
            print(f'   export TELEGRAM_CHAT_ID="{first_id}"')
            print("\n3️⃣  Run the test again:")
            print("   python test_bot.py")
            print("\n" + "="*60)
            
            # Show full JSON for debugging
            print("\n🔧 DEBUG INFO (Full Response):")
            print("-" * 60)
            print(json.dumps(updates[-1], indent=2))
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)