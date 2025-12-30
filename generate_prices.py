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
# SEARCH SCRAPER
# ---------------------------------------------------

def scrape_search(url, pages=5, category="search"):
    products = []

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

            # titolo
            # Titolo – Amazon 2025 usa molti layout diversi
            title_el = (
            item.select_one("h2 a span") or
            item.select_one("span.a-size-base-plus.a-color-base.a-text-normal") or
            item.select_one("span.a-size-medium.a-color-base.a-text-normal") or
            item.select_one("span.a-size-base-plus.a-color-base") or
            item.select_one("span.a-size-base.a-color-base") or
            item.select_one("h2 span")
            )

            title = title_el.get_text(strip=True) if title_el else None


            # brand
            brand = extract_brand_from_title(title)

            # immagine
            img_el = item.select_one("img.s-image")
            image = img_el.get("src") if img_el else None

            # prezzo
            price_el = item.select_one(".a-price .a-offscreen")
            if not price_el:
                continue

            base_price = safe_float(price_el.get_text(strip=True))
            if base_price is None:
                continue

            # coupon
            coupon_el = item.select_one(".s-coupon-highlight-color, span.a-color-base")
            coupon = extract_coupon(coupon_el, base_price)

            final_price = base_price - coupon
            if final_price <= 0:
                final_price = base_price

            products.append({
                "asin": asin,
                "title": title,
                "brand": brand,
                "image": image,
                "price": round(final_price, 2),
                "base_price": round(base_price, 2),
                "coupon": coupon,
                "category": f"search_{category}",
                "url": f"https://www.amazon.it/dp/{asin}"
            })

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
# SCRAPING COMBINATO (SOLO SEARCH)
# ---------------------------------------------------

all_products = {}

for name, url in SEARCH_CATEGORIES.items():
    print(f"\n=== SEARCH: {name} ===")
    prods = scrape_search(url, pages=5, category=name)
    for p in prods:
        asin = p["asin"]
        if asin not in all_products:
            all_products[asin] = p

print(f"\nTotale prodotti raccolti: {len(all_products)}")

# ---------------------------------------------------
# SALVATAGGIO
# ---------------------------------------------------

with open(PRICES_FILE, "w") as f:
    json.dump(all_products, f, indent=4, ensure_ascii=False)

print("\nprices.json generato con successo!")
