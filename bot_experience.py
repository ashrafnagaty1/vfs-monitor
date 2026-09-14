import json


def _keyboard(rows):
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "is_persistent": True,
    }


MAIN_MENU = _keyboard([
    ["📊 الشاشة اللحظية", "🎯 فرص اليوم"],
    ["🔍 تحليل سهم", "🧠 التحليل المتقدم"],
    ["🚀 الإشارات النشطة", "🔮 فرص بكرة"],
    ["🟡 Golden Zone", "🗺️ السوق والقطاعات"],
    ["🚨 تنبيهاتي", "💼 محفظتي"],
    ["📈 تقرير الأداء", "🤖 المساعد الذكي"],
    ["⚙️ الإعدادات"],
])

ADVANCED_MENU = _keyboard([
    ["📐 الفني المتقدم", "🧭 Smart Money"],
    ["⏳ التوقع الزمني", "📏 تحليل جان"],
    ["🦋 الهارمونيك", "🌊 موجات إليوت"],
    ["📑 التقارير المالية", "💰 القيمة العادلة"],
    ["🏠 القائمة الرئيسية"],
])

MARKET_MENU = _keyboard([
    ["🗺️ أداء القطاعات", "📊 الشاشة اللحظية"],
    ["🎯 فرص اليوم", "🔮 فرص بكرة"],
    ["🏠 القائمة الرئيسية"],
])

STOCK_ACTION_MENU = _keyboard([
    ["🔄 تحديث التحليل", "📐 تحليل متقدم للسهم"],
    ["👁️ متابعة الخطة", "🗑️ إلغاء المتابعة"],
    ["📊 الشاشة اللحظية", "🏠 القائمة الرئيسية"],
])

PORTFOLIO_MENU = _keyboard([
    ["🚀 الإشارات النشطة", "📈 تقرير الأداء"],
    ["🔄 تحديث المحفظة", "🏠 القائمة الرئيسية"],
])

SIGNALS_MENU = _keyboard([
    ["💼 محفظتي", "📈 تقرير الأداء"],
    ["🎯 فرص اليوم", "🏠 القائمة الرئيسية"],
])


def _send_keyboard(base, text, chat_id, keyboard):
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


def _disabled(base, chat_id, title, reason):
    _send_keyboard(
        base,
        f"🚧 <b>{title}</b>\n\nالميزة غير مفعلة حاليًا لأن {reason}.\n"
        "لن يعرض ReFo نتيجة تقديرية على أنها تحليل حقيقي قبل توفر البيانات/الخوارزمية الموثوقة.",
        chat_id,
        ADVANCED_MENU,
    )


def _source_label(base, analysis):
    if analysis.get("quote_live"):
        return "🟢 LIVE — مصدر السعر أكد اللحظية"
    try:
        snap = base.load_json(base.STATE_FILE, {}).get("pro_engine_snapshot") or {}
        source = snap.get("quote_source") or "OHLCV / آخر إغلاق متاح"
    except Exception:
        source = "OHLCV / آخر إغلاق متاح"
    return f"🟡 DELAYED / EVALUATION — {source}"


def _plan_status(analysis):
    price = float(analysis.get("price") or 0)
    trigger = float(analysis.get("res20") or 0)
    if analysis.get("quote_live") and trigger and price >= trigger * 0.997:
        return "ENTRY", "🟢"
    return "WATCH", "🟡"


def _rr(entry, stop, target):
    risk = max(0.0, float(entry) - float(stop))
    reward = max(0.0, float(target) - float(entry))
    return reward / risk if risk > 0 else 0.0


def _as_list(value):
    """Accept schema-v2 lists and legacy dict-shaped collections safely."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _runtime_state(base):
    try:
        return base.load_json(base.STATE_FILE, {}) or {}
    except Exception:
        return {}


def _num(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _quote_mode_label(mode):
    return "🟢 LIVE مؤكد" if mode == "LIVE" else "🟡 DELAYED / EVALUATION"


def _build_active_signals_text(runtime):
    lifecycle = runtime.get("trade_lifecycle") or {}
    plans = _as_list(lifecycle.get("plans"))
    quote_mode = lifecycle.get("quote_mode") or "DELAYED_EVALUATION"
    if not plans:
        return (
            "🚀 <b>الإشارات النشطة</b>\n\n"
            "لا توجد خطط نشطة محفوظة حاليًا.\n"
            f"📡 {_quote_mode_label(quote_mode)}"
        )

    rank = {"T3": 0, "T2": 1, "T1": 2, "ENTRY": 3, "WATCH": 4}
    plans = sorted(
        plans,
        key=lambda p: (rank.get(str(p.get("lifecycle_status") or p.get("status") or "WATCH"), 9), -float(p.get("score") or 0)),
    )
    lines = [
        "🚀 <b>الإشارات النشطة</b>",
        f"📡 {_quote_mode_label(quote_mode)}",
        "",
    ]
    for p in plans[:10]:
        status = str(p.get("lifecycle_status") or p.get("status") or "WATCH")
        icon = {"WATCH": "🟡", "ENTRY": "🟢", "T1": "1️⃣", "T2": "2️⃣", "T3": "3️⃣"}.get(status, "•")
        sid = str(p.get("signal_id") or "-")
        lines.extend([
            f"{icon} <b>{p.get('symbol', '-')}</b> · {status} · Score {_num(p.get('score'), 0)}",
            f"   ID <code>{sid}</code>",
            f"   Trigger {_num(p.get('trigger'))} · Stop {_num(p.get('dynamic_stop') or p.get('initial_stop'))}",
            f"   T1 {_num(p.get('target1'))} · T2 {_num(p.get('target2'))} · T3 {_num(p.get('target3'))}",
        ])
    if quote_mode != "LIVE":
        lines.extend(["", "⚠️ البيانات الحالية لا تسمح بتحويل WATCH إلى ENTRY؛ لا يتم إنشاء صفقة من مصدر متأخر."])
    return "\n".join(lines)


def _build_portfolio_text(runtime):
    portfolio = runtime.get("signal_portfolio") or {}
    quote_mode = portfolio.get("quote_mode") or (runtime.get("trade_lifecycle") or {}).get("quote_mode") or "DELAYED_EVALUATION"
    open_positions = _as_list(portfolio.get("open_positions"))
    closed = _as_list(portfolio.get("closed_trades"))
    lines = [
        "💼 <b>محفظة إشارات ReFo</b>",
        f"📡 {_quote_mode_label(quote_mode)}",
        f"🟢 مراكز مفتوحة: <b>{len(open_positions)}</b> · 📁 مغلقة: <b>{len(closed)}</b>",
        "",
    ]
    if not open_positions:
        lines.append("لا توجد مراكز إشارات مفتوحة حاليًا.")
    else:
        for pos in open_positions[:8]:
            status = str(pos.get("lifecycle_status") or pos.get("stage") or "ENTRY")
            lines.extend([
                f"📌 <b>{pos.get('symbol', '-')}</b> · {status}",
                f"   ID <code>{pos.get('signal_id', '-')}</code>",
                f"   Entry {_num(pos.get('entry_price'))} · Last {_num(pos.get('last_price'))}",
                f"   Stop {_num(pos.get('dynamic_stop') or pos.get('initial_stop'))} · P/L {_num(pos.get('unrealized_r'))}R",
                f"   T1 {_num(pos.get('target1'))} · T2 {_num(pos.get('target2'))} · T3 {_num(pos.get('target3'))}",
            ])
    lines.extend([
        "",
        "⚠️ هذه محفظة تتبع إشارات مؤكدة وليست كشف حساب وساطة. البيانات delayed لا تنشئ مراكز جديدة.",
    ])
    return "\n".join(lines)


def _build_performance_text(runtime):
    portfolio = runtime.get("signal_portfolio") or {}
    perf = portfolio.get("performance") or {}
    events = _as_list(portfolio.get("events"))
    lines = [
        "📈 <b>تقرير أداء إشارات ReFo</b>",
        f"الصفقات المغلقة: <b>{int(perf.get('closed_trades') or 0)}</b> · المفتوحة: <b>{int(perf.get('open_positions') or 0)}</b>",
        f"✅ فوز {int(perf.get('wins') or 0)} · ❌ خسارة {int(perf.get('losses') or 0)} · ➖ تعادل {int(perf.get('breakeven') or 0)}",
        f"🎯 Win rate: <b>{_num(perf.get('win_rate_pct'), 1)}%</b>",
        f"⚖️ Total R: <b>{_num(perf.get('total_r'))}R</b> · Avg R: <b>{_num(perf.get('avg_r'))}R</b>",
        f"🏆 Best: {_num(perf.get('best_r'))}R · Worst: {_num(perf.get('worst_r'))}R",
    ]
    if events:
        labels = {"ENTRY": "🟢 ENTRY", "T1": "1️⃣ T1", "T2": "2️⃣ T2", "T3": "3️⃣ T3", "CLOSED": "🔒 CLOSED"}
        lines.append("\n🧾 <b>آخر أحداث دورة الصفقة</b>")
        for e in events[-8:][::-1]:
            event = str(e.get("event") or "-")
            label = labels.get(event, event)
            detail = f" · {e.get('detail')}" if e.get("detail") else ""
            lines.append(f"• {e.get('symbol', '-')} · {label} @ {_num(e.get('price'))}{detail}")
    else:
        lines.append("\nلا توجد أحداث تداول مؤكدة مسجلة بعد.")
    lines.extend([
        "",
        "ℹ️ التقرير يحتسب فقط ENTRY المؤكد في وضع LIVE؛ WATCH الناتج من delayed/evaluation مستبعد من الأداء.",
    ])
    return "\n".join(lines)


def _render_stock_card(base, chat_id, state, symbol, advanced=False):
    sym = base.normalize_symbol(symbol)
    if not sym:
        _send_keyboard(base, "⚠️ اكتب رمز سهم صحيح مثل <b>COMI</b>.", chat_id, MAIN_MENU)
        return
    try:
        from pro_engine import analyze

        a = analyze(sym)
    except Exception:
        _send_keyboard(base, f"⚠️ تعذر تحليل <b>{sym}</b> حاليًا.", chat_id, MAIN_MENU)
        return

    state["last_analysis_symbol"] = sym
    price = float(a.get("price") or 0)
    stop = float(a.get("stop") or 0)
    trigger = float(a.get("res20") or 0)
    t1 = float(a.get("t1") or 0)
    t2 = float(a.get("t2") or 0)
    t3 = float(a.get("t3") or 0)
    status, status_icon = _plan_status(a)
    source_label = _source_label(base, a)
    reasons = a.get("why") or []
    setups = a.get("setups") or []
    followed = sym in set(state.get("user_watchlist") or [])

    lines = [
        f"📌 <b>ReFo — {sym}</b>",
        f"{status_icon} الحالة: <b>{status}</b>{' · تحت المتابعة' if followed else ''}",
        f"💵 السعر المرجعي: <b>{price:.2f}</b>",
        f"🎯 Trigger: <b>{trigger:.2f}</b>",
        f"🛑 Stop: <b>{stop:.2f}</b>",
        f"🏁 T1 {t1:.2f} · T2 {t2:.2f} · T3 {t3:.2f}",
        f"⚖️ RR: T1 <b>{_rr(price, stop, t1):.2f}R</b> · T2 <b>{_rr(price, stop, t2):.2f}R</b> · T3 <b>{_rr(price, stop, t3):.2f}R</b>",
        f"⭐ Score: <b>{a.get('score', 0)}/100</b> · Confidence <b>{a.get('confidence', '-')}</b>",
        f"💧 Liquidity {float(a.get('liquidity_score') or 0):.0f}/100 · Volume {float(a.get('vr') or 0):.2f}x",
        f"📐 RSI {float(a.get('rsi') or 0):.1f} · ADX {float(a.get('adx') or 0):.1f} · MFI {float(a.get('mfi') or 0):.1f}",
        f"📊 S1 {float(a.get('sup20') or 0):.2f} · R1 {trigger:.2f}",
    ]

    if advanced:
        lines.extend([
            f"📈 EMA20 {float(a.get('ema20') or 0):.2f} · EMA50 {float(a.get('ema50') or 0):.2f} · EMA200 {float(a.get('ema200') or 0):.2f}",
            f"🟡 Golden Zone {float(a.get('golden_low') or 0):.2f} — {float(a.get('golden_high') or 0):.2f}",
            f"⚡ Momentum 5D {float(a.get('mom5') or 0):+.2f}% · 20D {float(a.get('mom20') or 0):+.2f}%",
            f"🌡️ Volatility {float(a.get('volatility_pct') or 0):.2f}%",
        ])
        if setups:
            lines.append("🕯️ النماذج: " + " · ".join(setups[:4]))

    if reasons:
        lines.append("\n🔎 <b>أسباب الاختيار</b>")
        lines.extend([f"• {x}" for x in reasons[:6]])

    lines.extend([
        "",
        f"📡 {source_label}",
        "⚠️ WATCH لا يتحول إلى ENTRY إلا إذا كان السعر من مصدر Live مؤكد. التحليل أداة قرار وليس ضمان ربح.",
    ])
    _send_keyboard(base, "\n".join(lines), chat_id, STOCK_ACTION_MENU)


def apply(base):
    """Patch the lightweight Telegram UI without changing the proven engine."""
    original_handle = base.handle
    base.MAIN_MENU = MAIN_MENU

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()

        if text in ("/start", "/menu", "🏠 القائمة الرئيسية"):
            state.pop("awaiting", None)
            _send_keyboard(
                base,
                "📈 <b>ReFo . EGX Smart Trader</b>\n\n"
                "مساعد قرار للبورصة المصرية: تحليل فني، فرص، WATCH/ENTRY، متابعة خطط، محفظة وتنبيهات.\n"
                f"{base.market_status()}\n\n"
                "⚠️ لا توجد وعود ربح، ولا يتم اعتبار أي سعر LIVE إلا إذا أكده مصدر لحظي حقيقي.",
                chat_id,
                MAIN_MENU,
            )
            return True

        if text == "🧠 التحليل المتقدم":
            state.pop("awaiting", None)
            _send_keyboard(
                base,
                "🧠 <b>التحليل المتقدم</b>\n\n"
                "اختر الأداة. الأدوات غير المتاحة ببيانات حقيقية ستظهر بوضوح كغير مفعلة.",
                chat_id,
                ADVANCED_MENU,
            )
            return True

        if text == "📐 الفني المتقدم":
            state["awaiting"] = "advanced"
            _send_keyboard(base, "📐 اكتب رمز السهم للتحليل الفني المتقدم، مثال <b>COMI</b>.", chat_id, ADVANCED_MENU)
            return True

        if text == "🔍 تحليل سهم":
            state["awaiting"] = "analysis"
            _send_keyboard(base, "🔍 اكتب رمز السهم، مثال <b>COMI</b>.", chat_id, MAIN_MENU)
            return True

        awaiting = state.get("awaiting")
        if awaiting in ("analysis", "advanced"):
            state.pop("awaiting", None)
            _render_stock_card(base, chat_id, state, text, advanced=(awaiting == "advanced"))
            return True

        if text == "🔄 تحديث التحليل":
            sym = state.get("last_analysis_symbol")
            if not sym:
                state["awaiting"] = "analysis"
                _send_keyboard(base, "🔍 اكتب رمز السهم أولًا.", chat_id, MAIN_MENU)
            else:
                _render_stock_card(base, chat_id, state, sym, advanced=False)
            return True

        if text == "📐 تحليل متقدم للسهم":
            sym = state.get("last_analysis_symbol")
            if not sym:
                state["awaiting"] = "advanced"
                _send_keyboard(base, "📐 اكتب رمز السهم أولًا.", chat_id, ADVANCED_MENU)
            else:
                _render_stock_card(base, chat_id, state, sym, advanced=True)
            return True

        if text in ("👁️ متابعة الخطة", "🗑️ إلغاء المتابعة"):
            sym = state.get("last_analysis_symbol")
            if not sym:
                _send_keyboard(base, "⚠️ حلّل سهمًا أولًا ثم اختر متابعة الخطة.", chat_id, MAIN_MENU)
                return True
            watch = list(dict.fromkeys(state.get("user_watchlist") or []))
            if text == "👁️ متابعة الخطة":
                if sym not in watch:
                    watch.append(sym)
                state["user_watchlist"] = watch
                _send_keyboard(base, f"👁️ تمت إضافة <b>{sym}</b> إلى قائمة متابعة الخطط.\nلن يتحول إلى ENTRY تلقائيًا من بيانات متأخرة.", chat_id, STOCK_ACTION_MENU)
            else:
                state["user_watchlist"] = [x for x in watch if x != sym]
                _send_keyboard(base, f"🗑️ تم إلغاء متابعة <b>{sym}</b>.", chat_id, STOCK_ACTION_MENU)
            return True

        if text == "🚀 الإشارات النشطة":
            _send_keyboard(base, _build_active_signals_text(_runtime_state(base)), chat_id, SIGNALS_MENU)
            return True

        if text in ("💼 محفظتي", "🔄 تحديث المحفظة"):
            _send_keyboard(base, _build_portfolio_text(_runtime_state(base)), chat_id, PORTFOLIO_MENU)
            return True

        if text == "📈 تقرير الأداء":
            _send_keyboard(base, _build_performance_text(_runtime_state(base)), chat_id, PORTFOLIO_MENU)
            return True

        if text == "🗺️ السوق والقطاعات":
            state.pop("awaiting", None)
            _send_keyboard(
                base,
                "🗺️ <b>السوق والقطاعات</b>\n\n"
                "البيانات المعروضة هنا تعتمد على العينة والمصدر المتاحين، وليست Market Breadth كاملًا ما لم يتوفر Feed شامل.",
                chat_id,
                MARKET_MENU,
            )
            return True

        disabled = {
            "⏳ التوقع الزمني": ("التوقع الزمني", "لا توجد بعد خوارزمية توقيت موثوقة ومختبرة على بيانات كافية"),
            "📏 تحليل جان": ("تحليل جان", "وحدة Gann لم تُعتمد بعد على OHLCV الحالي"),
            "🦋 الهارمونيك": ("الأنماط الهارمونيك", "كاشف XABCD الموثوق لم يُفعّل بعد"),
            "🌊 موجات إليوت": ("موجات إليوت", "الترقيم الآلي يحتاج نموذجًا موثوقًا بدل تخمين بصري"),
            "🧭 Smart Money": ("Smart Money Concepts", "كاشف Order Blocks/FVG/Sweeps ما زال قيد التحقق"),
            "📑 التقارير المالية": ("التقارير المالية", "مصدر Fundamentals موثوق غير متصل"),
            "💰 القيمة العادلة": ("القيمة العادلة", "مصدر Fundamentals وافتراضات تقييم موثقة غير متوفرة بعد"),
        }
        if text in disabled:
            title, reason = disabled[text]
            _disabled(base, chat_id, title, reason)
            return True

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base
