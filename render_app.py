import os
import threading
from flask import Flask, request, jsonify

import telegram_bot

app = Flask(__name__)
STATE_LOCK = threading.Lock()


def _authorized_chat(chat_id):
    return str(chat_id) == str(telegram_bot.CHAT_ID)


def _load_state():
    return telegram_bot.load_json(telegram_bot.STATE_FILE, {})


def _save_state(state):
    telegram_bot.save_json(telegram_bot.STATE_FILE, state)


@app.get("/")
def health():
    return jsonify({"ok": True, "service": "EGX Smart Scanner Telegram webhook"})


@app.get("/health")
def health2():
    return jsonify({"ok": True})


@app.post("/telegram")
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text")

    if not chat_id or not text:
        return jsonify({"ok": True, "ignored": True})

    if not _authorized_chat(chat_id):
        return jsonify({"ok": True, "ignored": True})

    with STATE_LOCK:
        state = _load_state()
        telegram_bot.handle(str(chat_id), text, state)
        _save_state(state)

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
