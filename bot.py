import os
import json
import requests
import time

BOT_TOKEN = os.getenv("TrendBuyFinderBot")
CHAT_ID = "-1003544601340"
AFFILIATE_ID = "trendbuy013-21"

NEW_PRICES_FILE = "prices.json"
OLD_PRICES_FILE = "old_prices.json"


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def send_photo(product, caption):
    if not product.get("image"):
        send_message(caption)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {
        "chat_id": CHAT_ID,
        "photo": product["image"],
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


def format_message(asin, info_old, info_new):
    base_price = info_new["base_price"]
    final_price = info_new["price"]
    coupon = info_new["coupon"]
    old_price = info_old["price"]

    affiliate_link = f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_ID}"

    # Calcolo sconto
    discount_percent = 0
    if old_price > 0:
        discount_percent = round((old_price - final_price) / old_price * 100)

    coupon_text = ""
    if coupon > 0:
        coupon_text = f"🎟️ *Coupon:* -{coupon:.2f}€\n"

    return f"""
😱 *PREZZONE TECH!*

📦 *ASIN:* `{asin}`
💶 *Prezzo base:* {base_price:.2f}€
🧾 *Prezzo precedente:* {old_price:.2f}€
💥 *Prezzo finale:* *{final_price:.2f}€*
📉 *Sconto:* -{discount_percent}%

{coupon_text}
👉 [Vai su Amazon]({affiliate_link})
"""


if __name__ == "__main__":
    send_message("🔍 Controllo ribassi in corso...")

    # Carica nuovi prezzi (scraper)
    with open(NEW_PRICES_FILE, "r") as f:
        new_data = json.load(f)

    # Carica vecchi prezzi
    if os.path.exists(OLD_PRICES_FILE):
        with open(OLD_PRICES_FILE, "r") as f:
            old_data = json.load(f)
    else:
        old_data = {}

    ribassi = 0

    for asin, info_new in new_data.items():
        if asin in old_data:
            info_old = old_data[asin]

            # Se il prezzo finale è sceso → invia messaggio
            if info_new["price"] < info_old["price"]:
                msg = format_message(asin, info_old, info_new)
                send_message(msg)
                ribassi += 1
                time.sleep(2)

    if ribassi == 0:
        send_message("✅ Nessun ribasso trovato in questo giro.")

    # Salva nuovi prezzi come vecchi
    with open(OLD_PRICES_FILE, "w") as f:
        json.dump(new_data, f, indent=4)
