"""Final V11 reference-menu compatibility layer.

Applied last in always_on_bot so older feature wrappers cannot replace the
canonical Telegram entry menu. Legacy labels remain accepted for compatibility.
"""
import bot_experience


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


REFERENCE_MAIN_MENU = _keyboard([
    ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"],
    ["💳 اشترك الآن / ترقية"],
    ["📈 أسهم المضاربة اليومية", "📊 الصفقات"],
    ["📈 تحليل الأسهم", "♟️ التحليل المتقدم"],
    ["🎯 فرص اليوم", "🚀 الإشارات النشطة"],
    ["📋 قائمة المتابعة", "🚨 تنبيهاتي"],
    ["💼 محفظتي", "📈 تقرير الأداء"],
    ["🗺️ السوق والقطاعات", "⚙️ الإعدادات"],
])

ALIASES = {
    "📈 تحليل الأسهم": "🔍 تحليل سهم",
    "📈 أسهم المضاربة اليومية": "🎯 فرص اليوم",
    "📊 الصفقات": "🚀 الإشارات النشطة",
    "♟️ التحليل المتقدم": "🧠 التحليل المتقدم",
    "💳 اشترك الآن / ترقية": "💳 اشتراك / ترقية",
    # Legacy live-screen label is accepted; bot_live_screen handles both labels.
    "📊 الشاشة اللحظية": "🖥️ الشاشة اللحظية",
}


def apply(base):
    original = base.handle
    base.MAIN_MENU = REFERENCE_MAIN_MENU
    bot_experience.MAIN_MENU = REFERENCE_MAIN_MENU

    def handle(chat_id, text, state):
        raw = (text or "").strip()
        # Intercept start/menu after every older wrapper so the displayed menu is
        # deterministic even if a feature module assigned its own MAIN_MENU.
        if raw in ("/start", "/menu", "🏠 القائمة الرئيسية"):
            state.pop("awaiting", None)
            bot_experience._send_keyboard(
                base,
                "📈 <b>ReFo . EGX Smart Trader</b>\n\n"
                "مساعد قرار وتحليل للسوق المصري.\nاختر من القائمة الرئيسية.\n\n"
                "⚠️ البيانات المتأخرة تظل معلّمة بوضوح ولا تُعامل كلحظية.",
                chat_id,
                REFERENCE_MAIN_MENU,
            )
            return True
        target = ALIASES.get(raw, raw)
        return original(chat_id, target, state)

    base.handle = handle
    return base


def self_test():
    rows = REFERENCE_MAIN_MENU["keyboard"]
    assert rows[0] == ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"]
    assert rows[1] == ["💳 اشترك الآن / ترقية"]
    assert ["📈 تحليل الأسهم", "♟️ التحليل المتقدم"] in rows
    assert ALIASES["📊 الصفقات"] == "🚀 الإشارات النشطة"
    assert ALIASES["📊 الشاشة اللحظية"] == "🖥️ الشاشة اللحظية"
    print("bot reference menu self-test: PASS")


if __name__ == "__main__":
    self_test()
