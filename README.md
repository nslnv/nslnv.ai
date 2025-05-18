# Telegram Order Bot

This repository contains an example Telegram bot to manage student work orders.
It is written with `python-telegram-bot` and demonstrates basic conversation
flow with persistent storage.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   The bot requires `python-telegram-bot` version 20 or higher and `pytest` for
   running tests.

2. Set the environment variables:
   - `BOT_TOKEN` – Telegram bot token
   - `MY_CHAT_ID` – your Telegram chat ID where orders will be sent

3. Run the bot:
   ```bash
   python bot.py
   ```

## Tests

Run the unit tests with:

```bash
pytest
```

## Files

- `bot.py` – main bot implementation
- `orders.json` – JSON file where orders are stored
- `tests/` – directory with unit tests
