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
