import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "state.json"
ALARMS_FILE = "alarms.json"
CAIRO = ZoneInfo("Africa/Cairo")

MAIN_MENU = {
    "keyboard": [
        ["📊 الشاشة اللحظية", "🎯 فرص اليوم"],
        ["🔍 تحليل سهم", "🧠 التحليل المتقدم"],
        ["🟡 Golden Zone", "🚀 الإشارات النشطة"],
        ["🚨 تنبيهاتي", "💼 محفظتي"],
        ["📈 تقرير الأداء", "🔮 فرص بكرة"],
        ["🗺️ أداء القطاعات", "🤖 المساعد الذكي"],
        ["⚙️ الإعدادات"],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send(text, chat_id=None, menu=False):
    if not TOKEN:
        return
    payload = {
        "chat_id": str(chat_id or CHAT_ID),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if menu:
        payload["reply_markup"] = json.dumps(MAIN_MENU, ensure_ascii=False)
    r = requests.post(f"{API}/sendMessage", data=payload, timeout=15)
    r.raise_for_status()


def normalize_symbol(text):
    s = (text or "").strip().upper().replace(".CA", "")
    return s if s and len(s) <= 12 and s.replace("-", "").isalnum() else ""


def market_status():
    now = datetime.now(CAIRO)
    if now.weekday() >= 5:
        return "🔴 السوق مغلق — عطلة أسبوعية"
    mins = now.hour * 60 + now.minute
    if mins < 600:
        return "🟡 قبل جلسة التداول"
    if mins <= 870:
        return "🟢 جلسة التداول مفتوحة"
    return "🔴 السوق مغلق — بعد 14:30"


def snapshot(state):
    return state.get("pro_engine_snapshot") or {}


def fast_market_watch(chat_id, state):
    snap = snapshot(state)
    top = snap.get("top") or []
    if not top:
        send("⚠️ لا توجد لقطة سوق جاهزة الآن. سيعيد المحرك بناءها في دورة الفحص التالية.", chat_id, True)
        return
    lines = ["📊 <b>الشاشة اللحظية</b>", market_status(), ""]
    for i, x in enumerate(top[:12], 1):
        conf = x.get("confidence", "-")
        liq = x.get("liquidity_score", "-")
        lines.append(
            f"{i}) <b>{x.get('symbol','-')}</b>  {float(x.get('price',0)):.2f}  | Score {x.get('score','-')} | Conf {conf} | Liq {liq}"
        )
    regime = snap.get("market_regime") or {}
    if regime:
        lines.append(
            f"\n🧭 السوق: <b>{regime.get('name','-')}</b> | Breadth {float(regime.get('breadth',0)):.1f}% | Avg Score {float(regime.get('avg_score',0)):.1f}"
        )
    lines.append(
        f"\n🕒 آخر تحديث للمحرك: {snap.get('at','-')}\n"
        f"📡 المصدر: {snap.get('quote_source','غير محدد')}\n"
        "⚠️ <i>الشاشة تُفتح من آخر Snapshot جاهز لتكون سريعة؛ ليست شاشة تنفيذ لحظي قبل ربط Live Feed حقيقي.</i>"
    )
    send("\n".join(lines), chat_id, True)


def fast_opportunities(chat_id, state):
    top = (snapshot(state).get("top") or [])[:8]
    if not top:
        send("⚠️ لا توجد فرص مخزنة الآن.", chat_id, True); return
    lines = ["🎯 <b>أفضل فرص اليوم</b>", ""]
    for i, x in enumerate(top, 1):
        lines.append(
            f"{i}) <b>{x.get('symbol')}</b> | Score {x.get('score')} | Confidence {x.get('confidence','-')} | سعر {float(x.get('price',0)):.2f}"
        )
    lines.append("\n⚠️ قراءة فنية من آخر دورة للمحرك، وليست توصية شراء.")
    send("\n".join(lines), chat_id, True)


def fast_tomorrow(chat_id, state):
    items = snapshot(state).get("watchlist_next_session") or []
    if not items:
        send("🔮 لا توجد قائمة جلسة قادمة جاهزة الآن.", chat_id, True); return
    lines = ["🔮 <b>مرشحو الجلسة القادمة</b>", ""]
    for i, x in enumerate(items[:10], 1):
        lines.append(
            f"{i}) <b>{x.get('symbol')}</b> | Score {x.get('score')} | Trigger {float(x.get('trigger',0)):.2f} | Stop {float(x.get('stop',0)):.2f} | Conf {x.get('confidence','-')}"
        )
    send("\n".join(lines), chat_id, True)


def active_signals(chat_id, state):
    signals = state.get("signals") or {}
    active = [(s, v) for s, v in signals.items() if v.get("status") not in ("CLOSED_T3", "STOPPED")]
    if not active:
        send("🚀 <b>الإشارات النشطة</b>\n\nلا توجد إشارات نشطة حاليًا.", chat_id, True); return
    lines = ["🚀 <b>الإشارات النشطة</b>", ""]
    for sym, s in active[-12:]:
        lines.append(f"• <b>{sym}</b> | دخول {float(s.get('entry',0)):.2f} | Stop {float(s.get('stop',0)):.2f} | T{s.get('highest_target',0)}")
    send("\n".join(lines), chat_id, True)


def show_alarms(chat_id):
    data = load_json(ALARMS_FILE, {"alarms": []})
    items = [x for x in data.get("alarms", []) if x.get("active", True)]
    if not items:
        send("🚨 <b>تنبيهاتي</b>\n\nلا توجد تنبيهات نشطة.", chat_id, True); return
    lines = ["🚨 <b>التنبيهات النشطة</b>", ""]
    for x in items[:20]:
        lines.append(f"• <b>{x.get('symbol')}</b> {x.get('condition')} {float(x.get('price',0)):.2f}")
    send("\n".join(lines), chat_id, True)


def show_portfolio(chat_id, state):
    p = state.get("portfolio") or {}
    if not p:
        send("💼 <b>محفظتي</b>\n\nلا توجد مراكز مسجلة.", chat_id, True); return
    lines = ["💼 <b>محفظتي</b>", ""]
    for sym, pos in p.items():
        lines.append(f"• <b>{sym}</b> | كمية {float(pos.get('qty',0)):g} | متوسط {float(pos.get('avg',0)):.2f}")
    send("\n".join(lines), chat_id, True)


def performance(chat_id, state):
    hist = state.get("signal_history") or []
    if not hist:
        send("📈 <b>تقرير الأداء</b>\n\nلا توجد نتائج مغلقة كافية حتى الآن.", chat_id, True); return
    closed = [x for x in hist if x.get("result") in ("T3", "STOP")]
    if not closed:
        send("📈 <b>تقرير الأداء</b>\n\nالإشارات لا تزال تحت المتابعة.", chat_id, True); return
    wins = [x for x in closed if float(x.get("pnl_pct",0)) > 0]
    avg = sum(float(x.get("pnl_pct",0)) for x in closed) / len(closed)
    send(f"📈 <b>تقرير الأداء</b>\n\nالمغلقة: {len(closed)}\nنسبة النجاح: {len(wins)/len(closed)*100:.1f}%\nمتوسط النتيجة: {avg:+.2f}%", chat_id, True)


def analyze_symbol(chat_id, text, advanced=False):
    sym = normalize_symbol(text)
    if not sym:
        send("⚠️ اكتب رمز سهم صحيح مثل COMI.", chat_id, True); return
    try:
        from pro_engine import analyze
        a = analyze(sym)
        lines = [
            f"🧠 <b>{sym} — تحليل {'متقدم' if advanced else 'سريع'}</b>",
            f"السعر المرجعي: <b>{a['price']:.2f}</b>",
            f"Score: <b>{a['score']}/100</b>",
            f"RSI {a['rsi']:.1f} | ADX {a['adx']:.1f} | MFI {a['mfi']:.1f}",
            f"Volume {a['vr']:.2f}x",
            f"S1 {a['sup20']:.2f} | R1 {a['res20']:.2f}",
            f"T1 {a['t1']:.2f} | T2 {a['t2']:.2f} | T3 {a['t3']:.2f}",
            f"🛑 Stop {a['stop']:.2f}",
        ]
        if advanced:
            lines.append(f"Golden Zone: {a['golden_low']:.2f} — {a['golden_high']:.2f}")
            lines.append("🔎 " + " • ".join(a.get("why") or []))
        lines.append("\n⚠️ البيانات الحالية قد تكون متأخرة.")
        send("\n".join(lines), chat_id, True)
    except Exception:
        send(f"⚠️ تعذر تحليل <b>{sym}</b> حاليًا.", chat_id, True)


def handle(chat_id, text, state):
    text = (text or "").strip()
    if text in ("/start", "/menu", "🏠 القائمة الرئيسية"):
        state.pop("awaiting", None)
        send("📈 <b>EGX Smart Scanner PRO</b>\n\nاختر من القائمة الرئيسية.\n" + market_status(), chat_id, True)
        return True
    if text == "📊 الشاشة اللحظية":
        state.pop("awaiting", None); fast_market_watch(chat_id, state); return True
    if text == "🎯 فرص اليوم":
        state.pop("awaiting", None); fast_opportunities(chat_id, state); return True
    if text == "🔮 فرص بكرة":
        state.pop("awaiting", None); fast_tomorrow(chat_id, state); return True
    if text == "🚀 الإشارات النشطة":
        active_signals(chat_id, state); return True
    if text == "🚨 تنبيهاتي":
        show_alarms(chat_id); return True
    if text == "💼 محفظتي":
        show_portfolio(chat_id, state); return True
    if text == "📈 تقرير الأداء":
        performance(chat_id, state); return True
    if text == "🟡 Golden Zone":
        items = [x for x in (snapshot(state).get("top") or []) if x.get("score",0) >= 60]
        lines = ["🟡 <b>Golden Zone / Watchlist</b>", ""] + [f"• <b>{x.get('symbol')}</b> | Score {x.get('score')} | {float(x.get('price',0)):.2f}" for x in items[:8]]
        send("\n".join(lines), chat_id, True); return True
    if text == "🗺️ أداء القطاعات":
        regime = snapshot(state).get("market_regime") or {}
        send(f"🗺️ <b>ملخص السوق</b>\n\nالنظام: {regime.get('name','-')}\nBreadth: {float(regime.get('breadth',0)):.1f}%\nمتوسط الزخم: {float(regime.get('avg_mom',0)):+.2f}%\nمتوسط Score: {float(regime.get('avg_score',0)):.1f}", chat_id, True); return True
    if text == "🔍 تحليل سهم":
        state["awaiting"] = "analysis"; send("🔍 اكتب رمز السهم، مثال COMI", chat_id); return True
    if text == "🧠 التحليل المتقدم":
        state["awaiting"] = "advanced"; send("🧠 اكتب رمز السهم للتحليل المتقدم.", chat_id); return True
    if text == "🤖 المساعد الذكي":
        state["awaiting"] = "advanced"; send("🤖 اكتب رمز السهم وسأعطيك قراءة فنية متقدمة.", chat_id); return True
    if text == "⚙️ الإعدادات":
        snap = snapshot(state)
        send(f"⚙️ <b>الإعدادات</b>\n\nالفحص: كل 5 دقائق تقريبًا\nالمصدر: {snap.get('quote_source','غير محدد')}\nالوضع: {snap.get('quote_mode','-')}\nآخر Snapshot: {snap.get('at','-')}", chat_id, True); return True
    awaiting = state.get("awaiting")
    if awaiting in ("analysis", "advanced"):
        state.pop("awaiting", None)
        analyze_symbol(chat_id, text, advanced=(awaiting == "advanced"))
        return True
    send("استخدم القائمة الرئيسية 👇", chat_id, True)
    return True


def main():
    state = load_json(STATE_FILE, {})
    offset = int(state.get("telegram_update_offset", 0))
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{API}/getUpdates", params=params, timeout=20)
    r.raise_for_status()
    changed = False
    for u in r.json().get("result", []):
        uid = int(u.get("update_id", 0))
        state["telegram_update_offset"] = max(int(state.get("telegram_update_offset", 0)), uid + 1)
        changed = True
        m = u.get("message") or {}
        cid = str((m.get("chat") or {}).get("id", ""))
        text = m.get("text")
        if cid == str(CHAT_ID) and text:
            handle(cid, text, state)
    if changed:
        save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
