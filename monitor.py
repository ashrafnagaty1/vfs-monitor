import os
import json
import math
import uuid
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ALARMS_FILE = "alarms.json"
STATE_FILE = "state.json"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
CAIRO = ZoneInfo("Africa/Cairo")

UNIVERSE = [
    "COMI", "SWDY", "EAST", "ABUK", "FWRY", "TMGH", "ORAS", "ORHD",
    "ETEL", "MFPC", "SKPC", "JUFO", "ISPH", "PHDC", "EFIH", "CIRA",
    "ALCN", "AMOC", "CCAP", "AUTO", "ADIB", "FAIT", "MASR", "HELI",
    "DTPP", "KABO", "AIDC", "EPCO", "ARCC", "ASCM", "ETRS", "TALM"
]

SECTORS = {
    "COMI": "بنوك", "ADIB": "بنوك", "FAIT": "بنوك", "MASR": "عقارات",
    "SWDY": "صناعة", "ORAS": "مقاولات", "TMGH": "عقارات", "ORHD": "عقارات",
    "PHDC": "عقارات", "HELI": "عقارات", "EAST": "أغذية/تبغ", "JUFO": "أغذية",
    "ABUK": "بتروكيماويات", "MFPC": "أسمدة", "SKPC": "بتروكيماويات", "AMOC": "طاقة",
    "ETEL": "اتصالات", "FWRY": "تكنولوجيا مالية", "EFIH": "تكنولوجيا", "CIRA": "تعليم",
    "ALCN": "نقل", "AUTO": "سيارات", "ISPH": "دواء", "DTPP": "تعبئة وطباعة",
    "KABO": "منسوجات", "AIDC": "دواء", "EPCO": "دواء", "ARCC": "أسمنت",
    "ASCM": "أسمنت", "ETRS": "نقل", "TALM": "تعليم", "CCAP": "استثمار"
}

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


def send(message, chat_id=None, menu=False):
    if not TOKEN:
        return
    payload = {
        "chat_id": str(chat_id or CHAT_ID),
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if menu:
        payload["reply_markup"] = json.dumps(MAIN_MENU, ensure_ascii=False)
    r = requests.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=20)
    r.raise_for_status()


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_symbol(text):
    s = (text or "").strip().upper().replace(".CA", "")
    return s if s and len(s) <= 12 and s.replace("-", "").isalnum() else ""


def now_cairo():
    return datetime.now(CAIRO)


def is_market_day(now=None):
    now = now or now_cairo()
    return now.weekday() < 5


def in_session(now=None):
    now = now or now_cairo()
    mins = now.hour * 60 + now.minute
    return is_market_day(now) and 600 <= mins <= 870


def market_status():
    now = now_cairo()
    if not is_market_day(now):
        return "🔴 السوق مغلق — عطلة أسبوعية"
    mins = now.hour * 60 + now.minute
    if mins < 600:
        return "🟡 قبل جلسة التداول"
    if mins <= 870:
        return "🟢 جلسة التداول مفتوحة"
    return "🔴 السوق مغلق — بعد 14:30"


def get_quote(symbol):
    r = requests.get(f"https://demo.borsa.ashh.me/demo/quote/{symbol}", timeout=15)
    if r.status_code == 429:
        raise RuntimeError("DATA_LIMIT")
    r.raise_for_status()
    return r.json()


def get_history(symbol, period="6mo", interval="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.CA"
    r = requests.get(
        url,
        params={"range": period, "interval": interval},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    r.raise_for_status()
    result = r.json().get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError("NO_HISTORY")
    q = result[0].get("indicators", {}).get("quote", [{}])[0]
    ts = result[0].get("timestamp", [])
    rows = []
    closes = q.get("close", [])
    for i in range(len(closes)):
        vals = {}
        for k in ("open", "high", "low", "close", "volume"):
            arr = q.get(k) or []
            vals[k] = arr[i] if i < len(arr) else None
        vals["ts"] = ts[i] if i < len(ts) else None
        if all(vals[k] is not None for k in ("open", "high", "low", "close")):
            rows.append(vals)
    if len(rows) < 35:
        raise RuntimeError("SHORT_HISTORY")
    return rows


def ema(values, n):
    if not values:
        return 0.0
    k = 2 / (n + 1)
    out = float(values[0])
    for x in values[1:]:
        out = float(x) * k + out * (1 - k)
    return out


def sma(values, n):
    vals = values[-n:]
    return sum(vals) / len(vals) if vals else 0.0


def rsi(values, n=14):
    if len(values) <= n:
        return 50.0
    gains, losses = [], []
    for a, b in zip(values[-n - 1:-1], values[-n:]):
        d = b - a
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag, al = sum(gains) / n, sum(losses) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def atr(rows, n=14):
    tr = []
    for i in range(1, len(rows)):
        h, l, pc = float(rows[i]["high"]), float(rows[i]["low"]), float(rows[i - 1]["close"])
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(tr[-n:]) / min(n, len(tr)) if tr else 0.0


def candle_patterns(rows):
    if len(rows) < 3:
        return []
    p, c = rows[-2], rows[-1]
    po, pc, ph, pl = map(float, (p["open"], p["close"], p["high"], p["low"]))
    o, cl, h, l = map(float, (c["open"], c["close"], c["high"], c["low"]))
    body = abs(cl - o)
    rng = max(h - l, 0.0001)
    out = []
    if pc < po and cl > o and o <= pc and cl >= po:
        out.append("Bullish Engulfing")
    lower_wick = min(o, cl) - l
    upper_wick = h - max(o, cl)
    if body / rng <= 0.35 and lower_wick >= body * 2 and lower_wick > upper_wick * 1.5:
        out.append("Hammer")
    if cl > o and cl > ph and (cl - o) / rng > 0.45:
        out.append("Bullish Breakout Candle")
    return out


def stochastic(rows, n=14):
    r = rows[-n:]
    hh = max(float(x["high"]) for x in r)
    ll = min(float(x["low"]) for x in r)
    c = float(r[-1]["close"])
    return 50.0 if hh == ll else (c - ll) / (hh - ll) * 100


def technical(symbol):
    rows = get_history(symbol)
    closes = [float(x["close"]) for x in rows]
    highs = [float(x["high"]) for x in rows]
    lows = [float(x["low"]) for x in rows]
    vols = [float(x.get("volume") or 0) for x in rows]
    opens = [float(x["open"]) for x in rows]
    price = closes[-1]
    e20 = ema(closes[-100:], 20)
    e50 = ema(closes[-120:], 50)
    e200 = ema(closes, min(200, len(closes)))
    rv = rsi(closes)
    macd = ema(closes[-100:], 12) - ema(closes[-100:], 26)
    macd_prev = ema(closes[-101:-1], 12) - ema(closes[-101:-1], 26)
    a = atr(rows)
    support = min(lows[-20:])
    resistance = max(highs[-20:-1]) if len(highs) > 1 else highs[-1]
    support2 = min(lows[-50:])
    resistance2 = max(highs[-50:-1]) if len(highs) > 1 else highs[-1]
    avg_vol = sum(vols[-21:-1]) / max(1, len(vols[-21:-1]))
    vol_ratio = vols[-1] / avg_vol if avg_vol else 1.0
    momentum = (price / closes[-6] - 1) * 100 if len(closes) >= 6 else 0.0
    stoch = stochastic(rows)
    patterns = candle_patterns(rows)
    bb_mid = sma(closes, 20)
    variance = sum((x - bb_mid) ** 2 for x in closes[-20:]) / min(20, len(closes))
    bb_std = math.sqrt(max(variance, 0))
    bb_low = bb_mid - 2 * bb_std
    bb_high = bb_mid + 2 * bb_std

    golden_low = max(support, e20 - a * 0.55)
    golden_high = min(e20 + a * 0.35, price + a * 0.15)
    if golden_low > golden_high:
        golden_low, golden_high = min(golden_low, golden_high), max(golden_low, golden_high)
    in_golden = golden_low <= price <= golden_high and e20 >= e50 * 0.99 and 35 <= rv <= 60

    breakout_distance = (resistance - price) / price * 100 if price else 999
    score = 0
    reasons = []
    if price > e20:
        score += 12; reasons.append("السعر أعلى EMA20")
    if e20 > e50:
        score += 16; reasons.append("EMA20 أعلى EMA50")
    if e50 > e200:
        score += 8; reasons.append("الاتجاه الطويل داعم")
    if 50 <= rv <= 70:
        score += 14; reasons.append("RSI إيجابي")
    elif 40 <= rv < 50:
        score += 7
    if macd > 0:
        score += 12; reasons.append("MACD إيجابي")
    if macd > macd_prev:
        score += 8; reasons.append("زخم MACD يتحسن")
    if vol_ratio >= 1.3:
        score += 12; reasons.append("حجم تداول قوي")
    elif vol_ratio >= 1.05:
        score += 5
    if price >= resistance * 0.995:
        score += 10; reasons.append("اختراق/ملامسة مقاومة")
    elif 0 <= breakout_distance <= 3:
        score += 5; reasons.append("قريب من التفعيل")
    if momentum > 0:
        score += 4
    if patterns:
        score += min(8, 4 * len(patterns)); reasons.append("نموذج شموع صاعد")
    if in_golden:
        score += 6; reasons.append("داخل Golden Zone")
    if rv > 78:
        score -= 8
    score = max(0, min(100, score))

    if score >= 78:
        status, icon = "ENTRY", "🟢"
    elif score >= 62:
        status, icon = "WATCH", "🟡"
    else:
        status, icon = "NEUTRAL", "⚪"

    risk = max(a * 1.25, price * 0.025)
    stop = max(support * 0.995, price - risk)
    unit = max(price - stop, a, price * 0.015)
    t1, t2, t3 = price + unit, price + unit * 2, price + unit * 3
    rr = (t2 - price) / max(price - stop, 0.0001)

    if price >= resistance * 0.995:
        pattern = "اختراق مقاومة"
    elif patterns:
        pattern = " + ".join(patterns[:2])
    elif in_golden:
        pattern = "Golden Zone — ارتداد محتمل"
    elif price > e20 > e50:
        pattern = "اتجاه صاعد"
    elif price <= support * 1.04:
        pattern = "منطقة ارتداد"
    else:
        pattern = "تجميع/محايد"

    return {
        "symbol": symbol,
        "sector": SECTORS.get(symbol, "أخرى"),
        "price": price,
        "score": score,
        "status": status,
        "icon": icon,
        "rsi": rv,
        "stoch": stoch,
        "macd": macd,
        "macd_prev": macd_prev,
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "volume_ratio": vol_ratio,
        "support": support,
        "support2": support2,
        "resistance": resistance,
        "resistance2": resistance2,
        "atr": a,
        "momentum": momentum,
        "entry_low": price - a * 0.25,
        "entry_high": price + a * 0.25,
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "rr": rr,
        "pattern": pattern,
        "patterns": patterns,
        "reasons": reasons[:6],
        "golden_low": golden_low,
        "golden_high": golden_high,
        "in_golden": in_golden,
        "breakout_distance": breakout_distance,
        "bb_low": bb_low,
        "bb_high": bb_high,
        "open": opens[-1],
    }


def analysis_text(a, advanced=False):
    trend = "صاعد" if a["ema20"] > a["ema50"] else "هابط/ضعيف"
    macd_text = "إيجابي" if a["macd"] > 0 else "سلبي"
    base = (
        f"{a['icon']} <b>{a['symbol']} — {a['status']}</b>\n"
        f"🏷️ القطاع: {a['sector']}\n"
        f"💰 السعر المرجعي: <b>{a['price']:.2f}</b>\n"
        f"🧠 قوة التوافق: <b>{a['score']}/100</b>\n"
        f"📈 الاتجاه: <b>{trend}</b> | RSI <b>{a['rsi']:.1f}</b> | MACD <b>{macd_text}</b>\n"
        f"📦 الحجم: <b>{a['volume_ratio']:.2f}x</b> | النموذج: <b>{a['pattern']}</b>\n"
        f"🧱 S1 {a['support']:.2f} | S2 {a['support2']:.2f}\n"
        f"🧱 R1 {a['resistance']:.2f} | R2 {a['resistance2']:.2f}\n\n"
        f"🎯 <b>خطة فنية آلية</b>\n"
        f"منطقة دخول: <b>{a['entry_low']:.2f} — {a['entry_high']:.2f}</b>\n"
        f"T1 <b>{a['t1']:.2f}</b> | T2 <b>{a['t2']:.2f}</b> | T3 <b>{a['t3']:.2f}</b>\n"
        f"🛑 Stop <b>{a['stop']:.2f}</b> | R/R إلى T2 <b>{a['rr']:.2f}</b>\n"
    )
    if advanced:
        base += (
            f"\n🧪 <b>توافق متقدم</b>\n"
            f"Stochastic: {a['stoch']:.1f}\n"
            f"EMA20/50/200: {a['ema20']:.2f} / {a['ema50']:.2f} / {a['ema200']:.2f}\n"
            f"Bollinger: {a['bb_low']:.2f} — {a['bb_high']:.2f}\n"
            f"Golden Zone: {a['golden_low']:.2f} — {a['golden_high']:.2f}\n"
            f"بعد المقاومة: {a['breakout_distance']:.2f}%\n"
            f"نماذج: {', '.join(a['patterns']) if a['patterns'] else 'لا يوجد نموذج شموع مؤكد'}\n"
        )
    base += f"\n🔎 {' • '.join(a['reasons']) if a['reasons'] else 'لا يوجد توافق فني قوي حاليًا'}\n"
    base += "\n⚠️ <i>البيانات الحالية قد تكون متأخرة؛ التحليل ليس أمر شراء أو بيع.</i>"
    return base


def scan_market(limit=10):
    found = []
    for symbol in UNIVERSE:
        try:
            found.append(technical(symbol))
        except Exception:
            continue
    found.sort(key=lambda x: (x["score"], x["volume_ratio"], x["momentum"]), reverse=True)
    return found[:limit]


def send_opportunities(chat_id):
    items = scan_market(8)
    if not items:
        send("⚠️ تعذر تكوين قائمة الفرص من مصدر البيانات الحالي.", chat_id, True)
        return
    lines = ["🎯 <b>أفضل فرص اليوم</b>", market_status(), ""]
    for i, a in enumerate(items, 1):
        lines.append(
            f"{i}) {a['icon']} <b>{a['symbol']}</b> — {a['score']}/100 — {a['status']}\n"
            f"   {a['price']:.2f} | RSI {a['rsi']:.0f} | Vol {a['volume_ratio']:.1f}x | {a['pattern']}"
        )
    lines.append("\n⚠️ <i>ترتيب فني آلي من بيانات قد تكون متأخرة.</i>")
    send("\n".join(lines), chat_id, True)


def send_market_watch(chat_id):
    items = scan_market(12)
    lines = ["📊 <b>Market Watch — EGX Smart Scanner</b>", market_status(), ""]
    for a in items:
        arrow = "▲" if a["momentum"] > 0 else "▼"
        lines.append(
            f"{a['icon']} <b>{a['symbol']}</b> {a['price']:.2f}  {arrow}{abs(a['momentum']):.1f}%  "
            f"V {a['volume_ratio']:.1f}x  Score {a['score']}"
        )
    lines.append("\nℹ️ <i>شاشة تحليل؛ ليست أسعار تنفيذ لحظية قبل ربط Live Feed مرخص.</i>")
    send("\n".join(lines), chat_id, True)


def send_golden_zones(chat_id):
    items = [a for a in scan_market(16) if a["in_golden"]]
    if not items:
        send("🟡 <b>Golden Zone</b>\n\nلا توجد حاليًا فرص تستوفي شروط منطقة الارتداد.", chat_id, True)
        return
    lines = ["🟡 <b>Golden Zone — ارتداد محتمل</b>", ""]
    for a in items[:8]:
        lines.append(
            f"• <b>{a['symbol']}</b> {a['price']:.2f} | Zone {a['golden_low']:.2f}-{a['golden_high']:.2f} | "
            f"RSI {a['rsi']:.0f} | Score {a['score']}"
        )
    lines.append("\n⚠️ يحتاج تأكيد سعري/حجمي قبل أي قرار.")
    send("\n".join(lines), chat_id, True)


def tomorrow_opportunities(chat_id):
    items = scan_market(16)
    candidates = [a for a in items if a["score"] >= 58 and -1 <= a["breakout_distance"] <= 5]
    candidates.sort(key=lambda a: (a["score"], -abs(a["breakout_distance"])), reverse=True)
    if not candidates:
        candidates = [a for a in items if a["score"] >= 58][:6]
    lines = ["🔮 <b>مرشحو الجلسة القادمة</b>", ""]
    for i, a in enumerate(candidates[:7], 1):
        trigger = a["resistance"]
        lines.append(
            f"{i}) <b>{a['symbol']}</b> | Score {a['score']} | {a['pattern']}\n"
            f"   تفعيل تقريبي فوق {trigger:.2f} | Stop مرجعي {a['stop']:.2f}"
        )
    lines.append("\n⚠️ <i>قائمة مراقبة وليست توصية شراء.</i>")
    send("\n".join(lines), chat_id, True)


def sector_performance(chat_id):
    items = scan_market(len(UNIVERSE))
    agg = {}
    for a in items:
        d = agg.setdefault(a["sector"], {"sum": 0.0, "score": 0.0, "n": 0})
        d["sum"] += a["momentum"]
        d["score"] += a["score"]
        d["n"] += 1
    ranked = sorted(
        ((sec, d["sum"] / d["n"], d["score"] / d["n"]) for sec, d in agg.items() if d["n"]),
        key=lambda x: (x[1], x[2]),
        reverse=True,
    )
    lines = ["🗺️ <b>أداء القطاعات — تقدير فني</b>", ""]
    for sec, mom, sc in ranked[:10]:
        icon = "🟢" if mom > 0 else "🔴" if mom < 0 else "⚪"
        lines.append(f"{icon} {sec}: زخم {mom:+.2f}% | متوسط Score {sc:.0f}")
    send("\n".join(lines), chat_id, True)


def show_alarms(chat_id, alarms_data):
    active = [x for x in alarms_data.get("alarms", []) if x.get("active", True)]
    if not active:
        send("🚨 <b>تنبيهاتي</b>\n\nلا توجد تنبيهات نشطة.\nأضف: <code>/alert COMI >= 80</code>", chat_id, True)
        return
    lines = ["🚨 <b>التنبيهات النشطة</b>", ""]
    for x in active:
        lines.append(
            f"• <b>{x.get('symbol')}</b> {x.get('condition')} {float(x.get('price', 0)):.2f} "
            f"| مرات {x.get('max_notifications', 1)} | ID <code>{str(x.get('id'))[:8]}</code>"
        )
    lines.append("\nحذف بالرمز: <code>/remove_alert COMI</code>")
    send("\n".join(lines), chat_id, True)


def add_alarm_command(alarms_data, text, chat_id):
    try:
        parts = text.split()
        sym = normalize_symbol(parts[1])
        cond = parts[2]
        price = float(parts[3])
        if not sym or cond not in (">=", "<=") or price <= 0:
            raise ValueError
        alarms_data.setdefault("alarms", []).append({
            "id": str(uuid.uuid4()), "symbol": sym, "condition": cond, "price": price,
            "max_notifications": 1, "active": True, "mode": "telegram",
            "created_at": now_cairo().isoformat()
        })
        save_json(ALARMS_FILE, alarms_data)
        send(f"✅ تنبيه جديد: <b>{sym} {cond} {price:.2f}</b>", chat_id, True)
        return True
    except Exception:
        send("الصيغة: <code>/alert COMI >= 80</code>", chat_id, True)
        return False


def remove_alarm_command(alarms_data, text, chat_id):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send("الصيغة: <code>/remove_alert COMI</code>", chat_id, True)
        return False
    key = parts[1].strip().upper()
    removed = 0
    for a in alarms_data.get("alarms", []):
        if a.get("active", True) and (a.get("symbol", "").upper() == key or str(a.get("id", "")).startswith(key.lower())):
            a["active"] = False
            removed += 1
    if removed:
        save_json(ALARMS_FILE, alarms_data)
        send(f"✅ تم إيقاف {removed} تنبيه.", chat_id, True)
        return True
    send("لم أجد تنبيهًا مطابقًا.", chat_id, True)
    return False


def show_portfolio(chat_id, state):
    p = state.setdefault("portfolio", {})
    if not p:
        send("💼 <b>محفظتي</b>\n\nلا توجد مراكز.\nأضف: <code>/add_trade COMI 100 75.50</code>", chat_id, True)
        return
    lines = ["💼 <b>محفظتي</b>", ""]
    total_cost = total_value = 0.0
    for sym, pos in p.items():
        qty, avg = float(pos["qty"]), float(pos["avg"])
        try:
            a = technical(sym)
            current = a["price"]
            risk = "منخفض" if a["score"] >= 70 else "متوسط" if a["score"] >= 50 else "مرتفع"
        except Exception:
            current, risk = avg, "غير متاح"
        cost, value = qty * avg, qty * current
        pnl = value - cost
        pct = pnl / cost * 100 if cost else 0
        total_cost += cost
        total_value += value
        icon = "🟢" if pnl >= 0 else "🔴"
        lines.append(
            f"{icon} <b>{sym}</b> | {qty:g} سهم | متوسط {avg:.2f}\n"
            f"   حالي {current:.2f} | P/L {pnl:+,.2f} ({pct:+.2f}%) | مخاطرة {risk}"
        )
    pnl = total_value - total_cost
    lines.append(
        f"\nإجمالي التكلفة <b>{total_cost:,.2f}</b>\n"
        f"القيمة المرجعية <b>{total_value:,.2f}</b>\n"
        f"النتيجة <b>{pnl:+,.2f}</b>"
    )
    send("\n".join(lines), chat_id, True)


def add_trade(state, text, chat_id):
    try:
        _, sym, qty, price = text.split()
        sym = normalize_symbol(sym)
        qty, price = float(qty), float(price)
        if not sym or qty <= 0 or price <= 0:
            raise ValueError
        p = state.setdefault("portfolio", {})
        old = p.get(sym, {"qty": 0, "avg": 0})
        new_qty = float(old["qty"]) + qty
        new_avg = (float(old["qty"]) * float(old["avg"]) + qty * price) / new_qty
        p[sym] = {"qty": new_qty, "avg": new_avg, "updated_at": now_cairo().isoformat()}
        send(f"✅ تم تسجيل الصفقة\n<b>{sym}</b> — الكمية {new_qty:g} — المتوسط {new_avg:.2f}", chat_id, True)
        return True
    except Exception:
        send("الصيغة: <code>/add_trade COMI 100 75.50</code>", chat_id, True)
        return False


def sell_trade(state, text, chat_id):
    try:
        _, sym, qty = text.split()
        sym = normalize_symbol(sym)
        qty = float(qty)
        p = state.setdefault("portfolio", {})
        if sym not in p or qty <= 0 or qty > float(p[sym]["qty"]):
            raise ValueError
        p[sym]["qty"] = float(p[sym]["qty"]) - qty
        if p[sym]["qty"] <= 0:
            del p[sym]
        send(f"✅ تم تخفيض مركز <b>{sym}</b> بمقدار {qty:g} سهم.", chat_id, True)
        return True
    except Exception:
        send("الصيغة: <code>/sell_trade COMI 50</code>", chat_id, True)
        return False


def active_signals_text(state):
    signals = state.get("signals", {})
    active = [(sym, s) for sym, s in signals.items() if s.get("status") not in ("CLOSED_T3", "STOPPED")]
    if not active:
        return "🚀 <b>الإشارات النشطة</b>\n\nلا توجد إشارات دخول نشطة حاليًا."
    lines = ["🚀 <b>الإشارات النشطة</b>", ""]
    for sym, s in active[-12:]:
        hit = int(s.get("highest_target", 0))
        lines.append(
            f"• <b>{sym}</b> دخول {s['entry']:.2f} | T{hit if hit else '-'} | "
            f"Stop {s['stop']:.2f} | Score {s.get('score', '-')}"
        )
    return "\n".join(lines)


def performance_text(state):
    hist = state.get("signal_history", [])
    signals = state.get("signals", {})
    closed = [x for x in hist if x.get("result") in ("T3", "STOP")]
    if not closed:
        lines = ["📈 <b>تقرير الأداء</b>", "", "لا توجد صفقات مغلقة كفاية لقياس الأداء بعد.", ""]
        for sym, s in list(signals.items())[-10:]:
            hit = s.get("highest_target", 0)
            lines.append(f"• {sym}: أعلى هدف T{hit} | {s.get('status', 'متابعة')}")
        return "\n".join(lines)
    wins = [x for x in closed if float(x.get("pnl_pct", 0)) > 0]
    avg = sum(float(x.get("pnl_pct", 0)) for x in closed) / len(closed)
    best = max(closed, key=lambda x: float(x.get("pnl_pct", 0)))
    worst = min(closed, key=lambda x: float(x.get("pnl_pct", 0)))
    return (
        "📈 <b>تقرير أداء الإشارات</b>\n\n"
        f"الإشارات المغلقة: <b>{len(closed)}</b>\n"
        f"نسبة النجاح: <b>{len(wins) / len(closed) * 100:.1f}%</b>\n"
        f"متوسط النتيجة: <b>{avg:+.2f}%</b>\n"
        f"أفضل نتيجة: <b>{best.get('symbol')} {float(best.get('pnl_pct', 0)):+.2f}%</b>\n"
        f"أضعف نتيجة: <b>{worst.get('symbol')} {float(worst.get('pnl_pct', 0)):+.2f}%</b>"
    )


def smart_assistant(chat_id, text):
    t = (text or "").strip()
    sym = normalize_symbol(t)
    if sym:
        try:
            a = technical(sym)
            send("🤖 <b>المساعد الذكي — قراءة فنية</b>\n\n" + analysis_text(a, advanced=True), chat_id, True)
        except Exception:
            send(f"⚠️ تعذر تحليل <b>{sym}</b>.", chat_id, True)
        return
    send(
        "🤖 <b>المساعد الذكي</b>\n\n"
        "اكتب رمز سهم مثل <b>COMI</b> للحصول على قراءة متقدمة.\n"
        "أو استخدم أزرار: فرص اليوم / فرص بكرة / أداء القطاعات / تقرير الأداء.",
        chat_id,
        True,
    )


def handle_message(chat_id, text, state, alarms_data):
    text = (text or "").strip()
    if text in ("/start", "/menu", "🏠 القائمة الرئيسية"):
        state.pop("awaiting", None)
        send(
            "📈 <b>EGX Smart Scanner PRO</b>\n\n"
            "ماسح فني + WATCH/ENTRY + نماذج + Golden Zone + متابعة أهداف + محفظة + تقارير.\n"
            + market_status(),
            chat_id,
            True,
        )
        return True
    if text.startswith("/add_trade "):
        return add_trade(state, text, chat_id)
    if text.startswith("/sell_trade "):
        return sell_trade(state, text, chat_id)
    if text.startswith("/alert "):
        return add_alarm_command(alarms_data, text, chat_id)
    if text.startswith("/remove_alert "):
        return remove_alarm_command(alarms_data, text, chat_id)
    if text == "📊 الشاشة اللحظية":
        send_market_watch(chat_id); return False
    if text == "🎯 فرص اليوم":
        send_opportunities(chat_id); return False
    if text == "🟡 Golden Zone":
        send_golden_zones(chat_id); return False
    if text == "🔮 فرص بكرة":
        tomorrow_opportunities(chat_id); return False
    if text == "🗺️ أداء القطاعات":
        sector_performance(chat_id); return False
    if text == "🚨 تنبيهاتي":
        show_alarms(chat_id, alarms_data); return False
    if text == "💼 محفظتي":
        show_portfolio(chat_id, state); return True
    if text == "🚀 الإشارات النشطة":
        send(active_signals_text(state), chat_id, True); return False
    if text == "📈 تقرير الأداء":
        send(performance_text(state), chat_id, True); return False
    if text == "🔍 تحليل سهم":
        state["awaiting"] = "analysis"
        send("🔍 اكتب رمز السهم، مثال: <b>COMI</b> أو <b>ABUK</b>", chat_id)
        return True
    if text == "🧠 التحليل المتقدم":
        state["awaiting"] = "advanced"
        send("🧠 اكتب رمز السهم للتحليل المتقدم.", chat_id)
        return True
    if text == "🤖 المساعد الذكي":
        state["awaiting"] = "assistant"
        send("🤖 اكتب رمز السهم أو سؤالك المختصر.", chat_id)
        return True
    if text == "⚙️ الإعدادات":
        send(
            "⚙️ <b>الإعدادات</b>\n\n"
            "⏱️ الفحص السحابي: كل 5 دقائق تقريبًا\n"
            "🔔 تنبيهات السعر: مفعلة\n"
            "🟡 WATCH / 🟢 ENTRY: مفعلة أثناء الجلسة\n"
            "🧩 Pattern Alerts + Golden Zone: مفعلة\n"
            "🎯 T1/T2/T3 + Dynamic Stop: مفعلة\n"
            "📋 تقرير إغلاق يومي: مفعّل\n\n"
            "⚠️ مصدر السعر الحالي تجريبي/قد يكون متأخرًا.",
            chat_id,
            True,
        )
        return False

    awaiting = state.get("awaiting")
    if awaiting in ("analysis", "advanced"):
        state.pop("awaiting", None)
        sym = normalize_symbol(text)
        if not sym:
            send("⚠️ رمز غير صحيح.", chat_id, True); return True
        try:
            send(analysis_text(technical(sym), advanced=(awaiting == "advanced")), chat_id, True)
        except Exception:
            send(f"⚠️ تعذر تحليل <b>{sym}</b> من مصدر البيانات الحالي.", chat_id, True)
        return True
    if awaiting == "assistant":
        state.pop("awaiting", None)
        smart_assistant(chat_id, text)
        return True

    send("استخدم القائمة الرئيسية 👇", chat_id, True)
    return False


def process_updates(state, alarms_data):
    offset = int(state.get("telegram_update_offset", 0))
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=20)
    r.raise_for_status()
    changed = False
    for u in r.json().get("result", []):
        state["telegram_update_offset"] = max(
            int(state.get("telegram_update_offset", 0)), int(u.get("update_id", 0)) + 1
        )
        changed = True
        m = u.get("message") or {}
        cid = str((m.get("chat") or {}).get("id", ""))
        text = m.get("text")
        if cid == str(CHAT_ID) and text:
            changed = handle_message(cid, text, state, alarms_data) or changed
    return changed


def monitor_price_alarms(state, alarms_data):
    changed = False
    for alarm in alarms_data.get("alarms", []):
        if not alarm.get("active", True):
            continue
        aid, sym = alarm["id"], alarm["symbol"]
        try:
            data = get_quote(sym)
            price = float(data["price"])
        except Exception:
            continue
        ast = state.setdefault("alarms", {}).get(aid, {"notifications_sent": 0, "condition_was_true": False})
        met = price >= float(alarm["price"]) if alarm["condition"] == ">=" else price <= float(alarm["price"])
        maxn = int(alarm.get("max_notifications", 1))
        can = maxn == 0 or ast["notifications_sent"] < maxn
        if met and can:
            send(
                f"🚨 <b>EGX PRICE ALARM</b>\n\n<b>{sym}</b>\n"
                f"السعر: <b>{price:.2f}</b>\nالشرط: {alarm['condition']} {float(alarm['price']):.2f}\n\n✅ تحقق الشرط"
            )
            ast["notifications_sent"] += 1
            ast["condition_was_true"] = True
            changed = True
        elif not met and ast.get("condition_was_true"):
            ast = {"notifications_sent": 0, "condition_was_true": False}
            changed = True
        state["alarms"][aid] = ast
    return changed


def record_signal_history(state, symbol, result, pnl_pct, signal):
    hist = state.setdefault("signal_history", [])
    hist.append({
        "symbol": symbol,
        "result": result,
        "pnl_pct": round(pnl_pct, 4),
        "entry": signal.get("entry"),
        "score": signal.get("score"),
        "opened_at": signal.get("created_at"),
        "closed_at": now_cairo().isoformat(),
    })
    if len(hist) > 300:
        del hist[:-300]


def auto_scanner(state):
    now = now_cairo()
    if not in_session(now):
        return False
    changed = False
    seen = state.setdefault("scanner_seen", {})
    signals = state.setdefault("signals", {})
    items = scan_market(14)
    for a in items:
        if a["score"] < 60:
            continue
        key = f"{a['symbol']}:{a['status']}:{now.date().isoformat()}"
        if key not in seen:
            seen[key] = now.isoformat(); changed = True
            if a["status"] == "ENTRY":
                send("🚀 <b>تفعيل نموذج/إشارة دخول فنية</b>\n\n" + analysis_text(a))
                current = signals.get(a["symbol"])
                if not current or current.get("status") in ("CLOSED_T3", "STOPPED"):
                    signals[a["symbol"]] = {
                        "entry": a["price"], "t1": a["t1"], "t2": a["t2"], "t3": a["t3"],
                        "stop": a["stop"], "initial_stop": a["stop"], "score": a["score"],
                        "status": "ENTRY", "highest_target": 0, "created_at": now.isoformat(),
                        "pattern": a["pattern"],
                    }
            else:
                send(
                    f"🟡 <b>WATCH — فرصة تحت المراقبة</b>\n\n<b>{a['symbol']}</b> | Score {a['score']}/100\n"
                    f"السعر {a['price']:.2f}\n{a['pattern']}\nRSI {a['rsi']:.1f} | Vol {a['volume_ratio']:.2f}x\n"
                    f"مستوى التفعيل التقريبي {a['resistance']:.2f}\n\n⚠️ بيانات المصدر الحالي قد تكون متأخرة."
                )

        if a["in_golden"]:
            gkey = f"golden:{a['symbol']}:{now.date().isoformat()}"
            if gkey not in seen:
                seen[gkey] = now.isoformat(); changed = True
                send(
                    f"🟡 <b>Golden Zone — ارتداد محتمل</b>\n\n<b>{a['symbol']}</b>\n"
                    f"السعر {a['price']:.2f}\nالمنطقة {a['golden_low']:.2f} — {a['golden_high']:.2f}\n"
                    f"RSI {a['rsi']:.1f} | Score {a['score']}/100\n"
                    f"مستوى التفعيل {a['resistance']:.2f}\n🛑 وقف مرجعي {a['stop']:.2f}"
                )

        if a["patterns"]:
            pkey = f"pattern:{a['symbol']}:{'+'.join(a['patterns'])}:{now.date().isoformat()}"
            if pkey not in seen and a["score"] >= 65:
                seen[pkey] = now.isoformat(); changed = True
                send(
                    f"📐 <b>تفعيل نموذج فني صاعد</b>\n\n<b>{a['symbol']}</b>\n"
                    f"النموذج: <b>{' + '.join(a['patterns'])}</b>\nالسعر {a['price']:.2f}\n"
                    f"Score {a['score']}/100 | Vol {a['volume_ratio']:.2f}x\n"
                    f"T1 {a['t1']:.2f} | T2 {a['t2']:.2f} | T3 {a['t3']:.2f}\n"
                    f"🛑 Stop {a['stop']:.2f}"
                )
    return changed


def track_signals(state):
    if not in_session():
        return False
    changed = False
    for sym, s in state.setdefault("signals", {}).items():
        if s.get("status") in ("CLOSED_T3", "STOPPED"):
            continue
        try:
            a = technical(sym)
            price = a["price"]
        except Exception:
            continue
        old = int(s.get("highest_target", 0))
        new = old
        if price >= s["t3"]:
            new = 3
        elif price >= s["t2"]:
            new = max(new, 2)
        elif price >= s["t1"]:
            new = max(new, 1)

        if new > old:
            s["highest_target"] = new
            profit = (price / s["entry"] - 1) * 100
            if new == 1:
                s["stop"] = max(s["stop"], s["entry"])
            elif new == 2:
                s["stop"] = max(s["stop"], s["t1"])
            elif new == 3:
                s["status"] = "CLOSED_T3"
                record_signal_history(state, sym, "T3", profit, s)
            changed = True
            send(
                f"🎯 <b>{sym} — تحقق T{new}</b>\n\n"
                f"دخول {s['entry']:.2f}\nالسعر المرجعي {price:.2f}\n"
                f"الربح التقريبي <b>{profit:+.2f}%</b>\n"
                f"🛡️ وقف الحماية الجديد {s['stop']:.2f}"
            )
        elif price <= s["stop"] and old < 3:
            s["status"] = "STOPPED"
            pnl = (price / s["entry"] - 1) * 100
            record_signal_history(state, sym, "STOP", pnl, s)
            changed = True
            send(
                f"🛑 <b>{sym} — تفعيل وقف المتابعة</b>\n"
                f"دخول {s['entry']:.2f} → سعر {price:.2f}\nالنتيجة التقريبية <b>{pnl:+.2f}%</b>"
            )
        elif old >= 1:
            suggested = max(s["stop"], a["ema20"] - a["atr"] * 0.5)
            if suggested > s["stop"] * 1.005 and suggested < price:
                prev = s["stop"]
                s["stop"] = suggested
                changed = True
                send(
                    f"🛡️ <b>{sym} — رفع وقف حماية الأرباح</b>\n\n"
                    f"الوقف السابق {prev:.2f}\nالوقف الجديد {suggested:.2f}\nالسعر المرجعي {price:.2f}"
                )
    return changed


def end_of_day_report(state):
    now = now_cairo()
    if not is_market_day(now) or now.hour * 60 + now.minute < 875:
        return False
    day = now.date().isoformat()
    if state.get("last_eod_report") == day:
        return False
    state["last_eod_report"] = day
    lines = ["📋 <b>تقرير نهاية الجلسة</b>", f"📅 {day}", ""]
    signals = state.get("signals", {})
    active = [(sym, s) for sym, s in signals.items() if s.get("status") not in ("CLOSED_T3", "STOPPED")]
    lines.append(f"الإشارات النشطة: <b>{len(active)}</b>")
    for sym, s in active[:8]:
        lines.append(f"• {sym}: أعلى هدف T{s.get('highest_target', 0)} | Stop {s.get('stop', 0):.2f}")
    try:
        candidates = [a for a in scan_market(12) if a["score"] >= 60][:5]
        lines.append("\n🔮 <b>مراقبة للجلسة القادمة</b>")
        for a in candidates:
            lines.append(f"• {a['symbol']} | Score {a['score']} | تفعيل {a['resistance']:.2f}")
    except Exception:
        pass
    lines.append("\n🔴 تم إنهاء إشارات اليوم حسب آخر بيانات متاحة.")
    send("\n".join(lines))
    return True


def cleanup_state(state):
    now = now_cairo()
    seen = state.setdefault("scanner_seen", {})
    keep = {}
    for k, v in seen.items():
        try:
            dt = datetime.fromisoformat(v)
            if (now.date() - dt.date()).days <= 7:
                keep[k] = v
        except Exception:
            keep[k] = v
    state["scanner_seen"] = keep


alarms_data = load_json(ALARMS_FILE, {"alarms": []})
state = load_json(STATE_FILE, {"alarms": {}})
state.setdefault("alarms", {})
changed = False

try:
    changed = process_updates(state, alarms_data) or changed
except Exception as e:
    print("Telegram updates:", e)
try:
    changed = monitor_price_alarms(state, alarms_data) or changed
except Exception as e:
    print("Price alarms:", e)
try:
    changed = auto_scanner(state) or changed
except Exception as e:
    print("Auto scanner:", e)
try:
    changed = track_signals(state) or changed
except Exception as e:
    print("Signal tracking:", e)
try:
    changed = end_of_day_report(state) or changed
except Exception as e:
    print("EOD report:", e)
cleanup_state(state)
if changed:
    save_json(STATE_FILE, state)
