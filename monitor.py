import os
import json
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

SYMBOL = "COMI"
ARABIC_NAME = "البنك التجاري الدولي (مصر)"
ALARM_PRICE = 138.20
STATE_FILE = "state.json"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=20
    )

    response.raise_for_status()


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"alarm_triggered": False}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


response = requests.get(
    f"https://demo.borsa.ashh.me/demo/quote/{SYMBOL}",
    timeout=20
)

response.raise_for_status()
data = response.json()

current_price = float(data["price"])
change = float(data["change"])
change_percent_text = data["change_percent"]

state = load_state()


if change > 0:
    change_icon = "🟢"
elif change < 0:
    change_icon = "🔴"
else:
    change_icon = "⚪"


if current_price <= ALARM_PRICE and not state["alarm_triggered"]:

    send_telegram(
        f"🚨 <b>EGX PRICE ALARM</b>\n\n"
        f"السهم: <b>{ARABIC_NAME} - {SYMBOL}</b>\n"
        f"السعر الحالي: <b>{current_price:.2f} جنيه</b>\n"
        f"سعر التنبيه: {ALARM_PRICE:.2f} جنيه\n"
        f"التغير: {change_icon} <b>{change:+.2f} ({change_percent_text})</b>\n"
        f"أعلى سعر: {data['high']} جنيه\n"
        f"أقل سعر: {data['low']} جنيه\n"
        f"حجم التداول: {data['volume']:,}\n\n"
        f"✅ تم الوصول لسعر التنبيه"
    )

    state["alarm_triggered"] = True
    save_state(state)


elif current_price > ALARM_PRICE and state["alarm_triggered"]:

    state["alarm_triggered"] = False
    save_state(state)
