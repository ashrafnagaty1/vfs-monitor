import bot_experience
import bot_reference_menu
import bot_live_screen


def main():
    rows = bot_reference_menu.REFERENCE_MAIN_MENU["keyboard"]
    assert rows[0] == ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"]
    assert rows[1] == ["💳 اشترك الآن / ترقية"]
    assert ["📈 أسهم المضاربة اليومية", "📊 الصفقات"] in rows
    assert ["📈 تحليل الأسهم", "♟️ التحليل المتقدم"] in rows
    assert bot_experience.LIVE_SCREEN_URL.startswith("https://")
    assert bot_live_screen.WEBAPP_URL.startswith("https://")
    assert "🖥️ الشاشة اللحظية" in bot_live_screen.LIVE_LABELS
    assert "📊 الشاشة اللحظية" in bot_live_screen.LIVE_LABELS
    assert bot_reference_menu.ALIASES["📈 تحليل الأسهم"] == "🔍 تحليل سهم"
    assert bot_reference_menu.ALIASES["📈 أسهم المضاربة اليومية"] == "🎯 فرص اليوم"
    assert bot_reference_menu.ALIASES["📊 الصفقات"] == "🚀 الإشارات النشطة"
    assert bot_reference_menu.ALIASES["♟️ التحليل المتقدم"] == "🧠 التحليل المتقدم"
    print("V11 runtime-hardening integration self-test: PASS")


if __name__ == "__main__":
    main()
