import bot_experience
import bot_reference_menu
import bot_live_screen


def main():
    rows = bot_reference_menu.REFERENCE_MAIN_MENU["keyboard"]
    assert rows[0] == ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"]
    assert rows[1] == ["💳 اشترك الآن / ترقية"]
    assert ["📈 أسهم المضاربة اليومية", "📊 الصفقات"] in rows
    assert ["📈 تحليل الأسهم", "♟️ التحليل المتقدم"] in rows
    assert ["💼 المحافظ والتنبيهات", "👤 حسابي"] in rows
    trades = bot_reference_menu.TRADES_MENU["keyboard"]
    assert trades[0] == ["📊 صفقات مفتوحة", "✅ تحقق الهدف الأول", "✅ تحقق الهدف الثاني"]
    assert trades[1] == ["✅ تحقق الهدف الثالث", "⬅️ العودة للقائمة الرئيسية"]
    assert bot_experience.LIVE_SCREEN_URL.startswith("https://")
    assert bot_live_screen.WEBAPP_URL.startswith("https://")
    assert "🖥️ الشاشة اللحظية" in bot_live_screen.LIVE_LABELS
    assert "📊 الشاشة اللحظية" in bot_live_screen.LIVE_LABELS
    assert bot_reference_menu.ALIASES["📈 تحليل الأسهم"] == "🔍 تحليل سهم"
    assert bot_reference_menu.ALIASES["📈 أسهم المضاربة اليومية"] == "🎯 فرص اليوم"
    assert bot_reference_menu.ALIASES["♟️ التحليل المتقدم"] == "🧠 التحليل المتقدم"
    worker = open("cloudflare/composite_worker.js", encoding="utf-8").read()
    for label in [
        "🖥️ الشاشة اللحظية", "🤖 المساعد الذكي", "📈 أسهم المضاربة اليومية",
        "📊 الصفقات", "📈 تحليل الأسهم", "♟️ التحليل المتقدم",
        "🔮 التوقع الزمني", "🌀 التوقع الفركتالي", "📐 تحليل جان",
        "🦋 أنماط الهارمونيك", "🌊 موجات إليوت", "💰 Smart Money",
        "🎯 قناص EGX V2", "💼 المحافظ والتنبيهات", "👤 حسابي"
    ]:
        assert label in worker
    assert "reference-clone-completion-v4" in worker
    for label in ["📊 السوق","💵 التقارير المالية","💧 السيولة","📈 مؤشرات EGX","📄 تقرير سهم","⚖️ مقارنة سهمين","🏭 تحليل القطاع","🧮 القيمة العادلة","📉 أسهم تحت القيمة"]:
        assert label in worker
    assert "Fundamentals" in worker
    for label in ["📊 ملخص السوق","🎯 الأفضل اليوم","🔮 فرص الغد","📈 أعلى صاعد / خاسر","🤝 توافق التحليلات","🏭 القطاعات","🎯 متابعة الفرص","🧮 حاسبة المخاطر","💼 نظرة على المحفظة"]:
        assert label in worker
    assert "eventOf(x,stage)" in worker
    for label in ["💳 اشتراك / تجديد","👤 اشتراكي","🔗 رابط الإحالة","📊 إحصائيات الإحالة","👥 ادع صديق","🎟️ أكواد الخصم","🔔 إعدادات الإشعارات","📊 شارت السهم","🎯 متابعة الخطة","🚨 تنبيه سعر"]:
        assert label in worker
    assert 'allowed_updates:["message","callback_query"]' in worker
    assert 'import legacyWorker from "../src/tradingview_core_wrapper.js"' in worker
    print("reference clone all-in-one integration self-test: PASS")


if __name__ == "__main__":
    main()
