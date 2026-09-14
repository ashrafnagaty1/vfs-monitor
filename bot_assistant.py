import re


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


ASSISTANT_MENU = _keyboard([
    ["📌 حلّل آخر سهم", "🎯 أفضل الفرص"],
    ["🗺️ ملخص السوق", "💼 ملخص محفظتي"],
    ["✍️ سؤال جديد", "🏠 القائمة الرئيسية"],
])


def _send(base, chat_id, text, keyboard=ASSISTANT_MENU):
    if not base.TOKEN:
        return
    payload = {
        "chat_id": str(chat_id or base.CHAT_ID),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": base.json.dumps(keyboard, ensure_ascii=False),
    }
    r = base.requests.post(f"{base.API}/sendMessage", data=payload, timeout=15)
    r.raise_for_status()


def _runtime(base):
    try:
        return base.load_json(base.STATE_FILE, {}) or {}
    except Exception:
        return {}


def _num(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _source(runtime):
    snap = runtime.get("pro_engine_snapshot") or {}
    lifecycle = runtime.get("trade_lifecycle") or {}
    mode = lifecycle.get("quote_mode") or snap.get("quote_mode") or "DELAYED_EVALUATION"
    if mode == "LIVE":
        return "🟢 LIVE مؤكد من مزود السعر"
    src = snap.get("quote_source") or "OHLCV / آخر إغلاق متاح"
    return f"🟡 DELAYED / EVALUATION — {src}"


def _tokens(text):
    return re.findall(r"\b[A-Za-z][A-Za-z0-9-]{1,11}\b", text or "")


def _candidate_symbol(base, text, state):
    ignored = {"EGX", "RSI", "ADX", "MFI", "EMA", "MACD", "OBV", "RR", "AI"}
    for token in _tokens(text):
        sym = base.normalize_symbol(token)
        if sym and sym not in ignored:
            return sym
    return state.get("assistant_last_symbol") or state.get("last_analysis_symbol") or ""


def _market_answer(runtime):
    snap = runtime.get("pro_engine_snapshot") or {}
    regime = snap.get("market_regime") or {}
    top = snap.get("top") or []
    lines = [
        "🤖 <b>ReFo Assistant — قراءة السوق</b>",
        f"🧭 الحالة: <b>{regime.get('name', '-')}</b>",
        f"📊 Breadth للعينة: <b>{_num(regime.get('breadth'), 1)}%</b>",
        f"⭐ متوسط Score: <b>{_num(regime.get('avg_score'), 1)}</b>",
    ]
    if top:
        leaders = sorted(top, key=lambda x: float(x.get("score") or 0), reverse=True)[:3]
        lines.append("\n🎯 <b>أعلى المرشحين في آخر Snapshot</b>")
        for x in leaders:
            lines.append(f"• {x.get('symbol', '-')} · Score {_num(x.get('score'), 0)} · سعر {_num(x.get('price'))}")
    lines.extend([
        "",
        f"📡 {_source(runtime)}",
        "⚠️ الـBreadth والفرص هنا تخص العينة التي يملكها ReFo، وليست بالضرورة السوق المصري كاملًا.",
    ])
    return "\n".join(lines)


def _opportunities_answer(runtime):
    snap = runtime.get("pro_engine_snapshot") or {}
    items = list(snap.get("top") or [])
    if not items:
        return "🤖 لا توجد فرص محفوظة في آخر Snapshot حاليًا."
    items.sort(key=lambda x: (float(x.get("score") or 0), float(x.get("liquidity_score") or 0)), reverse=True)
    lines = ["🤖 <b>ReFo Assistant — أفضل الفرص الحالية</b>", ""]
    for i, x in enumerate(items[:5], 1):
        lines.append(
            f"{i}) <b>{x.get('symbol','-')}</b> · Score {_num(x.get('score'),0)} · "
            f"Liq {_num(x.get('liquidity_score'),0)} · سعر {_num(x.get('price'))}"
        )
    lines.extend([
        "",
        f"📡 {_source(runtime)}",
        "⚠️ الترتيب للمراقبة فقط؛ لا يحوّل WATCH إلى ENTRY من بيانات متأخرة.",
    ])
    return "\n".join(lines)


def _portfolio_answer(runtime):
    personal = runtime.get("personal_portfolio") or {}
    positions = personal.get("positions") or {}
    if isinstance(positions, list):
        positions = {str(i): p for i, p in enumerate(positions)}
    signal = runtime.get("signal_portfolio") or {}
    open_positions = signal.get("open_positions") or {}
    if isinstance(open_positions, list):
        signal_count = len(open_positions)
    elif isinstance(open_positions, dict):
        signal_count = len(open_positions)
    else:
        signal_count = 0
    lines = [
        "🤖 <b>ReFo Assistant — ملخص المحفظة</b>",
        f"👤 المراكز الشخصية: <b>{len(positions)}</b>",
        f"🚀 مراكز إشارات ReFo المفتوحة: <b>{signal_count}</b>",
    ]
    if positions:
        lines.append("\n📌 <b>المراكز الشخصية</b>")
        for p in list(positions.values())[:6]:
            lines.append(
                f"• {p.get('symbol','-')} · Qty {_num(p.get('qty'),0)} · Avg {_num(p.get('avg') or p.get('avg_cost'))}"
            )
    lines.extend([
        "",
        f"📡 {_source(runtime)}",
        "ℹ️ المحفظة الشخصية منفصلة عن محفظة إشارات ReFo، ولا يتم إنشاء مركز من WATCH متأخر.",
    ])
    return "\n".join(lines)


def _stock_answer(base, runtime, state, symbol):
    try:
        from pro_engine import analyze
        a = analyze(symbol)
    except Exception:
        return f"🤖 تعذر بناء قراءة موثوقة لـ <b>{symbol}</b> حاليًا."

    state["assistant_last_symbol"] = symbol
    price = float(a.get("price") or 0)
    trigger = float(a.get("res20") or 0)
    stop = float(a.get("stop") or 0)
    t1 = float(a.get("t1") or 0)
    risk = max(0.0, price - stop)
    rr1 = max(0.0, t1 - price) / risk if risk else 0.0
    live = bool(a.get("quote_live"))
    status = "ENTRY" if live and trigger and price >= trigger * 0.997 else "WATCH"
    score = float(a.get("score") or 0)
    rsi = float(a.get("rsi") or 0)
    adx = float(a.get("adx") or 0)
    vr = float(a.get("vr") or 0)

    positives = []
    risks = []
    if score >= 70:
        positives.append(f"Score قوي نسبيًا ({score:.0f}/100)")
    elif score < 50:
        risks.append(f"Score منخفض نسبيًا ({score:.0f}/100)")
    if adx >= 25:
        positives.append(f"ADX {adx:.1f} يشير لترند أوضح")
    else:
        risks.append(f"ADX {adx:.1f} لا يعطي ترندًا قويًا")
    if 45 <= rsi <= 68:
        positives.append(f"RSI {rsi:.1f} في نطاق متوازن")
    elif rsi >= 72:
        risks.append(f"RSI {rsi:.1f} مرتفع ويحتاج حذرًا")
    if vr >= 1.2:
        positives.append(f"الحجم {vr:.2f}x أعلى من المعتاد")
    elif vr < 0.8:
        risks.append(f"الحجم {vr:.2f}x ضعيف نسبيًا")

    decision = "مراقبة الشرط وعدم الاستباق" if status == "WATCH" else "الإشارة حققت شرط التفعيل من مصدر Live مؤكد"
    lines = [
        f"🤖 <b>ReFo Assistant — {symbol}</b>",
        f"📌 القرار المحتمل: <b>{status}</b> — {decision}",
        f"💵 السعر المرجعي {_num(price)} · Trigger {_num(trigger)}",
        f"🛑 Stop {_num(stop)} · T1 {_num(t1)} · RR1 <b>{rr1:.2f}R</b>",
        f"⭐ Score {_num(score,0)}/100 · RSI {_num(rsi,1)} · ADX {_num(adx,1)} · Volume {_num(vr,2)}x",
    ]
    if positives:
        lines.append("\n✅ <b>عوامل داعمة</b>")
        lines.extend([f"• {x}" for x in positives[:4]])
    if risks:
        lines.append("\n⚠️ <b>المخاطر/ما يحتاج تأكيدًا</b>")
        lines.extend([f"• {x}" for x in risks[:4]])
    why = a.get("why") or []
    if why:
        lines.append("\n🔎 <b>من محرك ReFo</b>")
        lines.extend([f"• {x}" for x in why[:3]])
    lines.extend([
        "",
        f"📡 {_source(runtime)}",
        "ℹ️ هذه قراءة آلية من بيانات ReFo الحالية، وليست ادعاء بوجود نموذج لغوي خارجي أو ضمان ربح.",
    ])
    return "\n".join(lines)


def _answer(base, chat_id, text, state):
    runtime = _runtime(base)
    q = (text or "").strip()
    ql = q.lower()
    symbol = _candidate_symbol(base, q, state)

    if any(k in ql for k in ("السوق", "market", "egx30", "egx 30", "الاتجاه العام")):
        result = _market_answer(runtime)
    elif any(k in ql for k in ("محفظ", "portfolio", "مراكزي", "مركزي")):
        result = _portfolio_answer(runtime)
    elif any(k in ql for k in ("فرص", "أفضل", "opportun", "مرشح")) and not symbol:
        result = _opportunities_answer(runtime)
    elif symbol:
        result = _stock_answer(base, runtime, state, symbol)
    else:
        result = (
            "🤖 <b>ReFo Assistant</b>\n\n"
            "أقدر أجاوبك من بيانات ReFo الحالية عن سهم، السوق، الفرص أو المحفظة.\n"
            "مثال: <code>إيه وضع COMI؟</code> أو <code>إيه أفضل الفرص؟</code> أو <code>ملخص السوق</code>.\n\n"
            "⚠️ لن أختلق Fundamentals أو Bid/Ask أو Market Depth أو Live غير مثبت."
        )
    _send(base, chat_id, result)


def apply(base):
    original_handle = base.handle

    def assistant_handle(chat_id, text, state):
        text = (text or "").strip()

        if text == "🤖 المساعد الذكي":
            state["awaiting"] = "assistant_question"
            _send(
                base,
                chat_id,
                "🤖 <b>ReFo Assistant</b>\n\n"
                "اسأل بالعربي عن سهم أو السوق أو الفرص أو محفظتك. الإجابة ستكون Grounded فقط على بيانات ReFo المتاحة.\n"
                "مثال: <code>هل COMI مناسب للمراقبة؟</code>",
            )
            return True

        if text == "✍️ سؤال جديد":
            state["awaiting"] = "assistant_question"
            _send(base, chat_id, "✍️ اكتب سؤالك عن سهم، السوق، الفرص أو المحفظة.")
            return True

        if text == "📌 حلّل آخر سهم":
            sym = state.get("assistant_last_symbol") or state.get("last_analysis_symbol")
            if not sym:
                state["awaiting"] = "assistant_question"
                _send(base, chat_id, "📌 اكتب رمز السهم أولًا، مثال <b>COMI</b>.")
            else:
                _send(base, chat_id, _stock_answer(base, _runtime(base), state, sym))
            return True

        if text == "🎯 أفضل الفرص":
            _send(base, chat_id, _opportunities_answer(_runtime(base)))
            return True

        if text == "🗺️ ملخص السوق":
            _send(base, chat_id, _market_answer(_runtime(base)))
            return True

        if text == "💼 ملخص محفظتي":
            _send(base, chat_id, _portfolio_answer(_runtime(base)))
            return True

        if state.get("awaiting") == "assistant_question":
            state.pop("awaiting", None)
            _answer(base, chat_id, text, state)
            return True

        return original_handle(chat_id, text, state)

    base.handle = assistant_handle
    return base


def self_test():
    class Base:
        @staticmethod
        def normalize_symbol(s):
            s = (s or "").strip().upper()
            return s if s.isalnum() and len(s) <= 12 else ""

    state = {}
    assert _candidate_symbol(Base, "حلل COMI", state) == "COMI"
    assert _candidate_symbol(Base, "RSI كام؟", {"assistant_last_symbol": "SWDY"}) == "SWDY"
    runtime = {"pro_engine_snapshot": {"market_regime": {"name": "NEUTRAL", "breadth": 51, "avg_score": 58}, "top": []}}
    assert "51.0%" in _market_answer(runtime)
    print("bot assistant self-test: PASS")


if __name__ == "__main__":
    self_test()
