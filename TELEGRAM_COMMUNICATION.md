# How This Project Communicates with Telegram

## Overview

This bot uses the **Telegram Bot API** to send messages. It's a one-way communication (bot → user) using HTTP POST requests.

## Architecture

```
Your Bot Script → HTTP POST Request → Telegram Bot API → Telegram Servers → Your Telegram Chat
```

## How It Works

### 1. Bot Token Authentication

Every Telegram bot has a unique **bot token** obtained from [@BotFather](https://t.me/BotFather):

- The token identifies your bot to Telegram's servers
- Format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
- Stored in environment variable: `TELEGRAM_BOT_TOKEN`

### 2. Chat ID Identification

The **chat_id** specifies WHERE to send the message:

- Can be a numeric ID (e.g., `123456789`) or username (e.g., `@yourusername`)
- Stored in environment variable: `TELEGRAM_CHAT_ID`
- Your bot needs to be in a conversation with this chat

### 3. Sending Messages

The bot uses the Telegram Bot API endpoint:

```
POST https://api.telegram.org/bot{TOKEN}/sendMessage
```

**Request Format:**
```json
{
  "chat_id": "your_chat_id",
  "text": "Your message text here",
  "parse_mode": "HTML"
}
```

**Code Location:** `notifier.py` - `send_message()` function

### 4. Current Implementation Details

#### Message Sending Flow:

1. **Format Message** (`notifier.py` lines 21-27):
   - Creates formatted text with apartment details
   - Uses HTML formatting for bold text

2. **HTTP Request** (`notifier.py` lines 29-38):
   - Constructs API URL with bot token
   - Sends POST request with JSON payload
   - Includes retry logic for reliability

3. **Error Handling** (`notifier.py` lines 36-54):
   - Retries up to 3 times on failure
   - Logs errors for debugging
   - Validates API response

## Communication Flow Diagram

```
┌─────────────────┐
│   main.py       │
│   (scrapes &    │
│    filters)     │
└────────┬────────┘
         │
         │ calls send_message(TOKEN, CHAT_ID, ap)
         ▼
┌─────────────────┐
│  notifier.py    │
│  send_message() │
└────────┬────────┘
         │
         │ HTTP POST
         ▼
┌──────────────────────────┐
│ Telegram Bot API         │
│ api.telegram.org         │
│ /bot{TOKEN}/sendMessage  │
└────────┬─────────────────┘
         │
         │ Validates token & chat_id
         │ Delivers message
         ▼
┌─────────────────┐
│  Your Telegram  │
│  Chat/Channel   │
└─────────────────┘
```

## Getting Your Chat ID

### Method 1: Start a conversation
1. Start a chat with your bot on Telegram
2. Send any message to your bot
3. Visit: `https://api.telegram.org/bot{YOUR_TOKEN}/getUpdates`
4. Look for `"chat":{"id":123456789}` in the response

### Method 2: Use @userinfobot
1. Send a message to [@userinfobot](https://t.me/userinfobot)
2. It will reply with your numeric chat ID

### Method 3: For channels/groups
- Use numeric ID (negative numbers for groups)
- Get from `getUpdates` API after bot joins

## Bot Communication Modes

### Current: **One-Way (Push Notifications)**
- Bot sends messages to you
- No commands or user input
- Perfect for notifications/alerts

### Alternative: **Two-Way (Interactive Bot)**
If you wanted to add commands/interactivity:

```python
# You would need to:
1. Set up webhook or polling to receive messages
2. Use getUpdates endpoint to read incoming messages
3. Process commands like /start, /help, /status
4. Use python-telegram-bot library (recommended)
```

**Example with python-telegram-bot:**
```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Bot started!')

app = Application.builder().token("YOUR_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

## API Rate Limits

Telegram Bot API limits:
- **20 messages per second** to the same group
- **30 messages per second** to different chats
- Your bot sends messages sequentially, so you're well within limits

## Security Considerations

✅ **What we're doing right:**
- Token stored in environment variable (not in code)
- Using HTTPS for all API calls
- Retry logic prevents spam on errors

⚠️ **Keep secure:**
- Never share your bot token publicly
- Keep `.env` file private (already in `.gitignore`)
- Rotate token if accidentally exposed

## API Response Format

**Success Response:**
```json
{
  "ok": true,
  "result": {
    "message_id": 123,
    "from": {...},
    "chat": {...},
    "date": 1234567890,
    "text": "Your message"
  }
}
```

**Error Response:**
```json
{
  "ok": false,
  "error_code": 400,
  "description": "Bad Request: chat not found"
}
```

Our code checks `result.get("ok")` and handles errors appropriately.

## Dependencies

- **requests**: HTTP library for API calls
- No Telegram-specific library needed (using raw HTTP API)

If you wanted more features, consider:
- `python-telegram-bot`: Full-featured Telegram bot library
- `aiogram`: Async Telegram bot framework

## Testing Your Bot

```bash
# Test from command line
curl -X POST \
  "https://api.telegram.org/bot{YOUR_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"YOUR_CHAT_ID","text":"Test message"}'
```

Or simply run your bot - it will send messages automatically when matches are found!
