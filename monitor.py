import os
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
EGX_API_KEY = os.environ.get("EGX_API_KEY")


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


headers = {
    "Authorization": f"Bearer {EGX_API_KEY}",
    "X-EGX-Env": "paper"
}

try:
    response = requests.get(
        "https://api.egxapi.com/v2/account",
        headers=headers,
        timeout=20
    )

    if response.status_code == 200:
        send_telegram("✅ EGXAPI متصل بنجاح والمفتاح شغال")
    else:
        send_telegram(
            f"❌ مشكلة في EGXAPI\n"
            f"Status Code: {response.status_code}\n"
            f"{response.text[:300]}"
        )

except Exception as e:
    send_telegram(f"❌ خطأ أثناء الاتصال بـ EGXAPI:\n{e}")
