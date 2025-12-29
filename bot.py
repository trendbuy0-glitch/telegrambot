import os
import json
import requests
from bs4 import BeautifulSoup
import time

BOT_TOKEN = os.getenv("TrendBuyFinderBot")
CHAT_ID = "-1003544601340"
AFFILIATE_ID = "trendbuy013-21"

CATEGORIES = [
    "https://www.amazon.it/gp/bestsellers/computers/",
    "https://www.amazon.it/gp/bestsellers/electronics/",
    "https://www.amazon.it/gp/bestsellers/computers/430203031/",
    "https://www.amazon.it/gp/bestsellers/computers/460150031/",
    "https://www.amazon.it/gp/bestsellers/electronics/473295031/",
    "https://www.amazon.it/gp/bestsellers/computers/460152031/",
]

PRICES_FILE = "prices.json"

def send_status_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "🔍 Sto cercando nuove offerte tech...",
    }
    requests.post(url, data=data)

def load_prices():
    if not os.path.exists(PRICES_FILE):
        return {}
    with open(PRICES_FILE, "r") as f:
        return json.load(f)


def save_prices(data):
    with open(PRICES_FILE, "w") as f:
        json.dump(data, f, indent=4)


def extract_products():
    headers = {"User-Agent": "Mozilla/5.0"}
    products = []

    for url in CATEGORIES:
        html = requests.get(url, headers=headers).text
        soup = BeautifulSoup(html, "html.parser")

        items = soup.select(".zg-grid-general-faceout, .a-section.a-spacing-none.p13n-asin")

        for item in items:
            title_el = item.select_one(".p13n-sc-truncate, .a-link-normal")
            price_el = item.select_one(".p13n-sc-price, .a-price-whole")
            old_price_el = item.select_one(".a-text-price span")
            img_el = item.select_one("img")

            link_el = item.select_one("a.a-link-normal")

            if not title_el or not price_el or not link_el:
                continue

            title = title_el.get_text(strip=True)
            price = price_el.get_text(strip=True).replace("€", "").replace(",", ".")
            try:
                price = float(price)
            except:
                continue

            old_price = None
            if old_price_el:
                try:
                    old_price = float(old_price_el.get_text(strip=True).replace("€", "").replace(",", "."))
                except:
                    old_price = None

            if "dp" not in link_el["href"]:
                continue

            asin = link_el["href"].split("/dp/")[1].split("/")[0]

            image = img_el["src"] if img_el else None

            # Check coupon
            coupon = None
            coupon_el = item.select_one(".s-coupon-unclipped")
            if coupon_el:
                coupon = coupon_el.get_text(strip=True)

            products.append({
                "asin": asin,
                "title": title,
                "price": price,
                "old_price": old_price,
                "image": image,
                "coupon": coupon
            })

    return products


def format_message(product, old_price):
    affiliate_link = f"https://www.amazon.it/dp/{product['asin']}?tag={AFFILIATE_ID}"

    discount_text = ""
    if old_price and old_price > product["price"]:
        discount = round((old_price - product["price"]) / old_price * 100)
        discount_text = f"📉 *Sconto:* -{discount}%\n"

    coupon_text = ""
    if product["coupon"]:
        coupon_text = f"🎟️ *Coupon disponibile:* {product['coupon']}\n"

    return f"""
🔥 *RIBASSO PREZZO TECH!*

📦 *{product['title']}*

💰 *Nuovo prezzo:* {product['price']}€
💸 *Prima:* {old_price}€

{discount_text}{coupon_text}

👉 {affiliate_link}
"""



def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)


if __name__ == "__main__":
    send_status_message()  # <--- MESSAGGIO DI STATO

    old_prices = load_prices()
    new_prices = {}
    products = extract_products()


    for p in products:
        asin = p["asin"]
        new_prices[asin] = p["price"]

        if asin in old_prices:
            if p["price"] < old_prices[asin]:
                msg = format_message(p, old_prices[asin])
                send_message(msg)
                time.sleep(2)

    save_prices(new_prices)
