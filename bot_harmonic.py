import json


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


HARMONIC_MENU = _keyboard([
    ["🔄 تحديث الهارمونيك", "🔍 تحليل سهم"],
    ["🧠 التحليل المتقدم", "🏠 القائمة الرئيسية"],
])


def _send(base, chat_id, text, keyboard=HARMONIC_MENU):
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


def _render(base, chat_id, state, symbol):
    sym = base.normalize_symbol(symbol)
    if not sym:
        _send(base, chat_id, "⚠️ اكتب رمز سهم صحيح مثل <b>COMI</b>.")
        return
    try:
        from harmonic_analysis import analyze_symbol
        out = analyze_symbol(sym)
    except Exception:
        _send(base, chat_id, f"⚠️ تعذر تشغيل تحليل الهارمونيك على <b>{sym}</b> حاليًا.")
        return

    state["last_harmonic_symbol"] = sym
    lines = [
        f"🦋 <b>الهارمونيك — {sym}</b>",
        "<i>كشف خوارزمي لنماذج XABCD المكتملة من OHLCV اليومي فقط؛ لا يتم اختلاق Intraday أو نقاط مستقبلية.</i>",
        "",
        f"💵 آخر إغلاق/سعر موثوق: <b>{float(out.get('price') or 0):.2f}</b>",
        f"🕯️ الفريم: <b>{out.get('timeframe', '1D')}</b>",
        f"🔎 عدد Pivot points المستخدمة: <b>{int(out.get('pivot_count') or 0)}</b>",
    ]

    p = out.get("pattern")
    if not p:
        lines.extend([
            "",
            "➖ لا يوجد نموذج Gartley/Bat/Butterfly/Crab مكتمل يطابق حدود النسب الحالية في أحدث البنية.",
            "هذا أفضل من فرض نموذج بصري غير مؤكد.",
        ])
    else:
        direction = "🟢 صاعد" if p.get("direction") == "BULLISH" else "🔴 هابط"
        lines.extend([
            "",
            f"🎯 النموذج: <b>{p.get('pattern')}</b> · {direction}",
            f"⏱️ عمر نقطة D: <b>{int(p.get('age_bars') or 0)}</b> جلسة",
            "📐 <b>النسب</b>",
        ])
        for k, v in (p.get("ratios") or {}).items():
            lines.append(f"• {k}: <b>{float(v):.3f}</b>")
        lines.append("📍 <b>نقاط XABCD</b>")
        for pt in p.get("points") or []:
            lines.append(f"• {pt.get('label')}: {float(pt.get('price') or 0):.2f} ({pt.get('kind')})")

    lines.extend([
        "",
        "⚠️ النتيجة Pattern heuristic وليست تأكيد انعكاس أو توصية دخول. يجب دمجها مع الاتجاه والسيولة والوقف.",
    ])
    _send(base, chat_id, "\n".join(lines))


def apply(base):
    original_handle = base.handle

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text == "🦋 الهارمونيك":
            state["awaiting"] = "harmonic"
            _send(base, chat_id, "🦋 اكتب رمز السهم لكشف نماذج XABCD على بيانات <b>1D OHLCV</b> الحقيقية المتاحة.")
            return True

        if state.get("awaiting") == "harmonic":
            state.pop("awaiting", None)
            _render(base, chat_id, state, text)
            return True

        if text == "🔄 تحديث الهارمونيك":
            sym = state.get("last_harmonic_symbol")
            if not sym:
                state["awaiting"] = "harmonic"
                _send(base, chat_id, "🦋 اكتب رمز السهم أولًا.")
            else:
                _render(base, chat_id, state, sym)
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    assert HARMONIC_MENU["keyboard"][0][0] == "🔄 تحديث الهارمونيك"
    print("bot harmonic self-test: PASS")


if __name__ == "__main__":
    self_test()
