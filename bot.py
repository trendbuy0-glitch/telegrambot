import os
import requests

# Legge il token dal secret GitHub chiamato "TrendBuyFinderBot"
BOT_TOKEN = os.getenv("TrendBuyFinderBot")

# Inserirai qui il CHAT_ID numerico del canale quando lo otteniamo
CHAT_ID = "-1003544601340"

def send_test_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "Test GitHub Actions: il bot funziona!"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    send_test_message()
