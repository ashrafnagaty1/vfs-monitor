import bot_experience


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
    ["📋 قائمة المتابعة", "🚨 تنبيهاتي"],
    ["💼 محفظتي", "📈 تقرير الأداء"],
    ["🤖 المساعد الذكي", "⚙️ الإعدادات"],
])

WATCHLIST_MENU = _keyboard([
    ["➕ إضافة سهم", "➖ إزالة سهم"],
    ["🔍 تحليل من المتابعة", "🔄 تحديث المتابعة"],
    ["🎯 فرص اليوم", "🏠 القائمة الرئيسية"],
])

STOCK_ACTION_MENU = _keyboard([
    ["🔄 تحديث التحليل", "📐 تحليل متقدم للسهم"],
    ["👁️ متابعة الخطة", "🗑️ إلغاء المتابعة"],
    ["📋 قائمة المتابعة", "📊 الشاشة اللحظية"],
    ["🏠 القائمة الرئيسية"],
])


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


def _quote_label(snapshot):
    mode = str(snapshot.get("quote_mode") or "").upper()
    if mode == "LIVE":
        return "🟢 LIVE مؤكد"
    source = snapshot.get("quote_source") or "OHLCV / آخر Snapshot متاح"
    return f"🟡 DELAYED / EVALUATION — {source}"


def _build_watchlist_text(state):
    symbols = []
    for raw in state.get("user_watchlist") or []:
        sym = str(raw or "").strip().upper().replace(".CA", "")
        if sym and sym not in symbols:
            symbols.append(sym)

    snap = state.get("pro_engine_snapshot") or {}
    top = {str(x.get("symbol") or "").upper(): x for x in _as_list(snap.get("top"))}
    lifecycle = state.get("trade_lifecycle") or {}
    plans = {
        str(x.get("symbol") or "").upper(): x
        for x in _as_list(lifecycle.get("plans"))
        if x.get("symbol")
    }

    lines = [
        "📋 <b>قائمة المتابعة الشخصية</b>",
        f"📡 {_quote_label(snap)}",
        "",
    ]
    if not symbols:
        lines.extend([
            "لا توجد أسهم في المتابعة حاليًا.",
            "استخدم ➕ إضافة سهم أو أضف السهم مباشرة من بطاقة التحليل عبر 👁️ متابعة الخطة.",
        ])
        return "\n".join(lines)

    for i, sym in enumerate(symbols[:20], 1):
        market = top.get(sym) or {}
        plan = plans.get(sym) or {}
        status = str(plan.get("lifecycle_status") or plan.get("status") or "WATCH")
        score = market.get("score", plan.get("score"))
        price = market.get("price", plan.get("last_price"))
        trigger = plan.get("trigger")
        stop = plan.get("dynamic_stop") or plan.get("initial_stop")
        sid = plan.get("signal_id")

        headline = f"{i}) <b>{sym}</b> · {status}"
        if score is not None:
            headline += f" · Score {_num(score, 0)}"
        lines.append(headline)

        details = []
        if price is not None:
            details.append(f"Price {_num(price)}")
        if trigger is not None:
            details.append(f"Trigger {_num(trigger)}")
        if stop is not None:
            details.append(f"Stop {_num(stop)}")
        if details:
            lines.append("   " + " · ".join(details))
        if sid:
            lines.append(f"   ID <code>{sid}</code>")

    if str(snap.get("quote_mode") or "").upper() != "LIVE":
        lines.extend([
            "",
            "⚠️ الأسعار/الحالات هنا مبنية على آخر Snapshot متاح. لا تتحول WATCH إلى ENTRY من بيانات متأخرة.",
        ])
    return "\n".join(lines)


def apply(base):
    """Add a persistent personal watchlist without changing the proven signal engine."""
    original_handle = base.handle

    # Keep every existing menu path aligned with the richer ReFo hierarchy.
    bot_experience.MAIN_MENU = MAIN_MENU
    bot_experience.STOCK_ACTION_MENU = STOCK_ACTION_MENU
    base.MAIN_MENU = MAIN_MENU

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()

        if text in ("📋 قائمة المتابعة", "🔄 تحديث المتابعة"):
            state.pop("awaiting", None)
            bot_experience._send_keyboard(
                base,
                _build_watchlist_text(state),
                chat_id,
                WATCHLIST_MENU,
            )
            return True

        if text == "➕ إضافة سهم":
            state["awaiting"] = "watch_add"
            bot_experience._send_keyboard(
                base,
                "➕ <b>إضافة إلى قائمة المتابعة</b>\n\nاكتب رمز السهم، مثال <b>COMI</b>.",
                chat_id,
                WATCHLIST_MENU,
            )
            return True

        if text == "➖ إزالة سهم":
            state["awaiting"] = "watch_remove"
            bot_experience._send_keyboard(
                base,
                "➖ <b>إزالة من قائمة المتابعة</b>\n\nاكتب رمز السهم الذي تريد إزالته.",
                chat_id,
                WATCHLIST_MENU,
            )
            return True

        if text == "🔍 تحليل من المتابعة":
            state["awaiting"] = "watch_analyze"
            bot_experience._send_keyboard(
                base,
                "🔍 اكتب رمز سهم موجود في قائمة المتابعة لفتح بطاقة التحليل الغنية.",
                chat_id,
                WATCHLIST_MENU,
            )
            return True

        awaiting = state.get("awaiting")
        if awaiting in ("watch_add", "watch_remove", "watch_analyze"):
            sym = base.normalize_symbol(text)
            if not sym:
                bot_experience._send_keyboard(base, "⚠️ رمز غير صالح. مثال صحيح: <b>COMI</b>.", chat_id, WATCHLIST_MENU)
                return True

            watch = []
            for raw in state.get("user_watchlist") or []:
                item = base.normalize_symbol(str(raw))
                if item and item not in watch:
                    watch.append(item)

            if awaiting == "watch_add":
                state.pop("awaiting", None)
                if sym not in watch:
                    watch.append(sym)
                state["user_watchlist"] = watch
                bot_experience._send_keyboard(
                    base,
                    f"✅ تمت إضافة <b>{sym}</b> إلى قائمة المتابعة الشخصية.\n"
                    "لن تُنشأ ENTRY تلقائيًا إذا كان مصدر السعر متأخرًا.",
                    chat_id,
                    WATCHLIST_MENU,
                )
                return True

            if awaiting == "watch_remove":
                state.pop("awaiting", None)
                existed = sym in watch
                state["user_watchlist"] = [x for x in watch if x != sym]
                msg = f"🗑️ تمت إزالة <b>{sym}</b> من المتابعة." if existed else f"ℹ️ <b>{sym}</b> غير موجود أصلًا في قائمة المتابعة."
                bot_experience._send_keyboard(base, msg, chat_id, WATCHLIST_MENU)
                return True

            state.pop("awaiting", None)
            if sym not in watch:
                bot_experience._send_keyboard(
                    base,
                    f"⚠️ <b>{sym}</b> ليس في قائمة المتابعة. أضفه أولًا أو استخدم تحليل سهم من القائمة الرئيسية.",
                    chat_id,
                    WATCHLIST_MENU,
                )
                return True
            state["last_analysis_symbol"] = sym
            return original_handle(chat_id, "🔄 تحديث التحليل", state)

        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    state = {
        "user_watchlist": ["COMI", "COMI.CA", "SWDY"],
        "pro_engine_snapshot": {
            "quote_mode": "DELAYED_EVALUATION",
            "quote_source": "daily OHLCV",
            "top": [
                {"symbol": "COMI", "price": 77.25, "score": 84},
                {"symbol": "SWDY", "price": 61.10, "score": 72},
            ],
        },
        "trade_lifecycle": {
            "plans": {
                "COMI": {
                    "symbol": "COMI",
                    "signal_id": "COMI-a1",
                    "status": "WATCH",
                    "trigger": 78.0,
                    "initial_stop": 73.5,
                }
            }
        },
    }
    text = _build_watchlist_text(state)
    assert text.count("<b>COMI</b>") == 1
    assert "COMI-a1" in text
    assert "DELAYED / EVALUATION" in text
    assert "WATCH" in text
    assert "SWDY" in text
    assert "ENTRY" not in text


if __name__ == "__main__":
    self_test()
    print("bot watchlist self-test: PASS")
