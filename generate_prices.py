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

# ---------------------------------------------------
# SCRAPER
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

            # TITOLO
            title_el = (
                item.select_one("h2 a span") or
                item.select_one("span.a-size-base-plus.a-color-base") or
                item.select_one("span.a-size-medium.a-color-base") or
                item.select_one("h2 span")
            )
            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            # IMMAGINE
            img_el = item.select_one("img.s-image")
            image = img_el.get("src") if img_el else None

            # PREZZO BASE
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

            # SALVA SOLO I DATI NECESSARI
            products[asin] = {
                "title": title,
                "image": image,
                "base_price": round(base_price, 2),
                "url": f"https://www.amazon.it/dp/{asin}",
                "category": category
            }

        time.sleep(1)

    return products

# ---------------------------------------------------
# CATEGORIE
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
# MAIN
# ---------------------------------------------------

all_products = {}

for name, url in SEARCH_CATEGORIES.items():
    print(f"\n=== SEARCH: {name} ===")
    prods = scrape_search(url, pages=5, category=name)
    all_products.update(prods)

print(f"\nTotale prodotti raccolti: {len(all_products)}")

with open(PRICES_FILE, "w", encoding="utf-8") as f:
    json.dump(all_products, f, indent=4, ensure_ascii=False)

print("\nprices.json generato con successo!")
