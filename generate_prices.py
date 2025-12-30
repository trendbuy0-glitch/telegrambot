import requests
from bs4 import BeautifulSoup
import json
import time
import os

OLD_PRICES_FILE = "old_prices.json"
NEW_PRICES_FILE = "prices.json"

# Funzione che estrae i prodotti da una categoria Amazon
def scrape_category(url, pages=5, limit=200):
    products = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive"
    }

    for page in range(1, pages + 1):
        paged_url = f"{url}&page={page}"
        print("Scraping:", paged_url)

        try:
            r = requests.get(paged_url, headers=headers, timeout=10)
        except:
            print("Errore nella richiesta, salto pagina")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        items = soup.select(".s-result-item[data-asin]")
        for item in items:
            asin = item.get("data-asin")
            if not asin:
                continue

            # Prezzo base
            price_el = item.select_one(".a-price .a-offscreen")
            if not price_el:
                continue

            price_text = price_el.get_text(strip=True)

            clean = (
                price_text.replace("€", "")
                          .replace(".", "")
                          .replace(",", ".")
                          .strip()
            )

            try:
                base_price = float(clean)
            except:
                print("Prezzo non valido, salto:", price_text)
                continue

            # -----------------------------
            # 🔥 RILEVAZIONE COUPON
            # -----------------------------
            coupon_discount = 0
            final_price = base_price

            coupon_el = item.select_one(".s-coupon-highlight-color, span.a-color-base")

            if coupon_el:
                coupon_text = coupon_el.get_text(strip=True).lower()

                # Coupon percentuale
                if "%" in coupon_text:
                    try:
                        perc = float(
                            coupon_text.replace("risparmia", "")
                                       .replace("%", "")
                                       .replace("-", "")
                                       .strip()
                        )
                        coupon_discount = base_price * (perc / 100)
                    except:
                        pass

                # Coupon fisso
                if "€" in coupon_text:
                    try:
                        fixed = coupon_text.replace("applica coupon", "").replace("€", "").strip()
                        coupon_discount = float(fixed)
                    except:
                        pass

                final_price = base_price - coupon_discount

            # Salva prodotto COMPLETO
            products.append({
                "asin": asin,
                "price": round(final_price, 2),
                "base_price": round(base_price, 2),
                "coupon": round(coupon_discount, 2)
            })

            if len(products) >= limit:
                return products

        time.sleep(1)

    return products


# Categorie da scrapare
CATEGORIES = {
    "alimentatori": "https://www.amazon.it/s?k=alimentatore+pc",
    "gpu": "https://www.amazon.it/s?k=scheda+video",
    "cpu": "https://www.amazon.it/s?k=cpu+intel+amd",
    "dissipatori": "https://www.amazon.it/s?k=dissipatore+cpu",
    "mobo": "https://www.amazon.it/s?k=scheda+madre",
    "case": "https://www.amazon.it/s?k=case+pc",
    "ram": "https://www.amazon.it/s?k=ram+ddr5",
    "ventole": "https://www.amazon.it/s?k=ventole+pc"
}

# Carica vecchi prezzi
if os.path.exists(OLD_PRICES_FILE):
    with open(OLD_PRICES_FILE, "r") as f:
        old_data = json.load(f)
else:
    old_data = {}

new_prices = {}

# Scraping di tutte le categorie
for name, url in CATEGORIES.items():
    print(f"\n--- Scraping categoria: {name} ---")
    products = scrape_category(url)

    for p in products:
        asin = p["asin"]

        new_prices[asin] = {
            "price": p["price"],
            "base_price": p["base_price"],
            "coupon": p["coupon"],
            "notify": False
        }

        # Se esiste un vecchio prezzo → confronta
        if asin in old_data:
            old_price = old_data[asin]["price"]

            # Se il prezzo è sceso → segna notify
            if p["price"] < old_price:
                new_prices[asin]["notify"] = True

# Salvataggio del file JSON
with open(NEW_PRICES_FILE, "w") as f:
    json.dump(new_prices, f, indent=4)

print("\nprices.json generato con successo!")
