"""Opt-in Telegram delivery. Never include the bot token in errors."""
from dataclasses import dataclass
import requests
import config


@dataclass(frozen=True)
class Delivery:
    ok: bool
    detail: str


def send_telegram(message, *, token=None, chat_id=None, session=None):
    token = config.TELEGRAM_TOKEN if token is None else token
    chat_id = config.TELEGRAM_CHAT_ID if chat_id is None else chat_id
    if not token or not chat_id:
        return Delivery(False, "Configure TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env.")
    try:
        response = (session or requests).post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4096]}, timeout=10,
        )
        response.raise_for_status()
        if response.json().get("ok") is True:
            return Delivery(True, "Telegram alert delivered.")
        return Delivery(False, "Telegram declined the message; check the bot/chat settings.")
    except (requests.RequestException, ValueError, AttributeError):
        return Delivery(False, "Telegram unavailable; check network and bot/chat settings.")
