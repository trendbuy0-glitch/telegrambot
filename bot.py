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
    if not BOT_TOKEN:
        print("WARN: BOT_TOKEN non impostato, skip send_message")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Errore invio messaggio:", e)

def send_photo(image_url, caption):
    if not BOT_TOKEN:
        print("WARN: BOT_TOKEN non impostato, skip send_photo")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {"chat_id": CHAT_ID, "photo": image_url, "caption": caption, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Errore invio foto:", e)

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
# SCRAPING SEARCH
# ---------------------------------------------------

def scrape_search(url, pages=5, category="search"):
    products = {}

    for page in range(1, pages + 1):
        paged = f"{url}&page={page}"
        print(f"[SEARCH] {category} - {paged}")

        try:
            r = requests.get(paged, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"WARN: status {r.status_code} per {paged}")
                continue
        except Exception as e:
            print("WARN: richiesta fallita:", e)
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".s-result-item[data-asin]")

        for item in items:
            asin = item.get("data-asin")
            if not asin:
                continue

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

            img_el = (
                item.select_one("img.s-image") or
                item.select_one("img.s-image-fixed-height")
            )
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
    title = info.get("title", "Prodotto")
    final_price = info.get("final_price", 0.0)
    coupon = info.get("coupon", 0.0)

    affiliate_link = f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_ID}"

    try:
        discount_percent = round((old_price - final_price) / old_price * 100)
    except Exception:
        discount_percent = 0

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

    # Carica prezzi vecchi (gestisce sia 'base_price' che 'price')
    try:
        with open(PRICES_FILE, "r", encoding="utf-8") as f:
            old_data = json.load(f)
    except Exception as e:
        print("Errore aprendo prices.json:", e)
        old_data = {}

    # Scraping nuovi prezzi
    new_data = {}
    for name, url in SEARCH_CATEGORIES.items():
        scraped = scrape_search(url)
        new_data.update(scraped)

    # Debug rapido
    print("ASIN nel file vecchio:", len(old_data), list(old_data.keys())[:10])
    print("ASIN trovati nello scraping:", len(new_data), list(new_data.keys())[:10])

    offerte_trovate = 0

    # Confronto vecchi vs nuovi
    for asin, new_info in new_data.items():
        if asin not in old_data:
            # opzionale: log per capire quali ASIN nuovi non sono nel file vecchio
            # print(f"Nuovo ASIN non presente in prices.json: {asin}")
            continue

        old_entry = old_data.get(asin, {})
        # preferiamo base_price, fallback su price (compatibilità)
        old_price = None
        if isinstance(old_entry, dict):
            old_price = old_entry.get("base_price")
            if old_price is None:
                old_price = old_entry.get("price")
        else:
            # se old_entry è un valore semplice
            try:
                old_price = float(old_entry)
            except:
                old_price = None

        if old_price is None:
            print(f"Salto {asin}: nessun prezzo vecchio valido")
            continue

        new_final = new_info.get("final_price")
        new_coupon = new_info.get("coupon", 0)

        if new_final is None:
            continue

        price_drop = new_final < old_price
        has_coupon = new_coupon > 0

        if not price_drop and not has_coupon:
            continue

        caption = format_message(asin, new_info, old_price)

        if new_info.get("image"):
            send_photo(new_info["image"], caption)
        else:
            send_message(caption)

        offerte_trovate += 1
        time.sleep(2)

    if offerte_trovate == 0:
        send_message("✅ Nessuna offerta da segnalare.")
