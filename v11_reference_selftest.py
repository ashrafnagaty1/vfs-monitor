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
    assert "reference-clone-all-in-one" in worker
    assert 'import legacyWorker from "../src/tradingview_core_wrapper.js"' in worker
    print("reference clone all-in-one integration self-test: PASS")


if __name__ == "__main__":
    main()
