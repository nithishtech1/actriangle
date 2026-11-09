"""Tasks 12-13 helper.
1) python tools/telegram_check.py            -> lists chat IDs the bot has seen (message the bot first!)
2) python tools/telegram_check.py send       -> sends a test message using TELEGRAM_CHAT_ID from .env
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

token = config.TELEGRAM_TOKEN
if not token:
    sys.exit("TELEGRAM_TOKEN is empty. Copy .env.example to .env and paste the BotFather token.")
base = f"https://api.telegram.org/bot{token}"

try:
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        if not config.TELEGRAM_CHAT_ID:
            sys.exit("TELEGRAM_CHAT_ID is empty. Run this script without 'send' first to find it.")
        r = requests.post(f"{base}/sendMessage",
                          json={"chat_id": config.TELEGRAM_CHAT_ID,
                                "text": "ClimaTwin test alert: Telegram works."},
                          timeout=10)
        print("OK, check Telegram." if r.ok else f"Failed: {r.status_code} {r.text}")
    else:
        r = requests.get(f"{base}/getUpdates", timeout=10).json()
        if not r.get("ok"):
            sys.exit(f"Telegram error (is the token right?): {r}")
        seen = {}
        for u in r.get("result", []):
            chat = (u.get("message") or {}).get("chat")
            if chat:
                seen[chat["id"]] = chat.get("first_name") or chat.get("title") or ""
        if not seen:
            print("No messages yet. Open your bot in Telegram, press Start, send 'hi', then run this again.")
        for cid, name in seen.items():
            print(f"chat id: {cid}   ({name})")
except requests.RequestException as e:
    sys.exit(f"Could not reach Telegram (internet or a blocked network?): {e.__class__.__name__}. "
             "Try a phone hotspot.")
