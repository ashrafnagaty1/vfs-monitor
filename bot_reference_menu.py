"""Reference-first Telegram shell for ReFo.

Applied near the end of the wrapper stack.  It owns the exact user-facing
main menu and the reference Trades submenu while delegating analytical work
to the existing ReFo engine.
"""
import bot_experience


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


# Exact visible hierarchy from the supplied reference screenshots.
REFERENCE_MAIN_MENU = _keyboard([
    ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"],
    ["💳 اشترك الآن / ترقية"],
    ["📈 أسهم المضاربة اليومية", "📊 الصفقات"],
    ["📈 تحليل الأسهم", "♟️ التحليل المتقدم"],
    ["💼 المحافظ والتنبيهات", "👤 حسابي"],
])

TRADES_MENU = _keyboard([
    ["📊 صفقات مفتوحة", "✅ تحقق الهدف الأول", "✅ تحقق الهدف الثاني"],
    ["✅ تحقق الهدف الثالث", "⬅️ العودة للقائمة الرئيسية"],
])

ALIASES = {
    "📈 تحليل الأسهم": "🔍 تحليل سهم",
    "📈 أسهم المضاربة اليومية": "🎯 فرص اليوم",
    "♟️ التحليل المتقدم": "🧠 التحليل المتقدم",
    "💳 اشترك الآن / ترقية": "💳 اشتراك / ترقية",
    "📊 الشاشة اللحظية": "🖥️ الشاشة اللحظية",
    "⬅️ العودة للقائمة الرئيسية": "🏠 القائمة الرئيسية",
}


def _as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return list(v.values())
    return []


def _num(v, digits=3):
    try:
        s = f"{float(v):.{digits}f}"
        return s.rstrip("0").rstrip(".")
    except Exception:
        return "-"


def _runtime(base):
    try:
        return base.load_json(base.STATE_FILE, {}) or {}
    except Exception:
        return {}


def _trade_rows(state):
    p = state.get("signal_portfolio") or {}
    lc = state.get("trade_lifecycle") or {}
    opened = _as_list(p.get("open_positions"))
    closed = _as_list(p.get("closed_trades"))
    plans = _as_list(lc.get("plans"))
    return opened, closed, plans


def _open_text(state):
    opened, _, plans = _trade_rows(state)
    rows = opened or [p for p in plans if str(p.get("lifecycle_status") or p.get("status") or "").upper() in ("ENTRY","T1","T2")]
    lines = ["📊 <b>صفقات اليوم (إشارات شراء)</b>", ""]
    if not rows:
        return "\n".join(lines + ["لا توجد صفقات مفتوحة مسجلة حاليًا."])
    for x in rows[:18]:
        sym = x.get("symbol") or "-"
        entry = x.get("entry_price") or x.get("trigger")
        stop = x.get("dynamic_stop") or x.get("initial_stop") or x.get("stop")
        t1 = x.get("target1") or x.get("t1")
        t2 = x.get("target2") or x.get("t2")
        t3 = x.get("target3") or x.get("t3")
        lines += [
            f"🔹 <b>{sym}</b>",
            f"💰 سعر الشراء: <b>{_num(entry)}</b>",
            f"🎯 الهدف الأول: {_num(t1)}",
            f"🎯 الهدف الثاني: {_num(t2)}",
            f"🎯 الهدف الثالث: {_num(t3)}",
            f"🛑 وقف الخسارة: {_num(stop)}",
            "",
        ]
    lines.append("⚠️ تعرض ReFo فقط الأحداث المسجلة فعليًا؛ WATCH المتأخر ليس صفقة.")
    return "\n".join(lines)


def _hit_text(state, stage):
    opened, closed, plans = _trade_rows(state)
    order = {"T1": 1, "T2": 2, "T3": 3}
    need = order[stage]
    all_rows = opened + closed + plans
    seen = set()
    rows = []
    for x in all_rows:
        sid = x.get("signal_id") or (x.get("symbol"), x.get("entry_price") or x.get("trigger"))
        if sid in seen:
            continue
        status = str(x.get("lifecycle_status") or x.get("stage") or x.get("status") or "").upper()
        reached = order.get(status, 0) >= need
        events = _as_list(x.get("events") or x.get("event_log"))
        reached = reached or any(str(e.get("event") or e.get("type") or "").upper() == stage for e in events if isinstance(e, dict))
        if reached:
            seen.add(sid)
            rows.append(x)
    label = {"T1": "الهدف الأول", "T2": "الهدف الثاني", "T3": "الهدف الثالث"}[stage]
    lines = [f"✅ <b>صفقات حققت {label}</b>", ""]
    if not rows:
        return "\n".join(lines + ["لا توجد صفقات مسجلة حققت هذا الهدف حتى الآن."])
    for x in rows[:20]:
        target = x.get({"T1":"target1","T2":"target2","T3":"target3"}[stage]) or x.get(stage.lower())
        lines += [
            f"🔹 <b>{x.get('symbol','-')}</b>",
            f"💰 سعر الشراء: {_num(x.get('entry_price') or x.get('trigger'))}",
            f"🎯 {label}: <b>{_num(target)}</b>",
            f"🆔 <code>{x.get('signal_id','-')}</code>",
            "",
        ]
    return "\n".join(lines)


def apply(base):
    original = base.handle
    base.MAIN_MENU = REFERENCE_MAIN_MENU
    bot_experience.MAIN_MENU = REFERENCE_MAIN_MENU

    def handle(chat_id, text, state):
        raw = (text or "").strip()
        if raw in ("/start", "/menu", "🏠 القائمة الرئيسية", "⬅️ العودة للقائمة الرئيسية"):
            state.pop("awaiting", None)
            bot_experience._send_keyboard(
                base,
                "🚀 <b>مرحبًا بك في ReFo . EGX Smart Trader</b>\n\n"
                "اختر من القائمة بالأسفل 👇\n\n"
                "🖥️ الشاشة اللحظية · 🤖 المساعد الذكي\n"
                "📈 المضاربة اليومية · 📊 الصفقات\n"
                "📈 تحليل الأسهم · ♟️ التحليل المتقدم",
                chat_id,
                REFERENCE_MAIN_MENU,
            )
            return True
        if raw == "📊 الصفقات":
            state.pop("awaiting", None)
            bot_experience._send_keyboard(base, "📊 <b>الصفقات</b>\nاختر نوع الصفقات:", chat_id, TRADES_MENU)
            return True
        if raw == "📊 صفقات مفتوحة":
            bot_experience._send_keyboard(base, _open_text(_runtime(base)), chat_id, TRADES_MENU)
            return True
        if raw in ("✅ تحقق الهدف الأول", "✅ تحقق الهدف الثاني", "✅ تحقق الهدف الثالث"):
            stage = {"✅ تحقق الهدف الأول":"T1","✅ تحقق الهدف الثاني":"T2","✅ تحقق الهدف الثالث":"T3"}[raw]
            bot_experience._send_keyboard(base, _hit_text(_runtime(base), stage), chat_id, TRADES_MENU)
            return True
        target = ALIASES.get(raw, raw)
        return original(chat_id, target, state)

    base.handle = handle
    return base


def self_test():
    assert REFERENCE_MAIN_MENU["keyboard"][0] == ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"]
    assert REFERENCE_MAIN_MENU["keyboard"][1] == ["💳 اشترك الآن / ترقية"]
    assert ["📈 أسهم المضاربة اليومية", "📊 الصفقات"] in REFERENCE_MAIN_MENU["keyboard"]
    assert TRADES_MENU["keyboard"][0] == ["📊 صفقات مفتوحة", "✅ تحقق الهدف الأول", "✅ تحقق الهدف الثاني"]
    assert ALIASES["♟️ التحليل المتقدم"] == "🧠 التحليل المتقدم"
    print("reference clone phase1 self-test: PASS")


if __name__ == "__main__":
    self_test()
