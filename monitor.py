import os
import json
import math
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ALARMS_FILE = "alarms.json"
STATE_FILE = "state.json"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
CAIRO = ZoneInfo("Africa/Cairo")

# Core EGX universe for the automatic scanner. Expandable without changing the engine.
UNIVERSE = [
    "COMI", "SWDY", "EAST", "ABUK", "FWRY", "TMGH", "ORAS", "ORHD",
    "ETEL", "MFPC", "SKPC", "JUFO", "ISPH", "PHDC", "EFIH", "CIRA",
    "ALCN", "AMOC", "CCAP", "AUTO", "ADIB", "FAIT", "MASR", "HELI"
]

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


def send(message, chat_id=None, menu=False):
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


def get_quote(symbol):
    r = requests.get(f"https://demo.borsa.ashh.me/demo/quote/{symbol}", timeout=15)
    if r.status_code == 429:
        raise RuntimeError("DATA_LIMIT")
    r.raise_for_status()
    return r.json()


def get_history(symbol, period="6mo", interval="1d"):
    # Yahoo is used only as the current historical-candle source; EGX quotes may be delayed.
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.CA"
    r = requests.get(url, params={"range": period, "interval": interval}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()
    result = r.json().get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError("NO_HISTORY")
    q = result[0].get("indicators", {}).get("quote", [{}])[0]
    rows = []
    for i in range(len(q.get("close", []))):
        vals = {k: (q.get(k) or [None] * (i + 1))[i] for k in ("open", "high", "low", "close", "volume")}
        if all(vals[k] is not None for k in ("high", "low", "close")):
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


def rsi(values, n=14):
    if len(values) <= n:
        return 50.0
    gains, losses = [], []
    for a, b in zip(values[-n-1:-1], values[-n:]):
        d = b - a
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag, al = sum(gains) / n, sum(losses) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def atr(rows, n=14):
    tr = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i-1]["close"]
        tr.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(tr[-n:]) / min(n, len(tr)) if tr else 0.0


def technical(symbol):
    rows = get_history(symbol)
    closes = [float(x["close"]) for x in rows]
    highs = [float(x["high"]) for x in rows]
    lows = [float(x["low"]) for x in rows]
    vols = [float(x.get("volume") or 0) for x in rows]
    price = closes[-1]
    e20, e50 = ema(closes[-80:], 20), ema(closes[-100:], 50)
    r = rsi(closes)
    macd = ema(closes[-80:], 12) - ema(closes[-80:], 26)
    macd_prev = ema(closes[-81:-1], 12) - ema(closes[-81:-1], 26)
    a = atr(rows)
    support = min(lows[-20:])
    resistance = max(highs[-20:-1]) if len(highs) > 1 else highs[-1]
    avg_vol = sum(vols[-21:-1]) / max(1, len(vols[-21:-1]))
    vol_ratio = vols[-1] / avg_vol if avg_vol else 1.0
    momentum = (price / closes[-6] - 1) * 100 if len(closes) >= 6 else 0

    score = 0
    reasons = []
    if price > e20: score += 15; reasons.append("السعر أعلى EMA20")
    if e20 > e50: score += 20; reasons.append("الاتجاه المتوسط صاعد")
    if 50 <= r <= 70: score += 15; reasons.append("RSI إيجابي بدون تشبع قوي")
    elif 40 <= r < 50: score += 7
    if macd > 0: score += 15; reasons.append("MACD إيجابي")
    if macd > macd_prev: score += 10; reasons.append("زخم MACD يتحسن")
    if vol_ratio >= 1.3: score += 15; reasons.append("حجم تداول أعلى من المتوسط")
    if price >= resistance * 0.995: score += 10; reasons.append("قرب/اختراق مقاومة 20 جلسة")
    if momentum > 0: score += 5
    score = min(100, score)

    if score >= 75:
        status, icon = "ENTRY", "🟢"
    elif score >= 60:
        status, icon = "WATCH", "🟡"
    else:
        status, icon = "NEUTRAL", "⚪"

    risk = max(a * 1.25, price * 0.025)
    stop = max(support * 0.995, price - risk)
    unit = max(price - stop, a, price * 0.015)
    t1, t2, t3 = price + unit, price + unit * 2, price + unit * 3
    rr = (t2 - price) / max(price - stop, 0.0001)
    pattern = "اختراق مقاومة" if price >= resistance * 0.995 else "اتجاه صاعد" if price > e20 > e50 else "منطقة ارتداد" if price <= support * 1.04 else "تجميع/محايد"
    return {
        "symbol": symbol, "price": price, "score": score, "status": status, "icon": icon,
        "rsi": r, "macd": macd, "ema20": e20, "ema50": e50, "volume_ratio": vol_ratio,
        "support": support, "resistance": resistance, "atr": a, "momentum": momentum,
        "entry_low": price - a * .25, "entry_high": price + a * .25,
        "stop": stop, "t1": t1, "t2": t2, "t3": t3, "rr": rr,
        "pattern": pattern, "reasons": reasons[:4]
    }


def analysis_text(a):
    trend = "صاعد" if a["ema20"] > a["ema50"] else "هابط/ضعيف"
    macd_text = "إيجابي" if a["macd"] > 0 else "سلبي"
    return (
        f"{a['icon']} <b>{a['symbol']} — {a['status']}</b>\n"
        f"💰 السعر المرجعي: <b>{a['price']:.2f}</b>\n"
        f"🧠 قوة الإشارة: <b>{a['score']}/100</b>\n"
        f"📈 الاتجاه: <b>{trend}</b> | RSI: <b>{a['rsi']:.1f}</b> | MACD: <b>{macd_text}</b>\n"
        f"📦 قوة الحجم: <b>{a['volume_ratio']:.2f}x</b> | النموذج: <b>{a['pattern']}</b>\n"
        f"🧱 دعم: <b>{a['support']:.2f}</b> | مقاومة: <b>{a['resistance']:.2f}</b>\n\n"
        f"🎯 <b>خطة فنية آلية</b>\n"
        f"منطقة دخول: <b>{a['entry_low']:.2f} — {a['entry_high']:.2f}</b>\n"
        f"T1: <b>{a['t1']:.2f}</b> | T2: <b>{a['t2']:.2f}</b> | T3: <b>{a['t3']:.2f}</b>\n"
        f"🛑 Stop: <b>{a['stop']:.2f}</b> | R/R إلى T2: <b>{a['rr']:.2f}</b>\n\n"
        f"🔎 {' • '.join(a['reasons']) if a['reasons'] else 'لا يوجد توافق فني قوي حاليًا'}\n\n"
        f"⚠️ <i>البيانات الحالية قد تكون متأخرة؛ الخطة تحليل فني وليست أمر شراء أو بيع.</i>"
    )


def scan_market(limit=7):
    found = []
    for symbol in UNIVERSE:
        try:
            found.append(technical(symbol))
        except Exception:
            continue
    found.sort(key=lambda x: (x["score"], x["volume_ratio"]), reverse=True)
    return found[:limit]


def send_opportunities(chat_id):
    items = scan_market(7)
    if not items:
        send("⚠️ تعذر تكوين قائمة الفرص من مصدر البيانات الحالي.", chat_id, True); return
    lines = ["🎯 <b>أفضل فرص المسح الفني</b>", market_status(), ""]
    for i, a in enumerate(items, 1):
        lines.append(f"{i}) {a['icon']} <b>{a['symbol']}</b> — {a['score']}/100 — {a['status']}\n   {a['price']:.2f} | RSI {a['rsi']:.0f} | Vol {a['volume_ratio']:.1f}x | {a['pattern']}")
    lines.append("\n⚠️ <i>ترتيب فني آلي من بيانات قد تكون متأخرة.</i>")
    send("\n".join(lines), chat_id, True)


def send_market_watch(chat_id):
    items = scan_market(10)
    lines = ["📊 <b>Market Watch — EGX Smart Scanner</b>", market_status(), ""]
    for a in items:
        arrow = "▲" if a["momentum"] > 0 else "▼"
        lines.append(f"{a['icon']} <b>{a['symbol']}</b>  {a['price']:.2f}  {arrow}{abs(a['momentum']):.1f}%  Score {a['score']}")
    lines.append("\nℹ️ <i>هذه شاشة تحليل وليست شاشة أسعار تنفيذ لحظية حتى يتم ربط Live Feed مرخص.</i>")
    send("\n".join(lines), chat_id, True)


def show_alarms(chat_id, alarms_data):
    active = [x for x in alarms_data.get("alarms", []) if x.get("active", True)]
    if not active:
        send("🚨 <b>تنبيهاتي</b>\n\nلا توجد تنبيهات نشطة.", chat_id, True); return
    lines = ["🚨 <b>التنبيهات النشطة</b>", ""]
    for x in active:
        lines.append(f"• <b>{x.get('symbol')}</b>  {x.get('condition')}  {float(x.get('price',0)):.2f}  | مرات: {x.get('max_notifications',1)}")
    lines.append("\nلإضافة تنبيه: <code>/alert COMI >= 80</code>")
    send("\n".join(lines), chat_id, True)


def show_portfolio(chat_id, state):
    p = state.setdefault("portfolio", {})
    if not p:
        send("💼 <b>محفظتي</b>\n\nلا توجد مراكز مسجلة.\nأضف صفقة: <code>/add_trade COMI 100 75.50</code>", chat_id, True); return
    lines = ["💼 <b>محفظتي</b>", ""]
    total_cost = total_value = 0.0
    for sym, pos in p.items():
        qty, avg = float(pos["qty"]), float(pos["avg"])
        try: current = technical(sym)["price"]
        except Exception: current = avg
        cost, value = qty*avg, qty*current
        pnl = value-cost; pct = pnl/cost*100 if cost else 0
        total_cost += cost; total_value += value
        icon = "🟢" if pnl >= 0 else "🔴"
        lines.append(f"{icon} <b>{sym}</b> | {qty:g} سهم | متوسط {avg:.2f}\n   حالي {current:.2f} | P/L {pnl:+,.2f} ({pct:+.2f}%)")
    pnl = total_value-total_cost
    lines.append(f"\nإجمالي التكلفة: <b>{total_cost:,.2f}</b>\nالقيمة المرجعية: <b>{total_value:,.2f}</b>\nالنتيجة: <b>{pnl:+,.2f}</b>")
    send("\n".join(lines), chat_id, True)


def results_text(state):
    signals = state.get("signals", {})
    if not signals:
        return "📈 <b>نتائج الإشارات</b>\n\nلم تُسجل إشارات آلية بعد."
    lines = ["📈 <b>متابعة الإشارات</b>", ""]
    for sym, s in list(signals.items())[-12:]:
        hit = s.get("highest_target", 0)
        status = "T3 ✅" if hit >= 3 else "T2 ✅" if hit >= 2 else "T1 ✅" if hit >= 1 else s.get("status", "متابعة")
        lines.append(f"• <b>{sym}</b> دخول {s['entry']:.2f} | {status} | Score {s.get('score','-')}")
    return "\n".join(lines)


def add_trade(state, text, chat_id):
    try:
        _, sym, qty, price = text.split()
        sym = normalize_symbol(sym); qty=float(qty); price=float(price)
        if not sym or qty <= 0 or price <= 0: raise ValueError
        p = state.setdefault("portfolio", {})
        old = p.get(sym, {"qty":0,"avg":0})
        new_qty = float(old["qty"]) + qty
        new_avg = (float(old["qty"])*float(old["avg"]) + qty*price) / new_qty
        p[sym] = {"qty":new_qty,"avg":new_avg}
        send(f"✅ تم تسجيل الصفقة\n<b>{sym}</b> — الكمية {new_qty:g} — متوسط التكلفة {new_avg:.2f}", chat_id, True)
        return True
    except Exception:
        send("الصيغة: <code>/add_trade COMI 100 75.50</code>", chat_id, True); return False


def add_alarm_command(alarms_data, text, chat_id):
    try:
        parts=text.split(); sym=normalize_symbol(parts[1]); cond=parts[2]; price=float(parts[3])
        if not sym or cond not in (">=","<=") or price<=0: raise ValueError
        import uuid
        alarms_data.setdefault("alarms", []).append({"id":str(uuid.uuid4()),"symbol":sym,"condition":cond,"price":price,"max_notifications":1,"active":True,"mode":"telegram","created_at":datetime.now(CAIRO).isoformat()})
        save_json(ALARMS_FILE, alarms_data)
        send(f"✅ تنبيه جديد: <b>{sym} {cond} {price:.2f}</b>", chat_id, True)
        return True
    except Exception:
        send("الصيغة: <code>/alert COMI >= 80</code>", chat_id, True); return False


def handle_message(chat_id, text, state, alarms_data):
    text=(text or "").strip()
    if text in ("/start","/menu","🏠 القائمة الرئيسية"):
        state.pop("awaiting", None)
        send("📈 <b>EGX Smart Scanner PRO</b>\n\nماسح فني + فرص + متابعة إشارات + تنبيهات + محفظة.\n"+market_status(), chat_id, True); return True
    if text.startswith("/add_trade "): return add_trade(state,text,chat_id)
    if text.startswith("/alert "): return add_alarm_command(alarms_data,text,chat_id)
    if text == "📊 الشاشة اللحظية": send_market_watch(chat_id); return False
    if text == "🎯 فرص اليوم": send_opportunities(chat_id); return False
    if text == "🚨 تنبيهاتي": show_alarms(chat_id,alarms_data); return False
    if text == "💼 محفظتي": show_portfolio(chat_id,state); return True
    if text == "📈 نتائج الإشارات": send(results_text(state),chat_id,True); return False
    if text in ("🔍 تحليل سهم","🤖 المساعد الذكي"):
        state["awaiting"] = "analysis"
        send("🔍 اكتب رمز السهم، مثال: <b>COMI</b> أو <b>ABUK</b>",chat_id); return True
    if text == "⚙️ الإعدادات":
        send("⚙️ <b>الإعدادات</b>\n\n⏱️ الفحص السحابي: كل 5 دقائق تقريبًا\n🔔 تنبيهات السعر: مفعلة\n🎯 ماسح WATCH/ENTRY: مفعل أثناء الجلسة\n📊 تتبع T1/T2/T3 ووقف الخسارة: مفعل\n\n⚠️ مصدر الأسعار الحالي تجريبي/قد يكون متأخرًا.",chat_id,True); return False
    if state.get("awaiting") == "analysis":
        state.pop("awaiting",None); sym=normalize_symbol(text)
        if not sym: send("⚠️ رمز غير صحيح.",chat_id,True); return True
        try: send(analysis_text(technical(sym)),chat_id,True)
        except Exception: send(f"⚠️ تعذر تحليل <b>{sym}</b> من مصدر البيانات الحالي.",chat_id,True)
        return True
    send("استخدم القائمة الرئيسية 👇",chat_id,True); return False


def process_updates(state, alarms_data):
    offset=int(state.get("telegram_update_offset",0)); params={"timeout":0,"allowed_updates":json.dumps(["message"])}
    if offset: params["offset"]=offset
    r=requests.get(f"{TELEGRAM_API}/getUpdates",params=params,timeout=20); r.raise_for_status()
    changed=False
    for u in r.json().get("result",[]):
        state["telegram_update_offset"]=max(int(state.get("telegram_update_offset",0)),int(u.get("update_id",0))+1); changed=True
        m=u.get("message") or {}; cid=str((m.get("chat") or {}).get("id","")); text=m.get("text")
        if cid == str(CHAT_ID) and text:
            changed = handle_message(cid,text,state,alarms_data) or changed
    return changed


def monitor_price_alarms(state, alarms_data):
    changed=False
    for alarm in alarms_data.get("alarms",[]):
        if not alarm.get("active",True): continue
        aid=alarm["id"]; sym=alarm["symbol"]
        try: data=get_quote(sym); price=float(data["price"])
        except Exception: continue
        ast=state.setdefault("alarms",{}).get(aid,{"notifications_sent":0,"condition_was_true":False})
        met=price>=float(alarm["price"]) if alarm["condition"]==">=" else price<=float(alarm["price"])
        maxn=int(alarm.get("max_notifications",1)); can=maxn==0 or ast["notifications_sent"]<maxn
        if met and can:
            send(f"🚨 <b>EGX PRICE ALARM</b>\n\n<b>{sym}</b>\nالسعر: <b>{price:.2f}</b>\nالشرط: {alarm['condition']} {float(alarm['price']):.2f}\n\n✅ تحقق الشرط")
            ast["notifications_sent"]+=1; ast["condition_was_true"]=True; changed=True
        elif not met and ast.get("condition_was_true"):
            ast={"notifications_sent":0,"condition_was_true":False}; changed=True
        state["alarms"][aid]=ast
    return changed


def auto_scanner(state):
    # New WATCH/ENTRY alerts are emitted only during the EGX session and are de-duplicated.
    now=datetime.now(CAIRO); mins=now.hour*60+now.minute
    if now.weekday()>=5 or not (600<=mins<=870): return False
    changed=False; seen=state.setdefault("scanner_seen",{}); signals=state.setdefault("signals",{})
    for a in scan_market(8):
        if a["score"] < 60: continue
        key=f"{a['symbol']}:{a['status']}:{now.date().isoformat()}"
        if key in seen: continue
        seen[key]=now.isoformat(); changed=True
        if a["status"]=="ENTRY":
            send("🚀 <b>تفعيل إشارة دخول فنية</b>\n\n"+analysis_text(a))
            signals[a["symbol"]]={"entry":a["price"],"t1":a["t1"],"t2":a["t2"],"t3":a["t3"],"stop":a["stop"],"score":a["score"],"status":"ENTRY","highest_target":0,"created_at":now.isoformat()}
        else:
            send(f"🟡 <b>WATCH — فرصة تحت المراقبة</b>\n\n<b>{a['symbol']}</b> | Score {a['score']}/100\nالسعر {a['price']:.2f}\n{a['pattern']}\nRSI {a['rsi']:.1f} | Vol {a['volume_ratio']:.2f}x\nمستوى التفعيل التقريبي: {a['resistance']:.2f}\n\n⚠️ بيانات المصدر الحالي قد تكون متأخرة.")
    return changed


def track_signals(state):
    changed=False
    for sym,s in state.setdefault("signals",{}).items():
        if s.get("status") in ("CLOSED_T3","STOPPED"): continue
        try: price=technical(sym)["price"]
        except Exception: continue
        old=int(s.get("highest_target",0)); new=old
        if price>=s["t3"]: new=3
        elif price>=s["t2"]: new=max(new,2)
        elif price>=s["t1"]: new=max(new,1)
        if new>old:
            s["highest_target"]=new; changed=True
            profit=(price/s["entry"]-1)*100
            if new==3: s["status"]="CLOSED_T3"
            elif new>=1:
                # Protect profit: after T1, move suggested stop to at least entry.
                s["stop"]=max(s["stop"],s["entry"])
            send(f"🎯 <b>{sym} — تحقق T{new}</b>\n\nدخول: {s['entry']:.2f}\nالسعر المرجعي: {price:.2f}\nالربح التقريبي: <b>{profit:+.2f}%</b>\n🛡️ وقف الحماية المقترح: {s['stop']:.2f}" )
        elif price<=s["stop"] and old<3:
            s["status"]="STOPPED"; changed=True
            pnl=(price/s["entry"]-1)*100
            send(f"🛑 <b>{sym} — تفعيل وقف المتابعة</b>\nدخول {s['entry']:.2f} → سعر {price:.2f}\nالنتيجة التقريبية {pnl:+.2f}%")
    return changed


alarms_data=load_json(ALARMS_FILE,{"alarms":[]})
state=load_json(STATE_FILE,{"alarms":{}})
state.setdefault("alarms",{})
changed=False
try: changed=process_updates(state,alarms_data) or changed
except Exception as e: print("Telegram updates:",e)
try: changed=monitor_price_alarms(state,alarms_data) or changed
except Exception as e: print("Price alarms:",e)
try: changed=auto_scanner(state) or changed
except Exception as e: print("Auto scanner:",e)
try: changed=track_signals(state) or changed
except Exception as e: print("Signal tracking:",e)
if changed: save_json(STATE_FILE,state)
