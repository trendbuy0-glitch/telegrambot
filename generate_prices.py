import requests
from bs4 import BeautifulSoup
import json
import time

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

            price_el = item.select_one(".a-price .a-offscreen")
            if not price_el:
                continue

            price_text = price_el.get_text(strip=True)

            # Pulizia robusta del prezzo
            clean = (
                price_text.replace("€", "")
                          .replace(".", "")   # rimuove separatore migliaia
                          .replace(",", ".")  # converte decimali
                          .strip()
            )

            try:
                price = float(clean)
            except:
                print("Prezzo non valido, salto:", price_text)
                continue

            products.append({
                "asin": asin,
                "price": price
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

new_prices = {}

# Scraping di tutte le categorie
for name, url in CATEGORIES.items():
    print(f"\n--- Scraping categoria: {name} ---")
    products = scrape_category(url)

    for p in products:
        new_prices[p["asin"]] = p["price"]

# Salvataggio del file JSON
with open("prices.json", "w") as f:
    json.dump(new_prices, f, indent=4)

print("\nprices.json generato con successo!")
