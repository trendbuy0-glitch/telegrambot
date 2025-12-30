import os
import json
import requests
import time

BOT_TOKEN = os.getenv("TrendBuyFinderBot")
CHAT_ID = "-1003544601340"
AFFILIATE_ID = "trendbuy013-21"

PRICES_FILE = "prices.json"


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def send_photo(image_url, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {
        "chat_id": CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def format_message(asin, info):
    title = info.get("title", f"ASIN {asin}")
    base_price = info.get("base_price", info["price"])
    final_price = info["price"]
    coupon = info.get("coupon", 0)

    affiliate_link = f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_ID}"

    # Calcolo sconto
    discount_percent = 0
    if base_price > 0:
        discount_percent = round((base_price - final_price) / base_price * 100)

    coupon_text = ""
    if coupon > 0:
        coupon_text = f"🎟️ *Coupon:* -{coupon:.2f}€\n"

    return f"""
😱 *OFFERTA TECH!*

📦 *{title}*
💶 *Prezzo base:* {base_price:.2f}€
💥 *Prezzo finale:* *{final_price:.2f}€*
📉 *Sconto:* -{discount_percent}%

{coupon_text}
👉 [Vai su Amazon]({affiliate_link})
"""


if __name__ == "__main__":
    send_message("🔍 Controllo offerte in corso...")

    # Carica SOLO prices.json (database gestito da un altro workflow)
    with open(PRICES_FILE, "r") as f:
        data = json.load(f)

    offerte_trovate = 0

    for asin, info in data.items():
        # Se il workflow esterno ha già deciso che questo è un ribasso,
        # allora info["notify"] = True
        if info.get("notify") is True:
            caption = format_message(asin, info)

            if info.get("image"):
                send_photo(info["image"], caption)
            else:
                send_message(caption)

            offerte_trovate += 1
            time.sleep(2)

    if offerte_trovate == 0:
        send_message("✅ Nessuna offerta da segnalare.")
