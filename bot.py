import os
import requests

BOT_TOKEN = os.getenv("TrendBuyFinderBot")  # <-- prende il token dal Secret
CHAT_ID = "@TrendBuyFinderBot"

def send_test_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "Test GitHub Actions: il bot funziona!"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    send_test_message()
