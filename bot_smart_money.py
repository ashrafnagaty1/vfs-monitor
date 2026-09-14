import json


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


SMC_MENU = _keyboard([
    ["🔄 تحديث Smart Money", "🔍 تحليل سهم"],
    ["🧠 التحليل المتقدم", "🏠 القائمة الرئيسية"],
])


def _send(base, chat_id, text, keyboard=SMC_MENU):
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


def _fmt_zone(obj):
    if not obj:
        return "غير موجودة بوضوح في آخر 25 جلسة"
    return f"{obj.get('type')} · {float(obj.get('low') or 0):.2f} — {float(obj.get('high') or 0):.2f}"


def _render(base, chat_id, state, symbol):
    sym = base.normalize_symbol(symbol)
    if not sym:
        _send(base, chat_id, "⚠️ اكتب رمز سهم صحيح مثل <b>COMI</b>.")
        return
    try:
        from smart_money import analyze_symbol
        out = analyze_symbol(sym)
    except Exception:
        _send(base, chat_id, f"⚠️ تعذر تشغيل Smart Money على <b>{sym}</b> حاليًا.")
        return

    state["last_smc_symbol"] = sym
    sweep = "لا يوجد sweep واضح"
    if out.get("bullish_sweep"):
        sweep = "🟢 Sweep صاعد محتمل"
    elif out.get("bearish_sweep"):
        sweep = "🔴 Sweep هابط محتمل"

    reasons = out.get("reasons") or []
    lines = [
        f"🧭 <b>Smart Money — {sym}</b>",
        "<i>قراءة خوارزمية Heuristic من OHLCV اليومي، وليست Order Flow مؤسسيًا مؤكدًا.</i>",
        "",
        f"💵 آخر إغلاق/سعر موثوق: <b>{float(out.get('price') or 0):.2f}</b>",
        f"🕯️ الفريم: <b>{out.get('timeframe', '1D')}</b> فقط",
        f"⚖️ Premium / Discount: <b>{out.get('premium_discount')}</b>",
        f"〽️ نطاق 25 جلسة: {float(out.get('range_low') or 0):.2f} — {float(out.get('range_high') or 0):.2f}",
        f"➗ Equilibrium: {float(out.get('equilibrium') or 0):.2f}",
        f"💧 Liquidity Sweep: {sweep}",
        f"🟦 FVG: {_fmt_zone(out.get('fvg'))}",
        f"🟨 Order Block heuristic: {_fmt_zone(out.get('order_block'))}",
        f"⭐ SMC heuristic score: <b>{int(out.get('score') or 0)}/100</b>",
    ]
    if reasons:
        lines.append("\n🔎 <b>ملاحظات الخوارزمية</b>")
        lines.extend([f"• {x}" for x in reasons[:5]])
    lines.extend([
        "",
        "⚠️ لا يوجد Intraday/Bid-Ask/Market Depth في هذا التحليل، ولا يتم استنتاجها أو اختلاقها.",
    ])
    _send(base, chat_id, "\n".join(lines))


def apply(base):
    original_handle = base.handle

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text == "🧭 Smart Money":
            state["awaiting"] = "smart_money"
            _send(base, chat_id, "🧭 اكتب رمز السهم لتشغيل Smart Money heuristic على بيانات <b>1D OHLCV</b> الحقيقية المتاحة.")
            return True

        if state.get("awaiting") == "smart_money":
            state.pop("awaiting", None)
            _render(base, chat_id, state, text)
            return True

        if text == "🔄 تحديث Smart Money":
            sym = state.get("last_smc_symbol")
            if not sym:
                state["awaiting"] = "smart_money"
                _send(base, chat_id, "🧭 اكتب رمز السهم أولًا.")
            else:
                _render(base, chat_id, state, sym)
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    assert SMC_MENU["keyboard"][0][0] == "🔄 تحديث Smart Money"
    print("bot smart money self-test: PASS")


if __name__ == "__main__":
    self_test()
