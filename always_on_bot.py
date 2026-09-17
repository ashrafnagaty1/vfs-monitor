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
import bot_gann
import bot_harmonic
import bot_elliott
import bot_temporal
import bot_opportunities
import bot_market
import bot_personal_portfolio
import bot_assistant
import bot_reports

telegram_bot = bot_experience.apply(telegram_bot)
telegram_bot = bot_watchlist.apply(telegram_bot)
telegram_bot = bot_alerts.apply(telegram_bot)
telegram_bot = bot_smart_money.apply(telegram_bot)
telegram_bot = bot_gann.apply(telegram_bot)
telegram_bot = bot_harmonic.apply(telegram_bot)
telegram_bot = bot_elliott.apply(telegram_bot)
telegram_bot = bot_temporal.apply(telegram_bot)
telegram_bot = bot_opportunities.apply(telegram_bot)
telegram_bot = bot_market.apply(telegram_bot)
telegram_bot = bot_personal_portfolio.apply(telegram_bot)
telegram_bot = bot_assistant.apply(telegram_bot)
telegram_bot = bot_reports.apply(telegram_bot)

CAIRO = ZoneInfo("Africa/Cairo")
RUNNING = True
POLL_SLEEP_SECONDS = float(os.environ.get("BOT_POLL_SLEEP_SECONDS", "1.0"))
ENGINE_INTERVAL_SECONDS = int(os.environ.get("ENGINE_INTERVAL_SECONDS", "300"))
HEALTH_INTERVAL_SECONDS = int(os.environ.get("HEALTH_INTERVAL_SECONDS", "1800"))
ENGINE_SCRIPT = os.environ.get("REFO_ENGINE_SCRIPT", "pro_engine_v2.py")


def log(message):
    print(f"[{datetime.now(CAIRO).isoformat(timespec='seconds')}] {message}", flush=True)

def stop_handler(signum, frame):
    global RUNNING
    RUNNING=False;log(f"shutdown requested by signal {signum}")

def run_script(path):
    try:
        result=subprocess.run([sys.executable,path],check=False,timeout=240,env=os.environ.copy())
        if result.returncode!=0:log(f"{path} exited with code {result.returncode}")
        return result.returncode==0
    except subprocess.TimeoutExpired:log(f"{path} timed out");return False
    except Exception as exc:log(f"{path} failed: {type(exc).__name__}: {exc}");return False

def main():
    signal.signal(signal.SIGTERM,stop_handler);signal.signal(signal.SIGINT,stop_handler)
    if not telegram_bot.TOKEN or not telegram_bot.CHAT_ID:raise RuntimeError("TOKEN and CHAT_ID environment variables are required")
    log("ReFo . EGX Smart Trader V11 always-on Telegram service started")
    log(f"Telegram polling continuous; snapshot engine={ENGINE_SCRIPT} every {ENGINE_INTERVAL_SECONDS}s")
    next_engine=0.0;next_health=0.0;error_streak=0
    while RUNNING:
        now=time.monotonic()
        try:telegram_bot.main();error_streak=0
        except Exception as exc:
            error_streak+=1;delay=min(30.0,max(2.0,2**min(error_streak,4)));log(f"telegram polling error: {type(exc).__name__}: {exc}; retry in {delay:.0f}s");time.sleep(delay);continue
        if now>=next_engine:run_script(ENGINE_SCRIPT);next_engine=time.monotonic()+ENGINE_INTERVAL_SECONDS
        if now>=next_health:run_script("data_health.py");next_health=time.monotonic()+HEALTH_INTERVAL_SECONDS
        time.sleep(max(.2,POLL_SLEEP_SECONDS))
    log("ReFo . EGX Smart Trader V11 always-on Telegram service stopped")

if __name__=="__main__":main()
