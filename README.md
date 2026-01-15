# Apartment Bot - Telegram Apartment Finder

A Python bot that scrapes apartment listings from ArgenProp and sends notifications via Telegram when listings match your criteria.

## Features

- Scrapes apartment listings from ArgenProp
- Filters listings based on price, rooms, and expenses
- Sends notifications via Telegram
- Tracks already sent listings to avoid duplicates
- Comprehensive error handling and logging

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

- `TELEGRAM_BOT_TOKEN`: Get this from [@BotFather](https://t.me/BotFather) on Telegram
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (can be username or numeric ID)
- `MAX_PRICE`: Maximum rental price (default: 600000)
- `MIN_ROOMS`: Minimum number of rooms (default: 2)
- `MAX_EXPENSAS`: Maximum expenses (default: 100000)
- `MAX_PAGES`: Number of pages to scrape (default: 5)

### 3. Run the Bot

```bash
python main.py
```

## Production Deployment

### Using cron (Linux/macOS)

Add to crontab to run every hour:

```bash
0 * * * * cd /path/to/apartment_bot && /usr/bin/python3 main.py >> /path/to/apartment_bot/cron.log 2>&1
```

### Using systemd (Linux)

Create `/etc/systemd/system/apartment-bot.service`:

```ini
[Unit]
Description=Apartment Bot
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/apartment_bot
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/apartment_bot/main.py
```

Create timer `/etc/systemd/system/apartment-bot.timer`:

```ini
[Unit]
Description=Run Apartment Bot hourly
Requires=apartment-bot.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable apartment-bot.timer
sudo systemctl start apartment-bot.timer
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

## Important Notes

- **Security**: Never commit your `.env` file or `sent.json` to version control
- **Rate Limiting**: The bot includes delays between requests to be respectful to the website
- **Logging**: Logs are written to `bot.log` and stdout
- **Data Persistence**: Already sent listings are stored in `sent.json`

## Troubleshooting

- Check `bot.log` for detailed error messages
- Verify your Telegram bot token is correct
- Ensure your chat ID is correct (can use @username or numeric ID)
- Check network connectivity if scraping fails
