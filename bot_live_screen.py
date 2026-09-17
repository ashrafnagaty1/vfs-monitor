"""Reference-style Telegram launcher for the ReFo live terminal.

Kept as a small module so the WebApp entry flow is testable independently from
market analysis. It never supplies market data; it only opens the approved UI.
"""
import json
import os

WEBAPP_URL = os.environ.get("REFO_WEBAPP_URL", "https://refogx-pro.folkhero3.workers.dev/")


def apply(base):
    original = base.handle

    def handle(chat_id, text, state):
        text = (text or "").strip()
        if text != "📊 الشاشة اللحظية":
            return original(chat_id, text, state)
        state.pop("awaiting", None)
        markup = {"inline_keyboard": [[{"text": "🚀 فتح الشاشة اللحظية", "web_app": {"url": WEBAPP_URL}}]]}
        payload = {
            "chat_id": str(chat_id or base.CHAT_ID),
            "text": "🖥️ <b>ReFo EGX Terminal Pro</b>\n\nمنصة التداول والتحليل المتقدمة متاحة الآن.\nاضغط على الزر أدناه لفتح الشاشة اللحظية داخل تيليجرام.",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": json.dumps(markup, ensure_ascii=False),
        }
        if base.TOKEN:
            r = base.requests.post(f"{base.API}/sendMessage", data=payload, timeout=15)
            r.raise_for_status()
        return True

    base.handle = handle
    return base


def self_test():
    assert WEBAPP_URL.startswith("https://")
    print("bot live screen self-test: PASS")


if __name__ == "__main__":
    self_test()
