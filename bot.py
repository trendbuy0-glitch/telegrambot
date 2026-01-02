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
# SCRAPING UTILS
# ---------------------------------------------------

def safe_float(text):
    if not text:
        return None
    clean = text.replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(clean)
    except:
        return None


def extract_brand_from_title(title):
    if not title:
        return None
    t = title.strip()
    if " - " in t:
        t = t.split(" - ")[0].strip()
    parts = t.split()
    if len(parts) == 1:
        return parts[0]
    return " ".join(parts[:2])


def extract_coupon(el, base_price):
    if not el or not base_price:
        return 0.0
    text = el.get_text(strip=True).lower()
    coupon = 0.0

    if "%" in text:
        try:
            perc = text.replace("risparmia", "").replace("coupon", "").replace("%", "").strip()
            perc_val = float(perc)
            coupon = base_price * (perc_val / 100)
        except:
            pass

    if "€" in text:
        try:
            fixed = text.replace("coupon", "").replace("€", "").strip()
            fixed_val = float(fixed)
            coupon = max(coupon, fixed_val)
        except:
            pass

    return round(coupon, 2)


# ---------------------------------------------------
# SCRAPING SEARCH (STESSO DI generate_prices.py)
# ---------------------------------------------------

def scrape_search(url, pages=5, category="search"):
    products = {}

    for page in range(1, pages + 1):
        paged = f"{url}&page={page}"
        print(f"[SEARCH] {category} - {paged}")

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

            # ---------------------------
            # TITOLO (fallback multipli)
            # ---------------------------
            title_el = (
                item.select_one("h2 a span") or
                item.select_one("span.a-size-base-plus.a-color-base.a-text-normal") or
                item.select_one("span.a-size-medium.a-color-base.a-text-normal") or
                item.select_one("span.a-size-base-plus.a-color-base") or
                item.select_one("span.a-size-base.a-color-base") or
                item.select_one("h2 span")
            )

            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue

            brand = extract_brand_from_title(title)

            # ---------------------------
            # IMMAGINE
            # ---------------------------
            img_el = (
                item.select_one("img.s-image") or
                item.select_one("img.s-image-fixed-height")
            )
            image = img_el.get("src") if img_el else None

            # ---------------------------
            # PREZZO (fallback multipli)
            # ---------------------------
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

            # ---------------------------
            # COUPON
            # ---------------------------
            coupon_el = (
                item.select_one(".s-coupon-highlight-color") or
                item.select_one("span.a-color-success") or
                item.select_one("span.a-size-base.a-color-secondary")
            )
            coupon = extract_coupon(coupon_el, base_price)

            final_price = base_price - coupon
            if final_price <= 0:
                final_price = base_price

            products[asin] = {
                "title": title,
                "brand": brand,
                "image": image,
                "price": round(final_price, 2),
                "base_price": round(base_price, 2),
                "coupon": coupon,
                "category": f"search_{category}",
                "url": f"https://www.amazon.it/dp/{asin}"
            }

        time.sleep(1)

    return products



SEARCH_CATEGORIES = {
    "gpu": "https://www.amazon.it/s?k=scheda+video",
    "cpu": "https://www.amazon.it/s?k=cpu+intel+amd",
    "ram": "https://www.amazon.it/s?k=ram+ddr5",
    "case": "https://www.amazon.it/s?k=case+pc",
    "mobo": "https://www.amazon.it/s?k=scheda+madre",
}


# ---------------------------------------------------
# FORMAT MESSAGE
# ---------------------------------------------------

def format_message(asin, info):
    title = info["title"]
    base_price = info["base_price"]
    final_price = info["price"]
    coupon = info["coupon"]

    affiliate_link = f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_ID}"

    discount_percent = round((base_price - final_price) / base_price * 100)

    coupon_text = f"🎟️ *Coupon:* -{coupon:.2f}€\n" if coupon > 0 else ""

    return f"""
😱 *OFFERTA TECH!*

📦 *{title}*
💶 *Prezzo base:* {base_price:.2f}€
💥 *Prezzo finale:* *{final_price:.2f}€*
📉 *Sconto:* -{discount_percent}%

{coupon_text}
👉 [Vai su Amazon]({affiliate_link})
"""


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

if __name__ == "__main__":
    send_message("🔍 Controllo offerte in corso...")

    # 1) Carica prezzi vecchi
    with open(PRICES_FILE, "r") as f:
        old_data = json.load(f)

    # 2) Scraping prezzi nuovi
    new_data = {}

    for name, url in SEARCH_CATEGORIES.items():
        scraped = scrape_search(url)
        new_data.update(scraped)

    offerte_trovate = 0

    # 3) Confronto vecchi vs nuovi
    for asin, new_info in new_data.items():
        if asin not in old_data:
            continue

        old_price = old_data[asin]["price"]
        new_price = new_info["price"]
        new_coupon = new_info["coupon"]

        price_drop = new_price < old_price
        has_coupon = new_coupon > 0

        if not price_drop and not has_coupon:
            continue

        caption = format_message(asin, new_info)

        if new_info.get("image"):
            send_photo(new_info["image"], caption)
        else:
            send_message(caption)

        offerte_trovate += 1
        time.sleep(2)

    if offerte_trovate == 0:
        send_message("✅ Nessuna offerta da segnalare.")
