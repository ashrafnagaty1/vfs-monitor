import os
import sys
import time
import signal
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import telegram_bot
import bot_experience
import bot_watchlist
import bot_alerts
import bot_smart_money
import bot_opportunities
import bot_market

telegram_bot = bot_experience.apply(telegram_bot)
telegram_bot = bot_watchlist.apply(telegram_bot)
telegram_bot = bot_alerts.apply(telegram_bot)
telegram_bot = bot_smart_money.apply(telegram_bot)
telegram_bot = bot_opportunities.apply(telegram_bot)
telegram_bot = bot_market.apply(telegram_bot)

CAIRO = ZoneInfo("Africa/Cairo")
RUNNING = True

POLL_SLEEP_SECONDS = float(os.environ.get("BOT_POLL_SLEEP_SECONDS", "1.0"))
ENGINE_INTERVAL_SECONDS = int(os.environ.get("ENGINE_INTERVAL_SECONDS", "300"))
HEALTH_INTERVAL_SECONDS = int(os.environ.get("HEALTH_INTERVAL_SECONDS", "1800"))


def log(message):
    stamp = datetime.now(CAIRO).isoformat(timespec="seconds")
    print(f"[{stamp}] {message}", flush=True)


def stop_handler(signum, frame):
    global RUNNING
    RUNNING = False
    log(f"shutdown requested by signal {signum}")


def run_script(path):
    try:
        result = subprocess.run(
            [sys.executable, path],
            check=False,
            timeout=240,
            env=os.environ.copy(),
        )
        if result.returncode != 0:
            log(f"{path} exited with code {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"{path} timed out")
        return False
    except Exception as exc:
        log(f"{path} failed: {type(exc).__name__}: {exc}")
        return False


def main():
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    if not telegram_bot.TOKEN or not telegram_bot.CHAT_ID:
        raise RuntimeError("TOKEN and CHAT_ID environment variables are required")

    log("ReFo EGX always-on Telegram service started")
    log("Telegram polling is continuous; professional engine remains periodic")

    next_engine = 0.0
    next_health = 0.0
    error_streak = 0

    while RUNNING:
        now = time.monotonic()

        # Fast interactive path: consume Telegram updates continuously.
        try:
            telegram_bot.main()
            error_streak = 0
        except Exception as exc:
            error_streak += 1
            delay = min(30.0, max(2.0, 2 ** min(error_streak, 4)))
            log(f"telegram polling error: {type(exc).__name__}: {exc}; retry in {delay:.0f}s")
            time.sleep(delay)
            continue

        # Heavy market analysis stays decoupled from button response latency.
        if now >= next_engine:
            run_script("pro_engine.py")
            next_engine = time.monotonic() + ENGINE_INTERVAL_SECONDS

        # Data-source health is slower because it is diagnostic, not interactive.
        if now >= next_health:
            run_script("data_health.py")
            next_health = time.monotonic() + HEALTH_INTERVAL_SECONDS

        time.sleep(max(0.2, POLL_SLEEP_SECONDS))

    log("ReFo EGX always-on Telegram service stopped")


if __name__ == "__main__":
    main()
