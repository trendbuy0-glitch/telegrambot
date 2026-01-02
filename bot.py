import os
import json
import requests
import time
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("TrendBuyFinderBot")
CHAT_ID = "-1003544601340"
AFFILIATE_ID = "trendbuy013-21"

PRICES_FILE = "prices.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ---------------------------------------------------
# TELEGRAM
# ---------------------------------------------------

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def send_photo(image_url, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {"chat_id": CHAT_ID, "photo": image_url, "caption": caption, "parse_mode": "Markdown"}
    requests.post(url, data=data)

# ---------------------------------------------------
# UTILS
# ---------------------------------------------------

def safe_float(text):
    if not text:
        return None
    clean = text.replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(clean)
    except:
        return None

def extract_coupon(el, base_price):
    if not el or not base_price:
        return 0.0
    text = el.get_text(strip=True).lower()
    coupon = 0.0

    if "%" in text:
        try:
            perc = text.replace("risparmia", "").replace("coupon", "").replace("%", "").strip()
            coupon = base_price * (float(perc) / 100)
        except:
            pass

    if "€" in text:
        try:
            fixed = text.replace("coupon", "").replace("€", "").strip()
            coupon = max(coupon, float(fixed))
        except:
            pass

    return round(coupon, 2)

# ---------------------------------------------------
# SCRAPER (ATTUALE)
# ---------------------------------------------------

def scrape_search(url, pages=5):
    products = {}

    for page in range(1, pages + 1):
        paged = f"{url}&page={page}"

        try:
            r = requests.get(paged, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
        except:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".s-result-item[data-asin]")

        for item in items:
            asin = item.get("data-asin")
            if not asin:
                continue

            title_el = (
                item.select_one("h2 a span") or
                item.select_one("span.a-size-base-plus.a-color-base") or
                item.select_one("span.a-size-medium.a-color-base") or
                item.select_one("h2 span")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            img_el = item.select_one("img.s-image")
            image = img_el.get("src") if img_el else None

            base_price = None
            price_el = item.select_one(".a-price .a-offscreen")
            if price_el:
                base_price = safe_float(price_el.get_text(strip=True))

            if base_price is None:
                whole = item.select_one("span.a-price-whole")
                frac = item.select_one("span.a-price-fraction")
                if whole:
                    price_text = whole.get_text(strip=True)
                    if frac:
                        price_text += "." + frac.get_text(strip=True)
                    base_price = safe_float(price_text)

            if base_price is None:
                continue

            coupon_el = (
                item.select_one(".s-coupon-highlight-color") or
                item.select_one("span.a-color-success")
            )
            coupon = extract_coupon(coupon_el, base_price)

            final_price = base_price - coupon

            products[asin] = {
                "title": title,
                "image": image,
                "base_price": round(base_price, 2),
                "coupon": coupon,
                "final_price": round(final_price, 2),
                "url": f"https://www.amazon.it/dp/{asin}"
            }

        time.sleep(1)

    return products

# ---------------------------------------------------
# CATEGORIE (IDENTICHE A generate_prices.py)
# ---------------------------------------------------

SEARCH_CATEGORIES = {
    "alimentatori": "https://www.amazon.it/s?k=alimentatore+pc",
    "gpu": "https://www.amazon.it/s?k=scheda+video",
    "cpu": "https://www.amazon.it/s?k=cpu+intel+amd",
    "dissipatori": "https://www.amazon.it/s?k=dissipatore+cpu",
    "mobo": "https://www.amazon.it/s?k=scheda+madre",
    "case": "https://www.amazon.it/s?k=case+pc",
    "ram": "https://www.amazon.it/s?k=ram+ddr5",
    "ventole": "https://www.amazon.it/s?k=ventole+pc"
}

# ---------------------------------------------------
# FORMAT MESSAGE
# ---------------------------------------------------

def format_message(asin, info, old_price):
    title = info["title"]
    final_price = info["final_price"]
    coupon = info["coupon"]

    affiliate_link = f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_ID}"

    discount_percent = round((old_price - final_price) / old_price * 100)

    coupon_text = f"🎟️ *Coupon:* -{coupon:.2f}€\n" if coupon > 0 else ""

    return f"""
😱 *OFFERTA TECH!*

📦 *{title}*
💶 *Prezzo vecchio:* {old_price:.2f}€
💥 *Prezzo nuovo:* *{final_price:.2f}€*
📉 *Sconto:* -{discount_percent}%

{coupon_text}
👉 [Vai su Amazon]({affiliate_link})
"""

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

if __name__ == "__main__":
    send_message("🔍 Controllo offerte in corso...")

    with open(PRICES_FILE, "r", encoding="utf-8") as f:
        old_data = json.load(f)

    new_data = {}
    for name, url in SEARCH_CATEGORIES.items():
        scraped = scrape_search(url)
        new_data.update(scraped)

    # 🔥 STAMPA TUTTI I PRODOTTI TROVATI
    send_message("📦 *Prodotti trovati nello scraping:*")
    for asin, info in new_data.items():
        msg = (
            f"ASIN: `{asin}`\n"
            f"Titolo: {info['title']}\n"
            f"Prezzo base: {info['base_price']}€\n"
            f"Prezzo finale: {info['final_price']}€\n"
            f"Coupon: {info['coupon']}€\n"
            f"URL: {info['url']}\n"
            "-------------------------"
        )
        send_message(msg)
        time.sleep(0.3)

    offerte_trovate = 0

    for asin, new_info in new_data.items():
        if asin not in old_data:
            continue

        old_price = old_data[asin]["base_price"]
        new_final = new_info["final_price"]
        new_coupon = new_info["coupon"]

        if new_final >= old_price and new_coupon == 0:
            continue

        caption = format_message(asin, new_info, old_price)

        if new_info["image"]:
            send_photo(new_info["image"], caption)
        else:
            send_message(caption)

        offerte_trovate += 1
        time.sleep(2)

    if offerte_trovate == 0:
        send_message("✅ Nessuna offerta da segnalare.")
