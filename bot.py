import requests

BOT_TOKEN = "INSERISCI_IL_TUO_TOKEN"
CHAT_ID = "@nome_del_tuo_canale"

def send_test_message():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "Test GitHub Actions: il bot funziona!"
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    send_test_message()
