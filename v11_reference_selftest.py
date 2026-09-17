import bot_experience


def main():
    rows = bot_experience.MAIN_MENU["keyboard"]
    assert rows[0] == ["📊 الشاشة اللحظية", "🤖 المساعد الذكي"]
    assert ["📈 أسهم المضاربة اليومية", "📊 الصفقات"] in rows
    assert ["📈 تحليل الأسهم", "🧠 التحليل المتقدم"] in rows
    assert bot_experience.LIVE_SCREEN_URL.startswith("https://")
    assert "refogx-pro" in bot_experience.LIVE_SCREEN_URL or "REFO_WEBAPP_URL" in str(bot_experience.LIVE_SCREEN_URL)
    print("V11 reference integration self-test: PASS")


if __name__ == "__main__":
    main()
