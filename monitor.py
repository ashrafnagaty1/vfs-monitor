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
    payload = {"chat_id": target_chat, "text": message, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    response = requests.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=20)
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
        "📈 <b>EGX Smart Scanner</b>\n\nأهلاً بيك 👋\nاختار من القائمة الرئيسية:",
        chat_id=chat_id,
        reply_markup=MAIN_MENU,
    )


def get_quote(symbol):
    response = requests.get(
        f"https://demo.borsa.ashh.me/demo/quote/{symbol.upper()}", timeout=20
    )
    if response.status_code == 429:
        raise RuntimeError("DATA_LIMIT")
    if response.status_code == 404:
        raise RuntimeError("NOT_FOUND")
    response.raise_for_status()
    return response.json()


def format_number(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "-"


def send_stock_analysis(chat_id, symbol):
    symbol = symbol.strip().upper().replace(".CA", "")
    if not symbol or len(symbol) > 12 or not symbol.replace("-", "").isalnum():
        send_telegram("⚠️ اكتب رمز سهم صحيح، مثال: <b>COMI</b>", chat_id=chat_id)
        return

    try:
        data = get_quote(symbol)
    except RuntimeError as exc:
        if str(exc) == "DATA_LIMIT":
            send_telegram(
                "⚠️ <b>مصدر الأسعار التجريبي وصل للحد المسموح حاليًا.</b>\n\n"
                "زر تحليل السهم شغال، لكن السعر الحقيقي محتاج مصدر بيانات EGX أفضل.\n"
                "هنربطه بالـLive Feed في مرحلة البيانات.",
                chat_id=chat_id,
                reply_markup=MAIN_MENU,
            )
        else:
            send_telegram(
                f"❌ لم أجد السهم <b>{symbol}</b>.\nتأكد من الرمز وجرب مرة أخرى.",
                chat_id=chat_id,
            )
        return
    except requests.RequestException:
        send_telegram(
            "⚠️ تعذر الاتصال بمصدر البيانات حاليًا. جرب بعد قليل.", chat_id=chat_id
        )
        return

    price = float(data.get("price", 0) or 0)
    change = float(data.get("change", 0) or 0)
    pct = str(data.get("change_percent", "-")).strip()
    icon = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"

    high = data.get("high", "-")
    low = data.get("low", "-")
    volume = data.get("volume", 0) or 0
    name = data.get("name") or data.get("arabic_name") or symbol

    # This first version intentionally reports only fields supported by the current feed.
    # RSI/MACD/targets will be activated once historical/live candles are connected.
    send_telegram(
        f"🔍 <b>تحليل سهم — {symbol}</b>\n\n"
        f"🏢 {name}\n"
        f"💰 السعر: <b>{price:.2f} جنيه</b>\n"
        f"{icon} التغير: <b>{change:+.2f} ({pct})</b>\n"
        f"⬆️ أعلى سعر: <b>{format_number(high)}</b>\n"
        f"⬇️ أقل سعر: <b>{format_number(low)}</b>\n"
        f"📦 حجم التداول: <b>{int(float(volume)):,}</b>\n\n"
        f"🧠 <b>التحليل الفني المتقدم</b>\n"
        f"RSI: ⏳ بانتظار بيانات الشموع\n"
        f"MACD: ⏳ بانتظار بيانات الشموع\n"
        f"الدعم والمقاومة: ⏳ بانتظار البيانات التاريخية\n"
        f"Entry / T1 / T2 / T3 / Stop: ⏳ غير مفعلة بعد\n\n"
        f"ℹ️ <i>لن نولد أهدافًا أو توصيات من بيانات ناقصة.</i>",
        chat_id=chat_id,
        reply_markup=MAIN_MENU,
    )


def handle_menu_message(chat_id, text, state):
    text = (text or "").strip()

    if text in ("/start", "/menu", "🏠 القائمة الرئيسية"):
        state.pop("awaiting_stock_analysis", None)
        send_main_menu(chat_id)
        return True

    if text == "🔍 تحليل سهم":
        state["awaiting_stock_analysis"] = True
        send_telegram(
            "🔍 <b>تحليل سهم</b>\n\nاكتب رمز السهم في البورصة المصرية.\nمثال: <b>COMI</b> أو <b>ABUK</b>",
            chat_id=chat_id,
        )
        return True

    if state.get("awaiting_stock_analysis"):
        state["awaiting_stock_analysis"] = False
        send_stock_analysis(chat_id, text)
        return True

    coming_soon = {
        "📊 الشاشة اللحظية": "📊 <b>الشاشة اللحظية</b>\n\nهنضيف هنا أسعار السوق اللحظية وMarket Watch.",
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
        return False

    send_telegram("استخدم أزرار القائمة الرئيسية 👇", chat_id=chat_id, reply_markup=MAIN_MENU)
    return False


def process_telegram_updates(state):
    offset = int(state.get("telegram_update_offset", 0))
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset:
        params["offset"] = offset

    response = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=20)
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

        if not incoming_chat_id or incoming_chat_id != str(CHAT_ID):
            continue
        if text and handle_menu_message(incoming_chat_id, text, state):
            changed = True

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
        alarm_id, {"notifications_sent": 0, "condition_was_true": False}
    )

    try:
        data = get_quote(symbol)
    except (requests.RequestException, RuntimeError):
        # A temporary/limited quote source must never break the Telegram menu.
        continue

    current_price = float(data["price"])
    change = float(data.get("change", 0))
    change_percent_text = data.get("change_percent", "0.00%")
    change_icon = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"

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
