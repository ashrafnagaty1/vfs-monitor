import pathlib

p = pathlib.Path("cloudflare/telegram_webhook_worker.js").read_text(encoding="utf-8")
assert "🖥️ الشاشة اللحظية" in p
assert "🚀 فتح الشاشة اللحظية" in p
assert "/telegram/webhook" in p
assert "/telegram/register" in p
assert "TELEGRAM_BOT_TOKEN" in p
assert "TELEGRAM_WEBHOOK_SECRET" in p
assert "https://refogx-pro.folkhero3.workers.dev/" in p
assert "TradingView" in p
print("cloudflare telegram webhook contract: PASS")
