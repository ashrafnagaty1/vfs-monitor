import bot_experience


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


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


def _portfolio(runtime):
    return runtime.get("signal_portfolio") or {}


def _performance(runtime):
    return _portfolio(runtime).get("performance") or {}


def _quote_label(runtime):
    mode = str(_portfolio(runtime).get("quote_mode") or (runtime.get("trade_lifecycle") or {}).get("quote_mode") or "DELAYED_EVALUATION").upper()
    return "🟢 LIVE tracking" if mode == "LIVE" else "🟡 DELAYED / EVALUATION"


def _trade_r(trade):
    try:
        return float(trade.get("r_multiple") or 0)
    except Exception:
        return 0.0


def _quality_metrics(runtime):
    closed = _as_list(_portfolio(runtime).get("closed_trades"))
    r_values = [_trade_r(x) for x in closed]
    wins = [x for x in r_values if x > 0]
    losses = [x for x in r_values if x < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    expectancy = sum(r_values) / len(r_values) if r_values else 0.0
    avg_win = gross_win / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0

    reasons = {}
    for trade in closed:
        reason = str(trade.get("close_reason") or "UNKNOWN")
        reasons[reason] = reasons.get(reason, 0) + 1

    return {
        "count": len(closed),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "reasons": reasons,
    }


REPORTS_MENU = _keyboard([
    ["📊 ملخص الأداء", "🧮 جودة النظام"],
    ["📁 الصفقات المغلقة", "🧾 سجل الأحداث"],
    ["🚀 الإشارات النشطة", "💼 محفظتي"],
    ["🏠 القائمة الرئيسية"],
])


def _summary_text(runtime):
    perf = _performance(runtime)
    q = _quality_metrics(runtime)
    lines = [
        "📈 <b>ReFo — تقرير الأداء</b>",
        f"📡 {_quote_label(runtime)}",
        "",
        f"المغلقة: <b>{int(perf.get('closed_trades') or q['count'])}</b> · المفتوحة: <b>{int(perf.get('open_positions') or 0)}</b>",
        f"✅ فوز {int(perf.get('wins') or 0)} · ❌ خسارة {int(perf.get('losses') or 0)} · ➖ تعادل {int(perf.get('breakeven') or 0)}",
        f"🎯 Win rate: <b>{_num(perf.get('win_rate_pct'), 1)}%</b>",
        f"⚖️ Total R: <b>{_num(perf.get('total_r'))}R</b> · Avg R: <b>{_num(perf.get('avg_r'))}R</b>",
        f"🏆 Best: {_num(perf.get('best_r'))}R · Worst: {_num(perf.get('worst_r'))}R",
        "",
        "ℹ️ الأداء هنا خاص بمحفظة إشارات ReFo فقط؛ المحفظة الشخصية منفصلة.",
        "⚠️ WATCH الناتج من بيانات delayed/evaluation لا يدخل الإحصائيات إطلاقًا.",
    ]
    return "\n".join(lines)


def _quality_text(runtime):
    q = _quality_metrics(runtime)
    if not q["count"]:
        return (
            "🧮 <b>جودة النظام</b>\n\n"
            "لا توجد صفقات LIVE مغلقة كافية لحساب جودة فعلية حتى الآن.\n"
            "لن يستخدم ReFo خطط WATCH أو نتائج افتراضية لصناعة Profit Factor أو Expectancy وهمية."
        )
    pf = "∞" if q["profit_factor"] == float("inf") else _num(q["profit_factor"], 2)
    reason_text = " · ".join(f"{k}: {v}" for k, v in sorted(q["reasons"].items())) or "-"
    sample_note = "⚠️ عينة صغيرة؛ لا تُعمم" if q["count"] < 20 else "✅ عينة أولية قابلة للتقييم"
    return "\n".join([
        "🧮 <b>جودة نظام إشارات ReFo</b>",
        f"📡 {_quote_label(runtime)}",
        "",
        f"الصفقات المقاسة: <b>{q['count']}</b> — {sample_note}",
        f"📐 Expectancy: <b>{_num(q['expectancy'])}R/صفقة</b>",
        f"⚙️ Profit Factor (R): <b>{pf}</b>",
        f"✅ Avg Win: <b>{_num(q['avg_win'])}R</b>",
        f"❌ Avg Loss: <b>{_num(q['avg_loss'])}R</b>",
        f"📈 Gross Wins: {_num(q['gross_win'])}R · Gross Losses: {_num(q['gross_loss'])}R",
        f"🔒 أسباب الإغلاق: {reason_text}",
        "",
        "ℹ️ المقاييس محسوبة من R-multiple للصفقات المؤكدة المسجلة فقط، وليست Backtest ولا ضمان أداء مستقبلي.",
    ])


def _closed_text(runtime):
    closed = _as_list(_portfolio(runtime).get("closed_trades"))
    if not closed:
        return "📁 <b>الصفقات المغلقة</b>\n\nلا توجد صفقات إشارات LIVE مغلقة مسجلة بعد."
    lines = ["📁 <b>آخر الصفقات المغلقة</b>", f"📡 {_quote_label(runtime)}", ""]
    for trade in closed[-10:][::-1]:
        r = _trade_r(trade)
        icon = "✅" if r > 0 else ("❌" if r < 0 else "➖")
        lines.extend([
            f"{icon} <b>{trade.get('symbol', '-')}</b> · {r:+.2f}R · {trade.get('close_reason') or '-'}",
            f"   ID <code>{trade.get('signal_id', '-')}</code>",
            f"   Entry {_num(trade.get('entry_price'))} → Exit {_num(trade.get('exit_price'))}",
            f"   Open {trade.get('opened_at', '-')} · Close {trade.get('closed_at', '-')}",
        ])
    lines.extend(["", "ℹ️ هذه سجلات إشارات وليست تنفيذات وسيط أو كشف حساب تداول."])
    return "\n".join(lines)


def _events_text(runtime):
    events = _as_list(_portfolio(runtime).get("events"))
    if not events:
        return "🧾 <b>سجل الأحداث</b>\n\nلا توجد أحداث دورة تداول مؤكدة بعد."
    labels = {
        "ENTRY": "🟢 ENTRY",
        "T1": "1️⃣ T1",
        "T2": "2️⃣ T2",
        "T3": "3️⃣ T3",
        "STOP_HIT": "🛑 STOP",
        "CLOSED": "🔒 CLOSED",
    }
    lines = ["🧾 <b>سجل دورة الإشارات</b>", f"📡 {_quote_label(runtime)}", ""]
    for event in events[-15:][::-1]:
        kind = str(event.get("event") or "-")
        label = labels.get(kind, kind)
        detail = f" · {event.get('detail')}" if event.get("detail") else ""
        lines.append(
            f"• <b>{event.get('symbol', '-')}</b> · {label} @ {_num(event.get('price'))}{detail}\n"
            f"  <code>{event.get('signal_id', '-')}</code> · {event.get('at', '-')}"
        )
    return "\n".join(lines)


def apply(base):
    """Add interactive, non-fabricated performance reporting to Telegram."""
    original_handle = base.handle

    def send(chat_id, text):
        bot_experience._send_keyboard(base, text, chat_id, REPORTS_MENU)

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text in ("📈 تقرير الأداء", "📊 ملخص الأداء"):
            state.pop("awaiting", None)
            send(chat_id, _summary_text(_runtime(base)))
            return True
        if text == "🧮 جودة النظام":
            state.pop("awaiting", None)
            send(chat_id, _quality_text(_runtime(base)))
            return True
        if text == "📁 الصفقات المغلقة":
            state.pop("awaiting", None)
            send(chat_id, _closed_text(_runtime(base)))
            return True
        if text == "🧾 سجل الأحداث":
            state.pop("awaiting", None)
            send(chat_id, _events_text(_runtime(base)))
            return True
        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    runtime = {
        "signal_portfolio": {
            "quote_mode": "LIVE",
            "open_positions": [{"symbol": "C", "signal_id": "C-3"}],
            "closed_trades": [
                {"symbol": "A", "signal_id": "A-1", "entry_price": 10, "exit_price": 12, "r_multiple": 2, "close_reason": "T3"},
                {"symbol": "B", "signal_id": "B-2", "entry_price": 20, "exit_price": 19, "r_multiple": -1, "close_reason": "STOP_HIT"},
            ],
            "events": [{"symbol": "A", "signal_id": "A-1", "event": "CLOSED", "price": 12}],
            "performance": {"closed_trades": 2, "open_positions": 1, "wins": 1, "losses": 1, "win_rate_pct": 50, "total_r": 1, "avg_r": 0.5, "best_r": 2, "worst_r": -1},
        }
    }
    q = _quality_metrics(runtime)
    assert q["count"] == 2 and abs(q["profit_factor"] - 2.0) < 1e-9
    assert abs(q["expectancy"] - 0.5) < 1e-9
    assert "A-1" in _closed_text(runtime)
    assert "Profit Factor" in _quality_text(runtime)
    assert "WATCH" in _summary_text({"signal_portfolio": {"performance": {}}})
    print("bot reports self-test: PASS")


if __name__ == "__main__":
    self_test()
