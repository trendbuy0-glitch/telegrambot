import requests
from bs4 import BeautifulSoup
import json
import time

PRICES_FILE = "prices.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Connection": "keep-alive"
}

# ---------------------------------------------------
# UTILS
# ---------------------------------------------------

def safe_float(text):
    if not text:
        return None
    clean = (
        text.replace("€", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
    )
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
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return " ".join(parts[:2])


def extract_coupon(el, base_price):
    if not el or not base_price:
        return 0.0

    text = el.get_text(strip=True).lower()
    coupon = 0.0

    # percentuale
    if "%" in text:
        try:
            perc = text
            for kw in ["risparmia", "coupon", "fino a"]:
                perc = perc.replace(kw, "")
            perc = perc.replace("%", "").replace("-", "").strip()
            perc_val = float(perc)
            coupon = base_price * (perc_val / 100)
        except:
            pass

    # fisso
    if "€" in text:
        try:
            fixed = text
            for kw in ["applica coupon", "coupon", "risparmia"]:
                fixed = fixed.replace(kw, "")
            fixed = fixed.replace("€", "").strip()
            fixed_val = float(fixed)
            coupon = max(coupon, fixed_val)
        except:
            pass

    return round(coupon, 2)


# ---------------------------------------------------
# SEARCH SCRAPER (VERSIONE CORRETTA)
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

            products[asin] = {
                "title": title,
                "brand": brand,
                "image": image,
                "price": round(base_price, 2),      # SALVA SOLO IL PREZZO BASE
                "base_price": round(base_price, 2), # IDENTICO
                "coupon": 0,                        # NON SALVI COUPON
            }


        time.sleep(1)

    return products


# ---------------------------------------------------
# CATEGORIE SEARCH
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
# SCRAPING COMBINATO
# ---------------------------------------------------

all_products = {}

for name, url in SEARCH_CATEGORIES.items():
    print(f"\n=== SEARCH: {name} ===")
    prods = scrape_search(url, pages=5, category=name)

    for asin, info in prods.items():
        if asin not in all_products:
            all_products[asin] = info

print(f"\nTotale prodotti raccolti: {len(all_products)}")

# ---------------------------------------------------
# SALVATAGGIO
# ---------------------------------------------------

with open(PRICES_FILE, "w") as f:
    json.dump(all_products, f, indent=4, ensure_ascii=False)

print("\nprices.json generato con successo!")

