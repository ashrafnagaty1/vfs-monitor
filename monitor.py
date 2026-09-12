import os
import json
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

ALARMS_FILE = "alarms.json"
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


def load_json(path, default):
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


alarms_data = load_json(ALARMS_FILE, {"alarms": []})
state = load_json(STATE_FILE, {"alarms": {}})

if "alarms" not in state:
    state["alarms"] = {}

state_changed = False


for alarm in alarms_data.get("alarms", []):

    if not alarm.get("active", True):
        continue

    alarm_id = alarm["id"]
    symbol = alarm["symbol"]
    arabic_name = alarm.get("arabic_name", symbol)
    condition = alarm["condition"]
    target_price = float(alarm["price"])
    max_notifications = alarm.get("max_notifications", 1)

    alarm_state = state["alarms"].get(
        alarm_id,
        {
            "notifications_sent": 0,
            "condition_was_true": False
        }
    )

    response = requests.get(
        f"https://demo.borsa.ashh.me/demo/quote/{symbol}",
        timeout=20
    )

    response.raise_for_status()
    data = response.json()

    current_price = float(data["price"])
    change = float(data.get("change", 0))
    change_percent_text = data.get("change_percent", "0.00%")

    if change > 0:
        change_icon = "🟢"
    elif change < 0:
        change_icon = "🔴"
    else:
        change_icon = "⚪"

    if condition == ">=":
        condition_met = current_price >= target_price
        condition_text = "أكبر من أو يساوي"
    else:
        condition_met = current_price <= target_price
        condition_text = "أقل من أو يساوي"

    notifications_sent = alarm_state.get("notifications_sent", 0)

    can_notify = (
        max_notifications == 0
        or notifications_sent < max_notifications
    )

    if condition_met and can_notify:

        send_telegram(
            f"🚨 <b>EGX PRICE ALARM</b>\n\n"
            f"السهم: <b>{arabic_name} - {symbol}</b>\n"
            f"السعر الحالي: <b>{current_price:.2f} جنيه</b>\n"
            f"شرط التنبيه: {condition_text} {target_price:.2f} جنيه\n"
            f"التغير: {change_icon} <b>{change:+.2f} ({change_percent_text})</b>\n"
            f"أعلى سعر: {data.get('high', '-')} جنيه\n"
            f"أقل سعر: {data.get('low', '-')} جنيه\n"
            f"حجم التداول: {data.get('volume', 0):,}\n\n"
            f"✅ تم تحقيق شرط التنبيه"
        )

        alarm_state["notifications_sent"] = notifications_sent + 1
        alarm_state["condition_was_true"] = True

        state["alarms"][alarm_id] = alarm_state
        state_changed = True

    elif not condition_met:

        if alarm_state.get("condition_was_true", False):
            alarm_state["condition_was_true"] = False
            alarm_state["notifications_sent"] = 0

            state["alarms"][alarm_id] = alarm_state
            state_changed = True


if state_changed:
    save_json(STATE_FILE, state)
