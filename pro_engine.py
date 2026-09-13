import os
import json
import math
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from data_provider import provider

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "state.json"
HEALTH_FILE = "data_health.json"
CAIRO = ZoneInfo("Africa/Cairo")

UNIVERSE = [
    "COMI","SWDY","EAST","ABUK","FWRY","TMGH","ORAS","ORHD","ETEL","MFPC","SKPC","JUFO",
    "ISPH","PHDC","EFIH","CIRA","ALCN","AMOC","CCAP","AUTO","ADIB","FAIT","MASR","HELI",
    "DTPP","KABO","AIDC","EPCO","ARCC","ASCM","ETRS","TALM","POUL","NEDA","ZEOT","SNFC"
]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send(text):
    if not TOKEN or not CHAT_ID:
        return
    r = requests.post(
        f"{API}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    r.raise_for_status()


def hist(sym, rng="6mo"):
    rows = provider.history(sym, period=rng, interval="1d")
    if len(rows) < 60:
        raise RuntimeError("SHORT")
    return rows


def ema(values, n):
    if not values:
        return 0.0
    k = 2 / (n + 1)
    out = float(values[0])
    for x in values[1:]:
        out = float(x) * k + out * (1 - k)
    return out


def rsi(values, n=14):
    if len(values) < n + 1:
        return 50.0
    ds = [values[i] - values[i - 1] for i in range(len(values) - n, len(values))]
    gain = sum(max(x, 0) for x in ds) / n
    loss = sum(max(-x, 0) for x in ds) / n
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def atr(rows, n=14):
    tr = []
    for i in range(1, len(rows)):
        h = float(rows[i]["high"])
        l = float(rows[i]["low"])
        pc = float(rows[i - 1]["close"])
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(tr[-n:]) / max(1, min(n, len(tr)))


def adx(rows, n=14):
    if len(rows) < n + 2:
        return 0.0
    plus, minus, trs = [], [], []
    for i in range(1, len(rows)):
        up = float(rows[i]["high"]) - float(rows[i - 1]["high"])
        down = float(rows[i - 1]["low"]) - float(rows[i]["low"])
        plus.append(up if up > down and up > 0 else 0)
        minus.append(down if down > up and down > 0 else 0)
        h = float(rows[i]["high"])
        l = float(rows[i]["low"])
        pc = float(rows[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    trn = sum(trs[-n:])
    pdi = 100 * sum(plus[-n:]) / trn if trn else 0
    mdi = 100 * sum(minus[-n:]) / trn if trn else 0
    return 100 * abs(pdi - mdi) / (pdi + mdi) if pdi + mdi else 0


def mfi(rows, n=14):
    if len(rows) < n + 1:
        return 50.0
    pos = neg = 0.0
    prev = None
    for x in rows[-n - 1:]:
        tp = (float(x["high"]) + float(x["low"]) + float(x["close"])) / 3
        flow = tp * float(x.get("volume") or 0)
        if prev is not None:
            if tp >= prev:
                pos += flow
            else:
                neg += flow
        prev = tp
    return 100.0 if neg == 0 else 100 - 100 / (1 + pos / neg)


def candle_setup(rows):
    if len(rows) < 3:
        return []
    prev, cur = rows[-2], rows[-1]
    po, pc = float(prev["open"]), float(prev["close"])
    o, c = float(cur["open"]), float(cur["close"])
    h, l = float(cur["high"]), float(cur["low"])
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    lower = min(o, c) - l
    out = []
    if pc < po and c > o and o <= pc and c >= po:
        out.append("Bullish Engulfing")
    if body / rng <= 0.35 and lower >= body * 2:
        out.append("Hammer")
    if c > o and c >= float(prev["high"]) and body / rng >= 0.45:
        out.append("Breakout Candle")
    return out


def analyze(sym):
    rows = hist(sym)
    closes = [float(x["close"]) for x in rows]
    highs = [float(x["high"]) for x in rows]
    lows = [float(x["low"]) for x in rows]
    vols = [float(x.get("volume") or 0) for x in rows]

    close_price = closes[-1]
    quote = None
    if provider.has_live_quote:
        try:
            quote = provider.quote(sym)
        except Exception:
            quote = None
    price = float(quote["price"]) if quote else close_price

    e20 = ema(closes[-100:], 20)
    e50 = ema(closes[-120:], 50)
    e200 = ema(closes, min(200, len(closes)))
    rv = rsi(closes)
    av = atr(rows)
    ax = adx(rows)
    mf = mfi(rows)
    setups = candle_setup(rows)

    res20 = max(highs[-20:-1])
    sup20 = min(lows[-20:])
    res50 = max(highs[-50:-1])
    sup50 = min(lows[-50:])
    avgvol = sum(vols[-21:-1]) / max(1, len(vols[-21:-1]))
    vr = vols[-1] / avgvol if avgvol else 1.0
    mom5 = (close_price / closes[-6] - 1) * 100
    mom20 = (close_price / closes[-21] - 1) * 100
    volatility_pct = (av / close_price * 100) if close_price else 0

    score = 0
    why = []
    if close_price > e20:
        score += 10; why.append("فوق EMA20")
    if e20 > e50:
        score += 14; why.append("EMA20>EMA50")
    if e50 > e200:
        score += 8; why.append("اتجاه طويل داعم")
    if 48 <= rv <= 68:
        score += 12; why.append("RSI صحي")
    elif 40 <= rv < 48:
        score += 5
    if ax >= 22:
        score += 10; why.append("ADX يؤكد الاتجاه")
    if 45 <= mf <= 80:
        score += 8; why.append("تدفق سيولة إيجابي")
    if vr >= 1.4:
        score += 16; why.append("حجم قوي")
    elif vr >= 1.1:
        score += 7

    dist = (res20 - price) / price * 100 if price else 999
    if price >= res20 * 0.997:
        score += 14; why.append("اختراق مقاومة")
    elif 0 <= dist <= 2.5:
        score += 8; why.append("قريب من التفعيل")
    if mom5 > 0:
        score += 4
    if mom20 > 0:
        score += 4
    if setups:
        score += min(8, len(setups) * 4); why.append("نموذج سعري صاعد")
    if rv > 78:
        score -= 8

    score = max(0, min(100, score))
    risk = max(av * 1.2, price * 0.02)
    stop = max(sup20 * 0.995, price - risk)
    unit = max(price - stop, av, price * 0.012)
    t1, t2, t3 = price + unit, price + 2 * unit, price + 3 * unit

    golden_low = max(sup20, e20 - av * 0.6)
    golden_high = e20 + av * 0.25
    golden = golden_low <= price <= golden_high and e20 >= e50 * 0.99 and 35 <= rv <= 60
    breakout = price >= res20 * 0.997 and vr >= 1.1

    liquidity_score = min(100, max(0, vr * 35 + max(0, mf - 40) * 0.8 + max(0, ax - 15) * 0.6))
    confidence = "HIGH" if score >= 80 and ax >= 22 and vr >= 1.1 else "MEDIUM" if score >= 62 else "LOW"

    return {
        "symbol": sym,
        "price": price,
        "close_price": close_price,
        "score": score,
        "confidence": confidence,
        "rsi": rv,
        "adx": ax,
        "mfi": mf,
        "vr": vr,
        "liquidity_score": liquidity_score,
        "volatility_pct": volatility_pct,
        "mom5": mom5,
        "mom20": mom20,
        "res20": res20,
        "res50": res50,
        "sup20": sup20,
        "sup50": sup50,
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "golden": golden,
        "golden_low": golden_low,
        "golden_high": golden_high,
        "breakout": breakout,
        "setups": setups,
        "why": why[:6],
        "quote_live": bool(quote and quote.get("is_live")),
        "bid": quote.get("bid") if quote else None,
        "ask": quote.get("ask") if quote else None,
    }


def scan():
    out = []
    for sym in UNIVERSE:
        try:
            out.append(analyze(sym))
        except Exception:
            pass
    return sorted(out, key=lambda x: (x["score"], x["liquidity_score"], x["mom5"]), reverse=True)


def once_key(state, key):
    sent = state.setdefault("pro_engine_sent", {})
    if key in sent:
        return False
    sent[key] = datetime.now(CAIRO).isoformat()
    return True


def market_regime(items):
    if not items:
        return {"name": "UNKNOWN", "breadth": 0, "avg_mom": 0, "avg_score": 0}
    breadth = sum(1 for x in items if x["mom5"] > 0) / len(items) * 100
    avg_mom = sum(x["mom5"] for x in items) / len(items)
    avg_score = sum(x["score"] for x in items) / len(items)
    if breadth >= 65 and avg_mom > 0.5:
        name = "RISK-ON 🟢"
    elif breadth <= 35 and avg_mom < -0.5:
        name = "RISK-OFF 🔴"
    else:
        name = "MIXED 🟡"
    return {"name": name, "breadth": breadth, "avg_mom": avg_mom, "avg_score": avg_score}


def event_alerts(state, items):
    now = datetime.now(CAIRO)
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    if not (600 <= mins <= 870):
        return False

    # Never label delayed fallback data as live pattern activation.
    if not provider.has_live_quote:
        key = f"delayed_mode:{now.date().isoformat()}"
        if once_key(state, key):
            send(
                "🟡 <b>وضع التحليل غير اللحظي</b>\n\n"
                "المحرك الفني يعمل، لكن تفعيل اختراقات الجلسة اللحظية متوقف في Pro Engine لأن مصدر السعر الحالي غير مرخص كلحظي.\n"
                "ستستمر قوائم المراقبة وتقارير الإغلاق بدون ادعاء Live."
            )
            return True
        return False

    changed = False
    day = now.date().isoformat()
    for a in items[:20]:
        if a["breakout"] and a["score"] >= 72 and a["confidence"] in ("HIGH", "MEDIUM"):
            key = f"breakout:{a['symbol']}:{day}"
            if once_key(state, key):
                book = ""
                if a.get("bid") is not None or a.get("ask") is not None:
                    book = f"\nBid {a.get('bid', '-')} | Ask {a.get('ask', '-')}"
                send(
                    f"🚀 <b>تفعيل اختراق فني — LIVE FEED</b>\n\n"
                    f"<b>{a['symbol']}</b>\nالسعر {a['price']:.2f}\n"
                    f"Score <b>{a['score']}/100</b> | Confidence {a['confidence']}\n"
                    f"Volume {a['vr']:.2f}x | ADX {a['adx']:.1f} | MFI {a['mfi']:.1f}\n"
                    f"Liquidity Pulse {a['liquidity_score']:.0f}/100{book}\n"
                    f"T1 {a['t1']:.2f} | T2 {a['t2']:.2f} | T3 {a['t3']:.2f}\n"
                    f"🛑 Stop {a['stop']:.2f}\n\n🔎 {' • '.join(a['why'])}"
                )
                changed = True
        if a["golden"] and a["score"] >= 58:
            key = f"golden:{a['symbol']}:{day}"
            if once_key(state, key):
                send(
                    f"🟡 <b>Golden Zone — ارتداد محتمل</b>\n\n"
                    f"<b>{a['symbol']}</b>\nالسعر {a['price']:.2f}\n"
                    f"المنطقة {a['golden_low']:.2f} — {a['golden_high']:.2f}\n"
                    f"RSI {a['rsi']:.1f} | ADX {a['adx']:.1f} | MFI {a['mfi']:.1f}\n"
                    f"Score {a['score']}/100 | Confidence {a['confidence']}\n"
                    f"التفعيل التقريبي {a['res20']:.2f}"
                )
                changed = True
    return changed


def scheduled_reports(state, items):
    now = datetime.now(CAIRO)
    if now.weekday() >= 5 or not items:
        return False
    day = now.date().isoformat()
    mins = now.hour * 60 + now.minute
    changed = False
    regime = market_regime(items)

    if 570 <= mins < 600 and once_key(state, f"premarket:{day}"):
        top = items[:7]
        lines = [
            "🌅 <b>خريطة ما قبل الجلسة</b>",
            f"حالة السوق الفنية: <b>{regime['name']}</b>",
            f"Breadth {regime['breadth']:.0f}% | Avg Score {regime['avg_score']:.0f}",
            "",
        ]
        for i, a in enumerate(top, 1):
            lines.append(
                f"{i}) <b>{a['symbol']}</b> Score {a['score']} | {a['confidence']} | "
                f"Trigger {a['res20']:.2f} | Stop {a['stop']:.2f} | Liq {a['liquidity_score']:.0f}"
            )
        lines.append("\n⚠️ مرشحون للمراقبة وليست أوامر شراء.")
        send("\n".join(lines))
        changed = True

    if 865 <= mins <= 910 and once_key(state, f"close:{day}"):
        top = items[:8]
        lines = [
            "📋 <b>تقرير إغلاق الجلسة</b>",
            f"Regime: <b>{regime['name']}</b>",
            f"Breadth {regime['breadth']:.0f}% | زخم 5 جلسات {regime['avg_mom']:+.2f}% | Avg Score {regime['avg_score']:.0f}",
            "",
        ]
        for a in top:
            lines.append(
                f"• <b>{a['symbol']}</b> {a['close_price']:.2f} | Score {a['score']} | "
                f"Vol {a['vr']:.1f}x | RSI {a['rsi']:.0f} | Liq {a['liquidity_score']:.0f}"
            )
        lines.append("\n🔮 أعلى الدرجات محفوظة لقائمة مراقبة الجلسة القادمة.")
        send("\n".join(lines))
        changed = True

    return changed


def data_health_alert(state):
    health = load_json(HEALTH_FILE, {})
    if not health:
        return False
    today = datetime.now(CAIRO).date().isoformat()
    status = health.get("status", "UNKNOWN")
    if status not in ("RED", "UNKNOWN"):
        return False
    key = f"health_warning:{today}:{status}"
    if not once_key(state, key):
        return False
    send(
        "⚠️ <b>جودة البيانات تحتاج انتباه</b>\n\n"
        f"الحالة: <b>{status}</b>\n"
        f"المصدر: {health.get('quote_source', '-')}\n"
        f"آخر فحص: {health.get('checked_at', '-')}\n"
        f"التفاصيل: {health.get('message', '-')}\n\n"
        "تم الإبقاء على التحليلات كمرجعية، ومنع Pro Engine من ادعاء إشارات لحظية."
    )
    return True


def build_watchlist(items):
    out = []
    for a in items:
        if a["score"] >= 58 and (-1.0 <= (a["res20"] - a["price"]) / max(a["price"], 1e-9) * 100 <= 6.0):
            out.append({
                "symbol": a["symbol"],
                "score": a["score"],
                "confidence": a["confidence"],
                "trigger": round(a["res20"], 4),
                "stop": round(a["stop"], 4),
                "liquidity_score": round(a["liquidity_score"], 2),
            })
    return out[:12]


def main():
    state = load_json(STATE_FILE, {})
    items = scan()
    changed = False

    changed = data_health_alert(state) or changed
    changed = event_alerts(state, items) or changed
    changed = scheduled_reports(state, items) or changed

    regime = market_regime(items)
    state["pro_engine_snapshot"] = {
        "at": datetime.now(CAIRO).isoformat(),
        "count": len(items),
        "quote_mode": "LIVE" if provider.has_live_quote else "DELAYED_EVALUATION",
        "quote_source": provider.quote_source_name,
        "history_source": provider.history_source_name,
        "market_regime": regime,
        "watchlist_next_session": build_watchlist(items),
        "top": [
            {
                "symbol": x["symbol"],
                "score": x["score"],
                "confidence": x["confidence"],
                "price": x["price"],
                "liquidity_score": round(x["liquidity_score"], 2),
            }
            for x in items[:12]
        ],
    }
    changed = True

    if changed:
        save_state(state)


if __name__ == "__main__":
    main()
