import os
import threading

import requests
from flask import Flask, jsonify, request

# Reuse the exact V11 wrapper order. Importing always_on_bot does not start polling.
import always_on_bot

bot = always_on_bot.telegram_bot
app = Flask(__name__)
_lock = threading.Lock()
_registered = False


def _register_webhook():
    global _registered
    if _registered or not bot.TOKEN:
        return
    base = (os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    if not base:
        return
    payload = {
        "url": base + "/telegram/webhook",
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
    }
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if secret:
        payload["secret_token"] = secret
    r = requests.post(f"{bot.API}/setWebhook", json=payload, timeout=15)
    r.raise_for_status()
    _registered = True


@app.get("/")
@app.get("/health")
def health():
    try:
        _register_webhook()
        return jsonify({
            "ok": True,
            "service": "ReFo . EGX Smart Trader",
            "mode": "telegram-webhook",
            "webapp": os.environ.get("REFO_WEBAPP_URL", "https://refogx-pro.folkhero3.workers.dev/"),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": type(exc).__name__}), 503


@app.post("/telegram/webhook")
def telegram_webhook():
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", ""))
    text = message.get("text")
    if not chat_id or not text:
        return jsonify({"ok": True})

    # Keep the current single-user safety gate used by the polling bot.
    if bot.CHAT_ID and chat_id != str(bot.CHAT_ID):
        return jsonify({"ok": True})

    with _lock:
        state = bot.load_json(bot.STATE_FILE, {})
        update_id = int(update.get("update_id", 0) or 0)
        last_id = int(state.get("telegram_webhook_update_id", -1))
        if update_id and update_id <= last_id:
            return jsonify({"ok": True, "duplicate": True})
        bot.handle(chat_id, text, state)
        if update_id:
            state["telegram_webhook_update_id"] = update_id
        bot.save_json(bot.STATE_FILE, state)

    return jsonify({"ok": True})


# Gunicorn imports the module before serving requests; register once when the
# Render URL is already available. Failure is non-fatal and /health retries it.
try:
    _register_webhook()
except Exception:
    pass
