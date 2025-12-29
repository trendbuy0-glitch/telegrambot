import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")  # <-- prende il token dal Secret
CHAT_ID = "@trendbuyit"      # <-- questo è l'username del canale? Se no, va cambiato

def send_test_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "Test GitHub Actions: il bot funziona!"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    send_test_message()
