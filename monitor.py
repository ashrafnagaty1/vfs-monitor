import os
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

SYMBOL = "COMI"
ALARM_PRICE = 138.20


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
    f"https://demo.borsa.ashh.me/demo/quote/{SYMBOL}",
    timeout=20
)

response.raise_for_status()
data = response.json()

current_price = float(data["price"])

if current_price <= ALARM_PRICE:
    send_telegram(
        f"🚨 EGX PRICE ALARM\n\n"
        f"السهم: {SYMBOL}\n"
        f"السعر الحالي: {current_price:.2f} EGP\n"
        f"سعر التنبيه: {ALARM_PRICE:.2f} EGP\n\n"
        f"✅ تم الوصول لسعر التنبيه"
    )
