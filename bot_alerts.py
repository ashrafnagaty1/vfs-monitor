import json
import uuid
from datetime import datetime


ALERTS_MENU = {
    "keyboard": [
        ["➕ إضافة تنبيه", "📋 التنبيهات النشطة"],
        ["🗑️ حذف تنبيه", "🔄 تحديث التنبيهات"],
        ["🏠 القائمة الرئيسية"],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

CONDITION_MENU = {
    "keyboard": [
        ["⬆️ أعلى من / يساوي", "⬇️ أقل من / يساوي"],
        ["↩️ رجوع للتنبيهات", "🏠 القائمة الرئيسية"],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def _send(base, chat_id, text, keyboard=ALERTS_MENU):
    if not base.TOKEN:
        return
    payload = {
        "chat_id": str(chat_id or base.CHAT_ID),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": json.dumps(keyboard, ensure_ascii=False),
    }
    r = base.requests.post(f"{base.API}/sendMessage", data=payload, timeout=15)
    r.raise_for_status()


def _load(base):
    data = base.load_json(base.ALARMS_FILE, {"alarms": []}) or {"alarms": []}
    if not isinstance(data, dict):
        data = {"alarms": []}
    if not isinstance(data.get("alarms"), list):
        data["alarms"] = []
    return data


def _active(data):
    return [x for x in data.get("alarms", []) if isinstance(x, dict) and x.get("active", True)]


def _condition_label(value):
    return "⬆️ ≥" if value == ">=" else "⬇️ ≤"


def _list_text(base):
    items = _active(_load(base))
    if not items:
        return (
            "🚨 <b>التنبيهات الذكية</b>\n\n"
            "لا توجد تنبيهات نشطة حاليًا.\n\n"
            "يمكنك إضافة تنبيه لسعر أعلى/يساوي أو أقل/يساوي من الأزرار بالأسفل."
        )
    lines = ["🚨 <b>التنبيهات الذكية النشطة</b>", ""]
    for i, item in enumerate(items[:20], 1):
        sent = int(item.get("notifications_sent") or 0)
        max_n = int(item.get("max_notifications") or 1)
        lines.append(
            f"{i}) <b>{item.get('symbol', '-')}</b> {_condition_label(item.get('condition'))} "
            f"<b>{float(item.get('price') or 0):.2f}</b> · إرسال {sent}/{max_n}"
        )
    lines.extend([
        "",
        "🔕 كل تنبيه يُنشأ افتراضيًا بإشعار واحد لمنع التكرار المزعج.",
        "📡 التنفيذ يعتمد على آخر سعر موثوق يصل للمحرك؛ لا يُفترض أنه LIVE ما لم يكن مصدر الأسعار نفسه لحظيًا ومؤكدًا.",
    ])
    return "\n".join(lines)


def _parse_price(text):
    try:
        value = float(str(text).strip().replace(",", "."))
        if value <= 0 or value > 1_000_000_000:
            return None
        return value
    except Exception:
        return None


def _add_alert(base, symbol, condition, price):
    data = _load(base)
    # De-duplicate the exact same active rule instead of creating alert spam.
    for item in _active(data):
        if (
            str(item.get("symbol") or "").upper() == symbol
            and item.get("condition") == condition
            and abs(float(item.get("price") or 0) - price) < 1e-9
        ):
            return item, False
    item = {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "condition": condition,
        "price": price,
        "max_notifications": 1,
        "notifications_sent": 0,
        "active": True,
        "mode": "telegram",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    data["alarms"].append(item)
    base.save_json(base.ALARMS_FILE, data)
    return item, True


def _delete_symbol(base, symbol):
    data = _load(base)
    count = 0
    for item in data.get("alarms", []):
        if (
            isinstance(item, dict)
            and item.get("active", True)
            and str(item.get("symbol") or "").upper() == symbol
        ):
            item["active"] = False
            count += 1
    if count:
        base.save_json(base.ALARMS_FILE, data)
    return count


def apply(base):
    """Add a button-first alert flow without changing the market engine."""
    original_handle = base.handle

    def alert_handle(chat_id, text, state):
        text = (text or "").strip()

        if text in ("🚨 تنبيهاتي", "📋 التنبيهات النشطة", "🔄 تحديث التنبيهات", "↩️ رجوع للتنبيهات"):
            state.pop("awaiting", None)
            for key in ("alert_symbol", "alert_condition"):
                state.pop(key, None)
            _send(base, chat_id, _list_text(base), ALERTS_MENU)
            return True

        if text == "➕ إضافة تنبيه":
            state["awaiting"] = "alert_symbol"
            state.pop("alert_symbol", None)
            state.pop("alert_condition", None)
            _send(base, chat_id, "➕ <b>إضافة تنبيه سعر</b>\n\nاكتب رمز السهم، مثال <b>COMI</b>.", ALERTS_MENU)
            return True

        if text == "🗑️ حذف تنبيه":
            state["awaiting"] = "alert_delete_symbol"
            _send(base, chat_id, "🗑️ اكتب رمز السهم لحذف كل تنبيهاته النشطة، مثال <b>COMI</b>.", ALERTS_MENU)
            return True

        if state.get("awaiting") == "alert_symbol":
            symbol = base.normalize_symbol(text)
            if not symbol:
                _send(base, chat_id, "⚠️ رمز غير صالح. اكتب مثل <b>COMI</b>.", ALERTS_MENU)
                return True
            state["alert_symbol"] = symbol
            state["awaiting"] = "alert_condition"
            _send(base, chat_id, f"🚨 <b>{symbol}</b>\nاختر شرط التنبيه.", CONDITION_MENU)
            return True

        if state.get("awaiting") == "alert_condition":
            mapping = {"⬆️ أعلى من / يساوي": ">=", "⬇️ أقل من / يساوي": "<="}
            condition = mapping.get(text)
            if not condition:
                _send(base, chat_id, "اختر شرطًا من الزرين المتاحين.", CONDITION_MENU)
                return True
            state["alert_condition"] = condition
            state["awaiting"] = "alert_price"
            _send(
                base,
                chat_id,
                f"💵 اكتب سعر التنبيه لـ <b>{state.get('alert_symbol')}</b> ({_condition_label(condition)}).",
                ALERTS_MENU,
            )
            return True

        if state.get("awaiting") == "alert_price":
            price = _parse_price(text)
            if price is None:
                _send(base, chat_id, "⚠️ اكتب سعرًا موجبًا صحيحًا، مثال <b>75.50</b>.", ALERTS_MENU)
                return True
            symbol = base.normalize_symbol(state.get("alert_symbol"))
            condition = state.get("alert_condition")
            if not symbol or condition not in (">=", "<="):
                state.pop("awaiting", None)
                _send(base, chat_id, "⚠️ انتهت جلسة إنشاء التنبيه. ابدأ من ➕ إضافة تنبيه.", ALERTS_MENU)
                return True
            _item, created = _add_alert(base, symbol, condition, price)
            state.pop("awaiting", None)
            state.pop("alert_symbol", None)
            state.pop("alert_condition", None)
            if created:
                msg = (
                    f"✅ تم إنشاء تنبيه <b>{symbol}</b> {_condition_label(condition)} <b>{price:.2f}</b>.\n"
                    "سيُرسل مرة واحدة افتراضيًا لمنع التكرار."
                )
            else:
                msg = "ℹ️ نفس التنبيه موجود ونشط بالفعل؛ لم أضف نسخة مكررة."
            _send(base, chat_id, msg + "\n\n" + _list_text(base), ALERTS_MENU)
            return True

        if state.get("awaiting") == "alert_delete_symbol":
            symbol = base.normalize_symbol(text)
            if not symbol:
                _send(base, chat_id, "⚠️ رمز غير صالح. اكتب مثل <b>COMI</b>.", ALERTS_MENU)
                return True
            state.pop("awaiting", None)
            count = _delete_symbol(base, symbol)
            if count:
                msg = f"🗑️ تم تعطيل <b>{count}</b> تنبيه نشط للسهم <b>{symbol}</b>."
            else:
                msg = f"ℹ️ لا توجد تنبيهات نشطة للسهم <b>{symbol}</b>."
            _send(base, chat_id, msg + "\n\n" + _list_text(base), ALERTS_MENU)
            return True

        return original_handle(chat_id, text, state)

    base.handle = alert_handle
    return base


def self_test():
    assert _parse_price("75.5") == 75.5
    assert _parse_price("75,5") == 75.5
    assert _parse_price("0") is None
    assert _condition_label(">=").startswith("⬆️")
    assert _condition_label("<=").startswith("⬇️")
    print("bot alerts self-test: PASS")


if __name__ == "__main__":
    self_test()
