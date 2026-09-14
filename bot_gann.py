import json


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


GANN_MENU = _keyboard([
    ["🔄 تحديث جان", "🔍 تحليل سهم"],
    ["🧠 التحليل المتقدم", "🏠 القائمة الرئيسية"],
])


def _send(base, chat_id, text, keyboard=GANN_MENU):
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


def _levels(values):
    values = values or []
    return " · ".join(f"{float(x):.2f}" for x in values) if values else "-"


def _render(base, chat_id, state, symbol):
    sym = base.normalize_symbol(symbol)
    if not sym:
        _send(base, chat_id, "⚠️ اكتب رمز سهم صحيح مثل <b>COMI</b>.")
        return
    try:
        from gann_analysis import analyze_symbol
        out = analyze_symbol(sym)
    except Exception:
        _send(base, chat_id, f"⚠️ تعذر تشغيل تحليل جان على <b>{sym}</b> حاليًا.")
        return

    state["last_gann_symbol"] = sym
    reasons = out.get("reasons") or []
    trend_map = {"UP": "🟢 صاعد", "DOWN": "🔴 هابط", "SIDEWAYS": "🟡 عرضي/مختلط"}
    lines = [
        f"📏 <b>تحليل جان — {sym}</b>",
        "<i>مستويات مرجعية خوارزمية Gann-style من OHLCV اليومي فقط، وليست توقعًا زمنيًا أو ضمانًا للحركة.</i>",
        "",
        f"💵 آخر إغلاق/سعر موثوق: <b>{float(out.get('price') or 0):.2f}</b>",
        f"🕯️ الفريم: <b>{out.get('timeframe', '1D')}</b>",
        f"📈 الاتجاه: <b>{trend_map.get(out.get('trend'), out.get('trend'))}</b>",
        f"〽️ SMA20 {float(out.get('sma20') or 0):.2f} · SMA50 {float(out.get('sma50') or 0):.2f}",
        f"📐 نطاق 20 جلسة: {float(out.get('range_low') or 0):.2f} — {float(out.get('range_high') or 0):.2f}",
        f"📍 موضع السعر داخل النطاق: <b>{float(out.get('range_position_pct') or 0):.0f}%</b>",
        f"🟩 مستويات دعم Gann-style: <b>{_levels(out.get('supports'))}</b>",
        f"🟥 مستويات مقاومة Gann-style: <b>{_levels(out.get('resistances'))}</b>",
        f"⭐ Context score: <b>{int(out.get('score') or 0)}/100</b>",
    ]
    if reasons:
        lines.append("\n🔎 <b>سياق القراءة</b>")
        lines.extend(f"• {x}" for x in reasons[:5])
    lines.extend([
        "",
        "⚠️ لا يتم هنا اختلاق زوايا زمنية أو Intraday أو نقاط انعكاس مستقبلية غير مثبتة.",
    ])
    _send(base, chat_id, "\n".join(lines))


def apply(base):
    original_handle = base.handle

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text == "📏 تحليل جان":
            state["awaiting"] = "gann"
            _send(base, chat_id, "📏 اكتب رمز السهم لتشغيل قراءة Gann-style على بيانات <b>1D OHLCV</b> الحقيقية المتاحة.")
            return True

        if state.get("awaiting") == "gann":
            state.pop("awaiting", None)
            _render(base, chat_id, state, text)
            return True

        if text == "🔄 تحديث جان":
            sym = state.get("last_gann_symbol")
            if not sym:
                state["awaiting"] = "gann"
                _send(base, chat_id, "📏 اكتب رمز السهم أولًا.")
            else:
                _render(base, chat_id, state, sym)
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    assert GANN_MENU["keyboard"][0][0] == "🔄 تحديث جان"
    print("bot gann self-test: PASS")


if __name__ == "__main__":
    self_test()
