import requests
from bs4 import BeautifulSoup
import json
import time
import random

PRICES_FILE = "prices.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
}

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
# SCRAPER ANTI-BLOCCO
# ---------------------------------------------------

def extract_price(item):
    # 1) classico
    el = item.select_one(".a-price .a-offscreen")
    if el:
        return safe_float(el.get_text(strip=True))

    # 2) prezzo spezzato
    whole = item.select_one(".a-price-whole")
    frac = item.select_one(".a-price-fraction")
    if whole and frac:
        return safe_float(f"{whole.get_text(strip=True)}.{frac.get_text(strip=True)}")

    # 3) fallback
    el = item.select_one(".a-color-price")
    if el:
        return safe_float(el.get_text(strip=True))

    return None


def extract_image(item):
    img = item.select_one("img.s-image")
    if img and img.get("src"):
        return img.get("src")

    img = item.select_one("img[data-src]")
    if img:
        return img.get("data-src")

    img = item.select_one("img[srcset]")
    if img:
        return img.get("srcset").split(" ")[0]

    return None


def extract_asin(item):
    # 1) data-asin
    asin = item.get("data-asin")
    if asin:
        return asin

    # 2) link /dp/
    link = item.select_one("a[href*='/dp/']")
    if link:
        href = link.get("href")
        try:
            return href.split("/dp/")[1].split("/")[0].split("?")[0]
        except:
            pass

    return None


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

        # TUTTI i layout Amazon 2025
        items = soup.select(".s-result-item[data-asin]") \
              + soup.select("div.s-card-container") \
              + soup.select("div.puis-card-container") \
              + soup.select("div.s-result-item.s-widget")

        for item in items:
            asin = extract_asin(item)
            if not asin:
                continue

            title_el = item.select_one("h2 a span")
            title = title_el.get_text(strip=True) if title_el else None

            if not title:
                continue

            brand = extract_brand_from_title(title)
            image = extract_image(item)
            base_price = extract_price(item)

            if base_price is None:
                continue

            coupon_el = item.select_one(".s-coupon-highlight-color, span.a-color-base")
            coupon = extract_coupon(coupon_el, base_price)

            final_price = base_price - coupon
            if final_price <= 0:
                final_price = base_price

            products[asin] = {
                "asin": asin,
                "title": title,
                "brand": brand,
                "image": image,
                "price": round(final_price, 2),
                "base_price": round(base_price, 2),
                "coupon": coupon,
                "category": f"search_{category}",
                "url": f"https://www.amazon.it/dp/{asin}"
            }

        time.sleep(random.uniform(1.0, 2.0))

    return products


# ---------------------------------------------------
# CATEGORIE SEARCH
# ---------------------------------------------------

SEARCH_CATEGORIES = {
    "gpu": "https://www.amazon.it/s?k=scheda+video",
    "cpu": "https://www.amazon.it/s?k=cpu+intel+amd",
    "ram": "https://www.amazon.it/s?k=ram+ddr5",
    "case": "https://www.amazon.it/s?k=case+pc",
    "mobo": "https://www.amazon.it/s?k=scheda+madre",
    "ventole": "https://www.amazon.it/s?k=ventole+pc",
}


# ---------------------------------------------------
# SCRAPING COMBINATO
# ---------------------------------------------------

all_products = {}

for name, url in SEARCH_CATEGORIES.items():
    print(f"\n=== SEARCH: {name} ===")
    prods = scrape_search(url, pages=5, category=name)
    all_products.update(prods)

print(f"\nTotale prodotti raccolti: {len(all_products)}")

with open(PRICES_FILE, "w") as f:
    json.dump(all_products, f, indent=4, ensure_ascii=False)

print("\nprices.json generato con successo!")
