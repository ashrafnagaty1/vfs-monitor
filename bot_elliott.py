import json


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


ELLIOTT_MENU = _keyboard([
    ["🔄 تحديث إليوت", "🔍 تحليل سهم"],
    ["🧠 التحليل المتقدم", "🏠 القائمة الرئيسية"],
])


def _send(base, chat_id, text, keyboard=ELLIOTT_MENU):
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


def _structure_lines(title, structure):
    if not structure:
        return [f"➖ لا يوجد {title} يحقق القواعد المحافظة في أحدث البنية."]
    direction = "🟢 صاعد" if structure.get("direction") == "BULLISH" else "🔴 هابط"
    lines = [
        f"{title}: <b>{direction}</b> · Score قواعد <b>{int(structure.get('confidence_score') or 0)}/100</b>",
        f"⏱️ عمر آخر Pivot: <b>{int(structure.get('age_bars') or 0)}</b> جلسة",
    ]
    rules = structure.get("rules") or {}
    for name, ok in rules.items():
        lines.append(f"{'✅' if ok else '⚠️'} {name.replace('_', ' ')}")
    ratios = structure.get("ratios") or {}
    if ratios:
        lines.append("📐 النسب: " + " · ".join(f"{k} {float(v):.2f}" for k, v in ratios.items()))
    points = structure.get("points") or []
    if points:
        lines.append("📍 النقاط: " + " · ".join(f"{p.get('label')}={float(p.get('price') or 0):.2f}" for p in points))
    return lines


def _render(base, chat_id, state, symbol):
    sym = base.normalize_symbol(symbol)
    if not sym:
        _send(base, chat_id, "⚠️ اكتب رمز سهم صحيح مثل <b>COMI</b>.")
        return
    try:
        from elliott_analysis import analyze_symbol
        out = analyze_symbol(sym)
    except Exception:
        _send(base, chat_id, f"⚠️ تعذر تشغيل تحليل إليوت على <b>{sym}</b> حاليًا.")
        return

    state["last_elliott_symbol"] = sym
    lines = [
        f"🌊 <b>موجات إليوت — {sym}</b>",
        "<i>ترقيم احتمالي محافظ من Swing pivots على OHLCV اليومي فقط؛ لا يتم اختلاق موجة مستقبلية.</i>",
        "",
        f"💵 آخر إغلاق/سعر موثوق: <b>{float(out.get('price') or 0):.2f}</b>",
        f"🕯️ الفريم: <b>{out.get('timeframe', '1D')}</b>",
        f"🔎 Pivot points: <b>{int(out.get('pivot_count') or 0)}</b>",
        "",
    ]
    lines.extend(_structure_lines("🌊 Impulse 0-5 candidate", out.get("impulse")))
    lines.append("")
    lines.extend(_structure_lines("🔁 ABC candidate", out.get("abc")))
    lines.extend([
        "",
        "⚠️ Elliott counting بطبيعته تفسيري؛ النتيجة Algorithmic heuristic وليست ترقيمًا يقينيًا أو توصية دخول.",
    ])
    _send(base, chat_id, "\n".join(lines))


def apply(base):
    original_handle = base.handle

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text == "🌊 موجات إليوت":
            state["awaiting"] = "elliott"
            _send(base, chat_id, "🌊 اكتب رمز السهم لتحليل Elliott candidate على بيانات <b>1D OHLCV</b> الحقيقية المتاحة.")
            return True

        if state.get("awaiting") == "elliott":
            state.pop("awaiting", None)
            _render(base, chat_id, state, text)
            return True

        if text == "🔄 تحديث إليوت":
            sym = state.get("last_elliott_symbol")
            if not sym:
                state["awaiting"] = "elliott"
                _send(base, chat_id, "🌊 اكتب رمز السهم أولًا.")
            else:
                _render(base, chat_id, state, sym)
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    assert ELLIOTT_MENU["keyboard"][0][0] == "🔄 تحديث إليوت"
    print("bot elliott self-test: PASS")


if __name__ == "__main__":
    self_test()
