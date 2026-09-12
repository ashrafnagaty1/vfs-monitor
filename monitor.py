import os
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()

response = requests.get(
    "https://demo.borsa.ashh.me/demo/quote/COMI",
    timeout=20
)

response.raise_for_status()

data = response.json()

message = (
    f"📈 EGX Smart Scanner\n\n"
    f"السهم: {data['symbol']}\n"
    f"السعر: {data['price']} EGP\n"
    f"التغير: {data['change']} ({data['change_percent']})\n"
    f"الحجم: {data['volume']}\n"
    f"أعلى سعر: {data['high']}\n"
    f"أقل سعر: {data['low']}\n"
    f"المصدر: {data['source']}"
)

send_telegram(message)
