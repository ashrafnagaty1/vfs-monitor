import os
import json
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

ALARMS_FILE = "alarms.json"
STATE_FILE = "state.json"

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

MAIN_MENU = {
    "keyboard": [
        ["📊 الشاشة اللحظية", "🔍 تحليل سهم"],
        ["🎯 فرص اليوم", "🚨 تنبيهاتي"],
        ["💼 محفظتي", "🤖 المساعد الذكي"],
        ["📈 نتائج الإشارات", "⚙️ الإعدادات"],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def send_telegram(message, chat_id=None, reply_markup=None):
    target_chat = str(chat_id or CHAT_ID)
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "HTML",
    }

    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data=payload,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_main_menu(chat_id):
    send_telegram(
        "📈 <b>EGX Smart Scanner</b>\n\n"
        "أهلاً بيك 👋\n"
        "اختار من القائمة الرئيسية:",
        chat_id=chat_id,
        reply_markup=MAIN_MENU,
    )


def handle_menu_message(chat_id, text):
    text = (text or "").strip()

    if text in ("/start", "/menu", "🏠 القائمة الرئيسية"):
        send_main_menu(chat_id)
        return

    coming_soon = {
        "📊 الشاشة اللحظية": "📊 <b>الشاشة اللحظية</b>\n\nهنضيف هنا أسعار السوق اللحظية وMarket Watch.",
        "🔍 تحليل سهم": "🔍 <b>تحليل سهم</b>\n\nهنضيف هنا اختيار السهم ثم التحليل الفني الكامل.",
        "🎯 فرص اليوم": "🎯 <b>فرص اليوم</b>\n\nهنضيف هنا أفضل الفرص مرتبة حسب قوة الإشارة.",
        "🚨 تنبيهاتي": "🚨 <b>تنبيهاتي</b>\n\nهنعرض هنا التنبيهات النشطة وحالتها.",
        "💼 محفظتي": "💼 <b>محفظتي</b>\n\nهنضيف هنا المراكز المفتوحة والربح والخسارة.",
        "🤖 المساعد الذكي": "🤖 <b>المساعد الذكي</b>\n\nهنضيف هنا أسئلة وتحليل سريع عن أسهم EGX.",
        "📈 نتائج الإشارات": "📈 <b>نتائج الإشارات</b>\n\nهنعرض هنا T1 / T2 / T3 ونسبة النجاح والأداء.",
        "⚙️ الإعدادات": "⚙️ <b>الإعدادات</b>\n\nهنضيف هنا إعدادات التنبيهات وطريقة المتابعة.",
    }

    if text in coming_soon:
        send_telegram(
            coming_soon[text] + "\n\n🛠️ <i>قيد التطوير</i>",
            chat_id=chat_id,
            reply_markup=MAIN_MENU,
        )
        return

    send_telegram(
        "استخدم أزرار القائمة الرئيسية 👇",
        chat_id=chat_id,
        reply_markup=MAIN_MENU,
    )


def process_telegram_updates(state):
    offset = int(state.get("telegram_update_offset", 0))
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset:
        params["offset"] = offset

    response = requests.get(
        f"{TELEGRAM_API}/getUpdates",
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    updates = response.json().get("result", [])

    changed = False

    for update in updates:
        update_id = int(update.get("update_id", 0))
        next_offset = update_id + 1
        if next_offset > int(state.get("telegram_update_offset", 0)):
            state["telegram_update_offset"] = next_offset
            changed = True

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        incoming_chat_id = str(chat.get("id", ""))
        text = message.get("text")

        # Keep this private bot limited to the configured owner/chat.
        if not incoming_chat_id or incoming_chat_id != str(CHAT_ID):
            continue

        if text:
            handle_menu_message(incoming_chat_id, text)

    return changed


alarms_data = load_json(ALARMS_FILE, {"alarms": []})
state = load_json(STATE_FILE, {"alarms": {}})

if "alarms" not in state or not isinstance(state.get("alarms"), dict):
    state["alarms"] = {}

state_changed = process_telegram_updates(state)

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
            "condition_was_true": False,
        },
    )

    response = requests.get(
        f"https://demo.borsa.ashh.me/demo/quote/{symbol}",
        timeout=20,
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
    can_notify = max_notifications == 0 or notifications_sent < max_notifications

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

    elif not condition_met and alarm_state.get("condition_was_true", False):
        alarm_state["condition_was_true"] = False
        alarm_state["notifications_sent"] = 0
        state["alarms"][alarm_id] = alarm_state
        state_changed = True


if state_changed:
    save_json(STATE_FILE, state)
