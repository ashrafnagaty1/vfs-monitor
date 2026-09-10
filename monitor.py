import os
import requests
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
EGX_API_KEY = os.environ.get("EGX_API_KEY")

API_BASE = "https://api.egxapi.com/v2"

# ==========================================
# الأسهم والتنبيهات
# ==========================================

ALERTS = [
    {
        "symbol": "COMI",
        "target": 100.00,
        "direction": "above"
    }
]


def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("Telegram TOKEN or CHAT_ID is missing")
        return

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


def get_stock_price(symbol):
    if not EGX_API_KEY:
        raise RuntimeError("EGX_API_KEY is missing")

    headers = {
        "Authorization": f"Bearer {EGX_API_KEY}",
        "X-EGX-Env": "paper"
    }

    # سنثبت endpoint النهائي بعد أول اختبار للـ API
    url = f"{API_BASE}/market/quotes/{symbol}"

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    # يدعم أكثر من شكل محتمل للاستجابة
    for key in ["price", "last", "last_price", "close"]:
        if key in data:
            return float(data[key])

    if "data" in data and isinstance(data["data"], dict):
        for key in ["price", "last", "last_price", "close"]:
            if key in data["data"]:
                return float(data["data"][key])

    raise RuntimeError(
        f"Could not find price for {symbol}. Response: {data}"
    )


def check_alert(alert):
    symbol = alert["symbol"]
    target = float(alert["target"])
    direction = alert["direction"]

    try:
        price = get_stock_price(symbol)

        print(
            f"{symbol}: current={price} "
            f"target={target} direction={direction}"
        )

        triggered = False

        if direction == "above" and price >= target:
            triggered = True

        elif direction == "below" and price <= target:
            triggered = True

        if triggered:
            arrow = "⬆️" if direction == "above" else "⬇️"

            message = (
                f"🔔 EGX Smart Scanner\n\n"
                f"📈 السهم: {symbol}\n"
                f"💰 السعر الحالي: {price:.2f} EGP\n"
                f"🎯 السعر المستهدف: {target:.2f} EGP\n"
                f"{arrow} تم تحقق شرط التنبيه\n\n"
                f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            send_telegram(message)

    except Exception as e:
        print(f"Error checking {symbol}: {e}")


def main():
    print("================================")
    print("EGX Smart Scanner Cloud Monitor")
    print("================================")

    for alert in ALERTS:
        check_alert(alert)


if __name__ == "__main__":
    main()
