import re

import bot_experience


def _keyboard(rows):
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "is_persistent": True,
    }


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _num(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _rr(entry, stop, target):
    try:
        entry = float(entry)
        stop = float(stop)
        target = float(target)
    except Exception:
        return 0.0
    risk = entry - stop
    if risk <= 0:
        return 0.0
    return max(0.0, target - entry) / risk


def _quote_label(snapshot):
    mode = str(snapshot.get("quote_mode") or "").upper()
    source = snapshot.get("quote_source") or "OHLCV / آخر Snapshot متاح"
    if mode == "LIVE":
        return f"🟢 LIVE مؤكد — {source}"
    return f"🟡 DELAYED / EVALUATION — {source}"


def _opportunity_type(item):
    if item.get("breakout"):
        return "اختراق فني"
    if item.get("golden"):
        return "Golden Zone"
    try:
        if float(item.get("mom5") or 0) > 0 and float(item.get("ema20") or 0) > float(item.get("ema50") or 0):
            return "ترند صاعد"
    except Exception:
        pass
    try:
        if float(item.get("price") or 0) <= float(item.get("ema20") or 0) * 1.015:
            return "ارتداد/مراقبة"
    except Exception:
        pass
    return "مراقبة فنية"


def _quality(score):
    try:
        score = float(score)
    except Exception:
        score = 0
    if score >= 80:
        return "A"
    if score >= 68:
        return "B+"
    if score >= 58:
        return "B"
    return "C"


def _plan_map(state):
    lifecycle = state.get("trade_lifecycle") or {}
    return {
        str(x.get("symbol") or "").upper(): x
        for x in _as_list(lifecycle.get("plans"))
        if x.get("symbol")
    }


def _candidate_rows(state, limit=6):
    snapshot = state.get("pro_engine_snapshot") or {}
    top = _as_list(snapshot.get("top"))
    plans = _plan_map(state)
    rows = []
    seen = set()
    for item in top:
        symbol = str(item.get("symbol") or "").strip().upper().replace(".CA", "")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        plan = plans.get(symbol) or {}
        trigger = plan.get("trigger", item.get("res20"))
        stop = plan.get("dynamic_stop") or plan.get("initial_stop") or item.get("stop")
        t1 = plan.get("target1", item.get("t1"))
        t2 = plan.get("target2", item.get("t2"))
        t3 = plan.get("target3", item.get("t3"))
        status = str(plan.get("lifecycle_status") or plan.get("status") or "WATCH")
        rows.append({
            "symbol": symbol,
            "status": status,
            "signal_id": plan.get("signal_id"),
            "score": item.get("score", plan.get("score")),
            "confidence": item.get("confidence") or "-",
            "price": item.get("price"),
            "trigger": trigger,
            "stop": stop,
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "liquidity": item.get("liquidity_score"),
            "volume_ratio": item.get("vr"),
            "type": _opportunity_type(item),
            "reasons": list(item.get("why") or [])[:4],
        })
        if len(rows) >= limit:
            break
    return rows


def _build_opportunities_text(state):
    snapshot = state.get("pro_engine_snapshot") or {}
    rows = _candidate_rows(state)
    lines = [
        "🎯 <b>ReFo EGX V2 — فرص اليوم</b>",
        f"📡 {_quote_label(snapshot)}",
        "",
    ]
    if not rows:
        lines.extend([
            "لا توجد فرص جاهزة في آخر Snapshot للمحرك.",
            "أعد التحديث بعد اكتمال دورة الفحص التالية.",
        ])
        return "\n".join(lines), rows

    for i, x in enumerate(rows, 1):
        entry_basis = x.get("trigger") or x.get("price") or 0
        rr1 = _rr(entry_basis, x.get("stop") or 0, x.get("t1") or 0)
        rr2 = _rr(entry_basis, x.get("stop") or 0, x.get("t2") or 0)
        rr3 = _rr(entry_basis, x.get("stop") or 0, x.get("t3") or 0)
        icon = {"WATCH": "🟡", "ENTRY": "🟢", "T1": "1️⃣", "T2": "2️⃣", "T3": "3️⃣"}.get(x["status"], "•")
        lines.extend([
            f"#{i} {icon} <b>{x['symbol']}</b> · {x['type']} · {x['status']}",
            f"   ⭐ Score {_num(x['score'], 0)}/100 · Quality {_quality(x['score'])} · Conf {x['confidence']}",
            f"   💵 Price {_num(x['price'])} · Trigger <b>{_num(x['trigger'])}</b> · Stop {_num(x['stop'])}",
            f"   🎯 T1 {_num(x['t1'])} · T2 {_num(x['t2'])} · T3 {_num(x['t3'])}",
            f"   ⚖️ RR {rr1:.2f}R / {rr2:.2f}R / {rr3:.2f}R · 💧 Liq {_num(x['liquidity'], 0)} · Vol {_num(x['volume_ratio'])}x",
        ])
        if x.get("signal_id"):
            lines.append(f"   🆔 <code>{x['signal_id']}</code>")
        if x["reasons"]:
            lines.append("   🔎 " + " · ".join(str(r) for r in x["reasons"]))
        lines.append("")

    lines.extend([
        "⚠️ الخطة لا تتفعل بمجرد وجود السهم في القائمة؛ Trigger هو شرط المراقبة، وWATCH لا يتحول إلى ENTRY من بيانات متأخرة.",
        "اختر متابعة أو تحليل الفرصة من الأزرار أسفل الرسالة.",
    ])
    return "\n".join(lines), rows


def _opportunities_menu(rows):
    menu_rows = []
    for i in range(0, len(rows), 2):
        follow = []
        for j in range(i, min(i + 2, len(rows))):
            follow.append(f"👁️ متابعة #{j + 1}")
        menu_rows.append(follow)
    for i in range(0, len(rows), 2):
        analyze = []
        for j in range(i, min(i + 2, len(rows))):
            analyze.append(f"🔍 تحليل #{j + 1}")
        menu_rows.append(analyze)
    menu_rows.extend([
        ["🔄 تحديث الفرص", "📋 قائمة المتابعة"],
        ["🚀 الإشارات النشطة", "🏠 القائمة الرئيسية"],
    ])
    return _keyboard(menu_rows)


def _index_from_action(text, prefix):
    m = re.fullmatch(re.escape(prefix) + r"\s*#(\d+)", text or "")
    if not m:
        return None
    return int(m.group(1)) - 1


def apply(base):
    """Upgrade Today's Opportunities to a ranked, actionable EGX V2 view."""
    original_handle = base.handle

    def show(chat_id, state):
        state.pop("awaiting", None)
        text, rows = _build_opportunities_text(state)
        state["opportunity_symbols"] = [x["symbol"] for x in rows]
        bot_experience._send_keyboard(base, text, chat_id, _opportunities_menu(rows))

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()

        if text in ("🎯 فرص اليوم", "🔄 تحديث الفرص"):
            show(chat_id, state)
            return True

        idx = _index_from_action(text, "👁️ متابعة")
        if idx is not None:
            symbols = state.get("opportunity_symbols") or []
            if idx < 0 or idx >= len(symbols):
                show(chat_id, state)
                return True
            symbol = base.normalize_symbol(symbols[idx])
            watch = []
            for raw in state.get("user_watchlist") or []:
                sym = base.normalize_symbol(str(raw))
                if sym and sym not in watch:
                    watch.append(sym)
            if symbol and symbol not in watch:
                watch.append(symbol)
            state["user_watchlist"] = watch
            state["last_analysis_symbol"] = symbol
            bot_experience._send_keyboard(
                base,
                f"👁️ تمت إضافة <b>{symbol}</b> إلى متابعة الخطة.\n"
                "سيظل WATCH ما لم تتحقق شروط دورة الإشارة من مصدر يسمح بالتفعيل الحقيقي.",
                chat_id,
                _opportunities_menu(_candidate_rows(state)),
            )
            return True

        idx = _index_from_action(text, "🔍 تحليل")
        if idx is not None:
            symbols = state.get("opportunity_symbols") or []
            if idx < 0 or idx >= len(symbols):
                show(chat_id, state)
                return True
            symbol = base.normalize_symbol(symbols[idx])
            state["last_analysis_symbol"] = symbol
            return original_handle(chat_id, "🔄 تحديث التحليل", state)

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    state = {
        "pro_engine_snapshot": {
            "quote_mode": "DELAYED_EVALUATION",
            "quote_source": "daily OHLCV",
            "top": [
                {
                    "symbol": "COMI",
                    "price": 77.0,
                    "score": 84,
                    "confidence": "HIGH",
                    "res20": 78.0,
                    "stop": 74.0,
                    "t1": 82.0,
                    "t2": 86.0,
                    "t3": 90.0,
                    "liquidity_score": 88,
                    "vr": 1.6,
                    "mom5": 2.1,
                    "ema20": 75.0,
                    "ema50": 72.0,
                    "why": ["فوق EMA20", "حجم قوي"],
                },
                {
                    "symbol": "SWDY",
                    "price": 61.0,
                    "score": 70,
                    "confidence": "MEDIUM",
                    "res20": 62.0,
                    "stop": 58.0,
                    "t1": 66.0,
                    "t2": 70.0,
                    "t3": 74.0,
                    "liquidity_score": 73,
                    "vr": 1.2,
                    "mom5": 1.0,
                    "ema20": 60.0,
                    "ema50": 59.0,
                    "why": ["EMA20>EMA50"],
                },
            ],
        },
        "trade_lifecycle": {
            "plans": {
                "COMI": {
                    "symbol": "COMI",
                    "signal_id": "COMI-a1",
                    "status": "WATCH",
                    "trigger": 78.0,
                    "dynamic_stop": 74.0,
                    "target1": 82.0,
                    "target2": 86.0,
                    "target3": 90.0,
                }
            }
        },
    }
    text, rows = _build_opportunities_text(state)
    assert len(rows) == 2
    assert "COMI-a1" in text
    assert "Trigger <b>78.00</b>" in text
    assert "RR 1.00R / 2.00R / 3.00R" in text
    assert "DELAYED / EVALUATION" in text
    assert "WATCH لا يتحول إلى ENTRY" in text
    menu = _opportunities_menu(rows)
    flat = [x for row in menu["keyboard"] for x in row]
    assert "👁️ متابعة #1" in flat
    assert "🔍 تحليل #2" in flat
    assert _index_from_action("👁️ متابعة #2", "👁️ متابعة") == 1
    print("bot opportunities self-test: PASS")


if __name__ == "__main__":
    self_test()
