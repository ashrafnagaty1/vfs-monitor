import json


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


TEMPORAL_MENU = _keyboard([
    ["🔄 تحديث التوقع الزمني", "🔍 تحليل سهم"],
    ["🧠 التحليل المتقدم", "🏠 القائمة الرئيسية"],
])


def _send(base, chat_id, text, keyboard=TEMPORAL_MENU):
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
        from temporal_analysis import analyze_symbol
        out = analyze_symbol(sym)
    except Exception:
        _send(base, chat_id, f"⚠️ تعذر تشغيل التوقع الزمني على <b>{sym}</b> حاليًا.")
        return

    state["last_temporal_symbol"] = sym
    if out.get("status") != "OK":
        _send(
            base,
            chat_id,
            f"⏳ <b>التوقع الزمني — {sym}</b>\n\n"
            "لا توجد Swing pivots مؤكدة كافية لاستخراج دورة زمنية محافظة حاليًا.\n"
            f"🕯️ الفريم: <b>{out.get('timeframe', '1D')}</b> · Pivots: <b>{int(out.get('pivot_count') or 0)}</b>\n\n"
            "⚠️ لن يعرض ReFo توقيتًا مصطنعًا عندما تكون البنية غير كافية.",
        )
        return

    phase_map = {
        "AHEAD": "🟡 قبل النافذة المتوقعة",
        "IN_WINDOW": "🟢 داخل النافذة الإحصائية",
        "OVERDUE": "🟠 تجاوز المتوسط التاريخي",
    }
    remaining = int(out.get("expected_next_pivot_in_sessions") or 0)
    start = int(out.get("window_start_sessions") or 0)
    end = int(out.get("window_end_sessions") or 0)
    lines = [
        f"⏳ <b>التوقع الزمني — {sym}</b>",
        "<i>تقدير نافذة زمنية من تباعد Swing pivots على OHLCV اليومي فقط.</i>",
        "",
        f"💵 آخر إغلاق/سعر موثوق: <b>{float(out.get('price') or 0):.2f}</b>",
        f"🕯️ الفريم: <b>{out.get('timeframe', '1D')}</b>",
        f"🔎 عدد Pivots المكتشفة: <b>{int(out.get('pivot_count') or 0)}</b>",
        f"🔁 Median cycle: <b>{float(out.get('median_cycle_sessions') or 0):.1f}</b> جلسة",
        f"📉 تشتت الدورة MAD: <b>{float(out.get('mad_sessions') or 0):.1f}</b> جلسة",
        f"⏱️ عمر آخر Pivot: <b>{int(out.get('last_pivot_age_sessions') or 0)}</b> جلسة",
        f"🧭 الحالة الزمنية: <b>{phase_map.get(out.get('phase'), out.get('phase', '-'))}</b>",
        f"🎯 المركز المتوقع للدورة: <b>{remaining}</b> جلسة من الآن",
        f"🪟 النافذة المحافظة: <b>{start} — {end}</b> جلسة من الآن",
        f"⭐ ثبات الإيقاع: <b>{int(out.get('confidence_score') or 0)}/100</b>",
        "",
        "⚠️ هذه نافذة احتمالية وليست توقع اتجاه أو سعر. لا يوجد Intraday timing ولا ادعاء بأن الانعكاس سيحدث حتمًا.",
    ]
    _send(base, chat_id, "\n".join(lines))


def apply(base):
    original_handle = base.handle

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text == "⏳ التوقع الزمني":
            state["awaiting"] = "temporal"
            _send(base, chat_id, "⏳ اكتب رمز السهم لاستخراج نافذة زمنية من بيانات <b>1D OHLCV</b> الحقيقية المتاحة.")
            return True

        if state.get("awaiting") == "temporal":
            state.pop("awaiting", None)
            _render(base, chat_id, state, text)
            return True

        if text == "🔄 تحديث التوقع الزمني":
            sym = state.get("last_temporal_symbol")
            if not sym:
                state["awaiting"] = "temporal"
                _send(base, chat_id, "⏳ اكتب رمز السهم أولًا.")
            else:
                _render(base, chat_id, state, sym)
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    assert TEMPORAL_MENU["keyboard"][0][0] == "🔄 تحديث التوقع الزمني"
    print("bot temporal self-test: PASS")


if __name__ == "__main__":
    self_test()
