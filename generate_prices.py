import requests
from bs4 import BeautifulSoup
import json
import time
import os

OLD_PRICES_FILE = "old_prices.json"
NEW_PRICES_FILE = "prices.json"

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

# -----------------------------
# UTILS
# -----------------------------


def safe_float_from_price(text):
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
    except Exception:
        return None


def extract_brand_from_title(title):
    if not title:
        return None
    t = title.strip()
    # taglia su " - " se presente (spesso dopo il nome prodotto)
    if " - " in t:
        t = t.split(" - ")[0].strip()
    # prendi le prime 2 parole max (gestisce "be quiet!", "Western Digital", etc.)
    parts = t.split()
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return " ".join(parts[:2])


def extract_coupon_from_element(el, base_price):
    if not el or not base_price:
        return 0.0

    text = el.get_text(strip=True).lower()
    coupon_discount = 0.0

    # percentuale es: "Risparmia 20%"
    if "%" in text:
        try:
            perc = text
            for kw in ["risparmia", "coupon", "fino a"]:
                perc = perc.replace(kw, "")
            perc = (
                perc.replace("%", "")
                    .replace("-", "")
                    .strip()
            )
            perc_val = float(perc)
            coupon_discount = base_price * (perc_val / 100.0)
        except Exception:
            pass

    # fisso es: "Applica coupon 5€"
    if "€" in text:
        try:
            fixed = text
            for kw in ["applica coupon", "coupon", "risparmia"]:
                fixed = fixed.replace(kw, "")
            fixed = fixed.replace("€", "").strip()
            fixed_val = float(fixed)
            # se già calcolato prima come percentuale, tieni lo sconto maggiore
            coupon_discount = max(coupon_discount, fixed_val)
        except Exception:
            pass

    return round(coupon_discount, 2)


# -----------------------------
# SEARCH SCRAPER (/s?k=...)
# -----------------------------


def scrape_search_category(url, pages=5, category_name="search"):
    products = []

    for page in range(1, pages + 1):
        paged_url = f"{url}&page={page}"
        print(f"[SEARCH] {category_name} - Scraping:", paged_url)

        try:
            r = requests.get(paged_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print("Status code non 200, salto pagina")
                continue
        except Exception as e:
            print("Errore nella richiesta SEARCH, salto pagina:", e)
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        items = soup.select(".s-result-item[data-asin]")
        if not items:
            # Amazon a volte cambia layout, meglio non bloccare tutto
            print("Nessun item trovato in questa pagina SEARCH")
            continue

        for item in items:
            asin = item.get("data-asin")
            if not asin:
                continue

            # titolo
            title_el = item.select_one("h2 a span")
            title = title_el.get_text(strip=True) if title_el else None

            # brand (se c'è un badge brand)
            brand = None
            brand_el = item.select_one("h5 span") or item.select_one("span.a-size-base-plus")
            if brand_el:
                btxt = brand_el.get_text(strip=True)
                # spesso qui ci sono stringhe un po' miste, ma ci proviamo
                if btxt and len(btxt.split()) <= 3:
                    brand = btxt

            if not brand:
                brand = extract_brand_from_title(title)

            # immagine
            img_el = item.select_one("img.s-image")
            image = img_el.get("src") if img_el else None

            # prezzo base (visibile)
            price_el = item.select_one(".a-price .a-offscreen")
            if not price_el:
                # prodotto senza prezzo (es. "vedi opzioni"), saltiamo
                continue

            price_text = price_el.get_text(strip=True)
            base_price = safe_float_from_price(price_text)
            if base_price is None:
                print("Prezzo non valido (SEARCH), salto:", price_text)
                continue

            # coupon
            coupon_el = item.select_one(".s-coupon-highlight-color, span.a-color-base")
            coupon_discount = extract_coupon_from_element(coupon_el, base_price)

            final_price = base_price - coupon_discount
            if final_price <= 0:
                final_price = base_price

            products.append({
                "asin": asin,
                "title": title,
                "brand": brand,
                "image": image,
                "price": round(final_price, 2),
                "base_price": round(base_price, 2),
                "coupon": coupon_discount,
                "category": f"search_{category_name}",
                "url": f"https://www.amazon.it/dp/{asin}"
            })

        time.sleep(1)

    return products


# -----------------------------
# BESTSELLER SCRAPER (/gp/bestsellers/...)
# -----------------------------


def scrape_bestseller_category(url, pages=5, category_name="bestseller"):
    """
    Scraping delle pagine Bestseller.
    Le pagine tipicamente supportano il parametro '?pg=2', '?pg=3', ...
    """
    products = []

    for page in range(1, pages + 1):
        paged_url = url
        if "?" in url:
            paged_url = f"{url}&pg={page}"
        else:
            paged_url = f"{url}?pg={page}"

        print(f"[BESTSELLER] {category_name} - Scraping:", paged_url)

        try:
            r = requests.get(paged_url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print("Status code non 200, salto pagina")
                continue
        except Exception as e:
            print("Errore nella richiesta BESTSELLER, salto pagina:", e)
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # layout classico bestseller: li.zg-grid-general-faceout o simili
        # proviamo selettori multipli per robustezza
        items = soup.select("div.zg-grid-general-faceout") or \
            soup.select("div.zg-grid-general-faceout-wrapper") or \
            soup.select("ol.a-ordered-list > li")

        if not items:
            print("Nessun item trovato in questa pagina BESTSELLER")
            continue

        for item in items:
            # ASIN spesso nel link principale
            link_el = item.select_one("a.a-link-normal[href*='/dp/']")
            asin = None
            url_dp = None
            if link_el:
                href = link_el.get("href", "")
                # estrai asin dal pattern /dp/ASIN/
                if "/dp/" in href:
                    try:
                        asin = href.split("/dp/")[1].split("/")[0].split("?")[0]
                    except Exception:
                        asin = None
                url_dp = "https://www.amazon.it" + href.split("?", 1)[0]
            if not asin:
                # fallback: cerca data-asin
                asin = item.get("data-asin")
            if not asin:
                continue

            # titolo
            title_el = item.select_one("div.p13n-sc-truncate") or \
                item.select_one("span.zg-text-center-align a div") or \
                item.select_one("a.a-link-normal div") or \
                item.select_one("a.a-link-normal span")
            title = title_el.get_text(strip=True) if title_el else None

            # brand: spesso in "byline" o sotto il titolo
            brand = None
            brand_el = item.select_one("span.a-size-small.a-color-base") or \
                item.select_one("span.a-size-small.a-color-secondary")
            if brand_el:
                btxt = brand_el.get_text(strip=True)
                if btxt and len(btxt.split()) <= 4:
                    brand = btxt
            if not brand:
                brand = extract_brand_from_title(title)

            # immagine
            img_el = item.select_one("img")
            image = img_el.get("src") if img_el else None

            # prezzo
            price_el = item.select_one("span.p13n-sc-price") or \
                item.select_one("span.a-color-price") or \
                item.select_one(".a-price .a-offscreen")
            if not price_el:
                # niente prezzo visibile → salta
                continue

            price_text = price_el.get_text(strip=True)
            base_price = safe_float_from_price(price_text)
            if base_price is None:
                print("Prezzo non valido (BESTSELLER), salto:", price_text)
                continue

            # coupon (più raro nei bestseller, ma proviamo)
            coupon_el = item.select_one(".s-coupon-highlight-color, span.a-color-base")
            coupon_discount = extract_coupon_from_element(coupon_el, base_price)

            final_price = base_price - coupon_discount
            if final_price <= 0:
                final_price = base_price

            products.append({
                "asin": asin,
                "title": title,
                "brand": brand,
                "image": image,
                "price": round(final_price, 2),
                "base_price": round(base_price, 2),
                "coupon": coupon_discount,
                "category": f"bestseller_{category_name}",
                "url": url_dp if url_dp else f"https://www.amazon.it/dp/{asin}"
            })

        time.sleep(1)

    return products


# -----------------------------
# CONFIG: CATEGORIE
# -----------------------------

# C: hardware + periferiche + elettronica
BESTSELLER_CATEGORIES = {
    # Hardware PC
    "gpu": "https://www.amazon.it/gp/bestsellers/computers/460150031",
    "cpu": "https://www.amazon.it/gp/bestsellers/computers/460152031",
    "ram": "https://www.amazon.it/gp/bestsellers/computers/460154031",
    "ssd": "https://www.amazon.it/gp/bestsellers/computers/430162031",
    "hdd": "https://www.amazon.it/gp/bestsellers/computers/430161031",
    "psu": "https://www.amazon.it/gp/bestsellers/computers/430203031",
    "case": "https://www.amazon.it/gp/bestsellers/computers/460157031",
    "cooler": "https://www.amazon.it/gp/bestsellers/computers/460158031",
    "mobo": "https://www.amazon.it/gp/bestsellers/computers/430170031",

    # Periferiche
    "monitor": "https://www.amazon.it/gp/bestsellers/computers/427968031",
    "mouse": "https://www.amazon.it/gp/bestsellers/computers/427968031#mouse",
    "tastiere": "https://www.amazon.it/gp/bestsellers/computers/427968031#tastiere",
    "cuffie": "https://www.amazon.it/gp/bestsellers/computers/430228031",

    # Elettronica generica
    "smartphone": "https://www.amazon.it/gp/bestsellers/electronics/4363360031",
    "tablet": "https://www.amazon.it/gp/bestsellers/electronics/473295031",
    "smartwatch": "https://www.amazon.it/gp/bestsellers/electronics/473251031",
    "router": "https://www.amazon.it/gp/bestsellers/electronics/473254031",
}

SEARCH_CATEGORIES = {
    "alimentatori": "https://www.amazon.it/s?k=alimentatore+pc",
    "gpu": "https://www.amazon.it/s?k=scheda+video",
    "cpu": "https://www.amazon.it/s?k=cpu+intel+amd",
    "dissipatori": "https://www.amazon.it/s?k=condissipatore+cpu",
    "mobo": "https://www.amazon.it/s?k=scheda+madre",
    "case": "https://www.amazon.it/s?k=case+pc",
    "ram": "https://www.amazon.it/s?k=ram+ddr5",
    "ventole": "https://www.amazon.it/s?k=ventole+pc"
}


# -----------------------------
# CARICAMENTO VECCHI PREZZI
# -----------------------------

if os.path.exists(OLD_PRICES_FILE):
    try:
        with open(OLD_PRICES_FILE, "r") as f:
            content = f.read().strip()
            old_data = json.loads(content) if content else {}
    except Exception:
        old_data = {}
else:
    old_data = {}

# -----------------------------
# SCRAPING COMBINATO
# -----------------------------

all_products = {}

# 1) Bestseller
for name, url in BESTSELLER_CATEGORIES.items():
    print(f"\n=== BESTSELLER: {name} ===")
    try:
        prods = scrape_bestseller_category(url, pages=5, category_name=name)
    except Exception as e:
        print(f"Errore durante scraping bestseller {name}:", e)
        continue

    for p in prods:
        asin = p["asin"]
        # merge: se già esiste, tieni il prezzo più basso e combina info
        if asin in all_products:
            existing = all_products[asin]
            # prezzo minimo tra i due
            if p["price"] < existing["price"]:
                existing["price"] = p["price"]
                existing["base_price"] = p["base_price"]
                existing["coupon"] = p["coupon"]
            # aggiorna titolo/brand/image se mancano
            if not existing.get("title") and p.get("title"):
                existing["title"] = p["title"]
            if not existing.get("brand") and p.get("brand"):
                existing["brand"] = p["brand"]
            if not existing.get("image") and p.get("image"):
                existing["image"] = p["image"]
            # aggiungi categoria concatenata
            existing["category"] = f'{existing.get("category", "")},{p["category"]}'.strip(",")
        else:
            all_products[asin] = p

# 2) Search
for name, url in SEARCH_CATEGORIES.items():
    print(f"\n=== SEARCH: {name} ===")
    try:
        prods = scrape_search_category(url, pages=5, category_name=name)
    except Exception as e:
        print(f"Errore durante scraping search {name}:", e)
        continue

    for p in prods:
        asin = p["asin"]
        if asin in all_products:
            existing = all_products[asin]
            if p["price"] < existing["price"]:
                existing["price"] = p["price"]
                existing["base_price"] = p["base_price"]
                existing["coupon"] = p["coupon"]
            if not existing.get("title") and p.get("title"):
                existing["title"] = p["title"]
            if not existing.get("brand") and p.get("brand"):
                existing["brand"] = p["brand"]
            if not existing.get("image") and p.get("image"):
                existing["image"] = p["image"]
            existing["category"] = f'{existing.get("category", "")},{p["category"]}'.strip(",")
        else:
            all_products[asin] = p

print(f"\nTotale prodotti raccolti (unici): {len(all_products)}")

# -----------------------------
# CONFRONTO PREZZI + NOTIFY
# -----------------------------

new_prices = {}

for asin, info in all_products.items():
    price = info["price"]
    base_price = info.get("base_price", price)
    coupon = info.get("coupon", 0.0)

    # titolo fallback
    title = info.get("title") or f"ASIN {asin}"
    brand = info.get("brand")

    notify = False
    if asin in old_data:
        try:
            old_price = old_data[asin]["price"]
            if price < old_price:
                notify = True
        except Exception:
            notify = False

    new_prices[asin] = {
        "title": title,
        "brand": brand,
        "image": info.get("image"),
        "price": round(price, 2),
        "base_price": round(base_price, 2),
        "coupon": round(coupon, 2),
        "category": info.get("category"),
        "url": info.get("url", f"https://www.amazon.it/dp/{asin}"),
        "notify": notify
    }

# -----------------------------
# SALVATAGGIO
# -----------------------------

with open(NEW_PRICES_FILE, "w") as f:
    json.dump(new_prices, f, indent=4, ensure_ascii=False)

print("\nprices.json generato con successo!")
