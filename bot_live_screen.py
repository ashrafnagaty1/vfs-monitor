"""Reference-style Telegram launcher for the ReFo live terminal.

This layer is applied last. It opens the approved WebApp only; it does not
pretend that TradingView iframe data are ReFo market-feed data.
"""
import json
import os

import bot_reference_menu

WEBAPP_URL = os.environ.get("REFO_WEBAPP_URL", "https://refogx-pro.folkhero3.workers.dev/")
LIVE_LABELS = {"🖥️ الشاشة اللحظية", "📊 الشاشة اللحظية"}


def apply(base):
    original = base.handle

    def handle(chat_id, text, state):
        text = (text or "").strip()
        if text not in LIVE_LABELS:
            return original(chat_id, text, state)
        state.pop("awaiting", None)
        markup = {"inline_keyboard": [[{"text": "🚀 فتح الشاشة اللحظية", "web_app": {"url": WEBAPP_URL}}]]}
        payload = {
            "chat_id": str(chat_id or base.CHAT_ID),
            "text": "🖥️ <b>ReFo EGX Terminal Pro</b>\n\n"
                    "منصة التداول والتحليل المتقدمة متاحة الآن.\n"
                    "اضغط على الزر أدناه لفتح الشاشة اللحظية داخل تيليجرام.\n\n"
                    "📡 TradingView للشارت، وبيانات ReFo خارج الشارت تعرض مصدرها وحالتها بوضوح.",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": json.dumps(markup, ensure_ascii=False),
        }
        if base.TOKEN:
            r = base.requests.post(f"{base.API}/sendMessage", data=payload, timeout=15)
            r.raise_for_status()
            # Telegram cannot attach inline WebApp and persistent reply keyboard to
            # the same message, so restore the canonical menu in a second message.
            bot_reference_menu.bot_experience._send_keyboard(
                base,
                "اختر أداة أخرى من القائمة عند الحاجة.",
                chat_id,
                bot_reference_menu.REFERENCE_MAIN_MENU,
            )
        return True

    base.handle = handle
    return base


def self_test():
    assert WEBAPP_URL.startswith("https://")
    assert "🖥️ الشاشة اللحظية" in LIVE_LABELS
    assert "📊 الشاشة اللحظية" in LIVE_LABELS
    print("bot live screen self-test: PASS")


if __name__ == "__main__":
    self_test()
