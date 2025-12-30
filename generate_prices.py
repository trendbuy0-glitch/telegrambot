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
            title_el = item.select_one("h2 a span")
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
# BESTSELLER SCRAPER
# ---------------------------------------------------

def scrape_bestseller(url, pages=5, category="bestseller"):
    products = []

    for page in range(1, pages + 1):
        paged = f"{url}?pg={page}"
        print(f"[BESTSELLER] {category} - {paged}")

        try:
            r = requests.get(paged, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
        except:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select("div.zg-grid-general-faceout") or \
                soup.select("ol.a-ordered-list > li")

        for item in items:
            # ASIN
            link_el = item.select_one("a.a-link-normal[href*='/dp/']")
            asin = None
            url_dp = None

            if link_el:
                href = link_el.get("href", "")
                if "/dp/" in href:
                    asin = href.split("/dp/")[1].split("/")[0].split("?")[0]
                url_dp = "https://www.amazon.it" + href.split("?", 1)[0]

            if not asin:
                asin = item.get("data-asin")
            if not asin:
                continue

            # titolo
            title_el = item.select_one("div.p13n-sc-truncate") or \
                       item.select_one("a.a-link-normal span")
            title = title_el.get_text(strip=True) if title_el else None

            # brand
            brand = extract_brand_from_title(title)

            # immagine
            img_el = item.select_one("img")
            image = img_el.get("src") if img_el else None

            # prezzo
            price_el = item.select_one("span.p13n-sc-price") or \
                       item.select_one(".a-price .a-offscreen")
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
                "category": f"bestseller_{category}",
                "url": url_dp if url_dp else f"https://www.amazon.it/dp/{asin}"
            })

        time.sleep(1)

    return products


# ---------------------------------------------------
# CATEGORIE
# ---------------------------------------------------

BESTSELLER_CATEGORIES = {
    "gpu": "https://www.amazon.it/gp/bestsellers/computers/460150031",
    "cpu": "https://www.amazon.it/gp/bestsellers/computers/460152031",
    "ram": "https://www.amazon.it/gp/bestsellers/computers/460154031",
    "ssd": "https://www.amazon.it/gp/bestsellers/computers/430162031",
    "hdd": "https://www.amazon.it/gp/bestsellers/computers/430161031",
    "psu": "https://www.amazon.it/gp/bestsellers/computers/430203031",
    "case": "https://www.amazon.it/gp/bestsellers/computers/460157031",
    "cooler": "https://www.amazon.it/gp/bestsellers/computers/460158031",
    "mobo": "https://www.amazon.it/gp/bestsellers/computers/430170031",
    "monitor": "https://www.amazon.it/gp/bestsellers/computers/427968031",
    "cuffie": "https://www.amazon.it/gp/bestsellers/computers/430228031",
    "smartphone": "https://www.amazon.it/gp/bestsellers/electronics/4363360031",
    "tablet": "https://www.amazon.it/gp/bestsellers/electronics/473295031",
    "smartwatch": "https://www.amazon.it/gp/bestsellers/electronics/473251031",
    "router": "https://www.amazon.it/gp/bestsellers/electronics/473254031",
}

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

# Bestseller
for name, url in BESTSELLER_CATEGORIES.items():
    print(f"\n=== BESTSELLER: {name} ===")
    prods = scrape_bestseller(url, pages=5, category=name)
    for p in prods:
        asin = p["asin"]
        if asin not in all_products:
            all_products[asin] = p

# Search
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
