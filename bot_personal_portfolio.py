import bot_experience


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


PORTFOLIO_MENU = _keyboard([
    ["➕ إضافة مركز", "🗑️ حذف مركز"],
    ["🔄 تحديث محفظتي", "🚀 محفظة الإشارات"],
    ["📈 تقرير الأداء", "🏠 القائمة الرئيسية"],
])


def _num(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _portfolio(state):
    raw = state.get("personal_portfolio")
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raw = {"schema_version": 1, "positions": {}}
        state["personal_portfolio"] = raw
    if not isinstance(raw.get("positions"), dict):
        raw["positions"] = {}
    return raw


def _latest_quote(base, symbol):
    try:
        from pro_engine import analyze
        a = analyze(symbol)
        price = float(a.get("price") or 0)
        if price <= 0:
            return None, "غير متاح"
        live = bool(a.get("quote_live"))
        return price, ("LIVE مؤكد" if live else "DELAYED / EVALUATION")
    except Exception:
        return None, "غير متاح"


def _render(base, state):
    p = _portfolio(state)
    positions = p.get("positions") or {}
    lines = [
        "💼 <b>محفظتي الشخصية — ReFo</b>",
        "<i>منفصلة عن محفظة إشارات النظام، ولا تُنشأ منها ENTRY تلقائيًا.</i>",
        "",
    ]
    if not positions:
        lines.extend([
            "لا توجد مراكز شخصية مسجلة.",
            "استخدم ➕ إضافة مركز لإدخال الرمز والكمية ومتوسط التكلفة.",
        ])
        return "\n".join(lines)

    total_cost = 0.0
    total_value = 0.0
    valued = 0
    for sym, pos in sorted(positions.items()):
        qty = float(pos.get("qty") or 0)
        avg = float(pos.get("avg") or 0)
        cost = qty * avg
        total_cost += cost
        last, mode = _latest_quote(base, sym)
        if last is not None:
            value = qty * last
            pnl = value - cost
            pnl_pct = (pnl / cost * 100.0) if cost > 0 else 0.0
            total_value += value
            valued += 1
            lines.extend([
                f"📌 <b>{sym}</b> · كمية {_num(qty, 0)} · متوسط {_num(avg)}",
                f"   آخر سعر {_num(last)} · P/L <b>{pnl:+.2f}</b> ({pnl_pct:+.2f}%)",
                f"   📡 {mode}",
            ])
        else:
            lines.extend([
                f"📌 <b>{sym}</b> · كمية {_num(qty, 0)} · متوسط {_num(avg)}",
                "   ⚠️ تعذر جلب سعر موثوق الآن؛ لم يتم احتساب P/L.",
            ])

    lines.append("")
    lines.append(f"💰 إجمالي التكلفة: <b>{total_cost:.2f}</b>")
    if valued == len(positions) and total_cost > 0:
        total_pnl = total_value - total_cost
        pct = total_pnl / total_cost * 100.0
        lines.append(f"📊 القيمة المرجعية: <b>{total_value:.2f}</b> · P/L <b>{total_pnl:+.2f}</b> ({pct:+.2f}%)")
    else:
        lines.append("ℹ️ الإجمالي السوقي غير مكتمل لأن بعض الأسعار غير متاحة.")
    lines.extend([
        "",
        "⚠️ الأسعار المتأخرة تُستخدم للتقييم فقط؛ لا تُعامل كتسعير تنفيذ لحظي.",
    ])
    return "\n".join(lines)


def apply(base):
    """Add a user-owned portfolio, separated from lifecycle signal positions."""
    original_handle = base.handle

    def send(chat_id, text, keyboard=PORTFOLIO_MENU):
        bot_experience._send_keyboard(base, text, chat_id, keyboard)

    def clear_flow(state):
        state.pop("personal_portfolio_flow", None)
        state.pop("personal_portfolio_draft", None)

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        flow = state.get("personal_portfolio_flow")

        if text in ("💼 محفظتي", "🔄 تحديث محفظتي"):
            clear_flow(state)
            send(chat_id, _render(base, state))
            return True

        if text == "🚀 محفظة الإشارات":
            clear_flow(state)
            send(chat_id, bot_experience._build_portfolio_text(bot_experience._runtime_state(base)), bot_experience.PORTFOLIO_MENU)
            return True

        if text == "➕ إضافة مركز":
            state["personal_portfolio_flow"] = "add_symbol"
            state["personal_portfolio_draft"] = {}
            send(chat_id, "➕ اكتب رمز السهم لإضافته إلى محفظتك، مثال <b>COMI</b>.")
            return True

        if text == "🗑️ حذف مركز":
            if not (_portfolio(state).get("positions") or {}):
                send(chat_id, "🗑️ لا توجد مراكز شخصية لحذفها.")
                return True
            state["personal_portfolio_flow"] = "remove_symbol"
            send(chat_id, "🗑️ اكتب رمز السهم الذي تريد حذفه من محفظتك.")
            return True

        if flow == "add_symbol":
            sym = base.normalize_symbol(text)
            if not sym:
                send(chat_id, "⚠️ رمز غير صالح. اكتب رمزًا مثل <b>COMI</b>.")
                return True
            state["personal_portfolio_draft"] = {"symbol": sym}
            state["personal_portfolio_flow"] = "add_qty"
            send(chat_id, f"📦 اكتب الكمية المملوكة من <b>{sym}</b>.")
            return True

        if flow == "add_qty":
            try:
                qty = float(text.replace(",", "."))
            except Exception:
                qty = 0
            if qty <= 0:
                send(chat_id, "⚠️ الكمية يجب أن تكون رقمًا أكبر من صفر.")
                return True
            state.setdefault("personal_portfolio_draft", {})["qty"] = qty
            state["personal_portfolio_flow"] = "add_avg"
            send(chat_id, "💵 اكتب متوسط سعر التكلفة للسهم.")
            return True

        if flow == "add_avg":
            try:
                avg = float(text.replace(",", "."))
            except Exception:
                avg = 0
            if avg <= 0:
                send(chat_id, "⚠️ متوسط التكلفة يجب أن يكون رقمًا أكبر من صفر.")
                return True
            draft = state.get("personal_portfolio_draft") or {}
            sym = draft.get("symbol")
            qty = float(draft.get("qty") or 0)
            if not sym or qty <= 0:
                clear_flow(state)
                send(chat_id, "⚠️ تعذر إكمال الإدخال؛ ابدأ إضافة المركز من جديد.")
                return True
            p = _portfolio(state)
            old = (p.get("positions") or {}).get(sym)
            if old:
                old_qty = float(old.get("qty") or 0)
                old_avg = float(old.get("avg") or 0)
                new_qty = old_qty + qty
                avg = ((old_qty * old_avg) + (qty * avg)) / new_qty if new_qty > 0 else avg
                qty = new_qty
            p["positions"][sym] = {"qty": qty, "avg": avg}
            clear_flow(state)
            send(chat_id, f"✅ تم حفظ <b>{sym}</b> · الكمية {_num(qty, 0)} · متوسط {_num(avg)}.\n\n" + _render(base, state))
            return True

        if flow == "remove_symbol":
            sym = base.normalize_symbol(text)
            p = _portfolio(state)
            if not sym or sym not in p["positions"]:
                send(chat_id, "⚠️ السهم غير موجود في محفظتك. اكتب رمز مركز مسجل.")
                return True
            p["positions"].pop(sym, None)
            clear_flow(state)
            send(chat_id, f"🗑️ تم حذف <b>{sym}</b> من محفظتك الشخصية.\n\n" + _render(base, state))
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    state = {}
    p = _portfolio(state)
    assert p["schema_version"] == 1 and p["positions"] == {}
    p["positions"]["COMI"] = {"qty": 10, "avg": 50}
    assert _portfolio(state)["positions"]["COMI"]["qty"] == 10
    assert _num(12.345) == "12.35"
    print("personal portfolio self-test: PASS")


if __name__ == "__main__":
    self_test()
