import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data_provider import provider

OUT = "data_health.json"
CAIRO = ZoneInfo("Africa/Cairo")
SYMBOLS = ["COMI", "ABUK", "SWDY", "FWRY", "TMGH", "EAST"]


def load():
    try:
        with open(OUT, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(data):
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def due(previous):
    raw = previous.get("checked_at")
    if not raw:
        return True
    try:
        before = datetime.fromisoformat(raw)
        if before.tzinfo is None:
            before = before.replace(tzinfo=CAIRO)
        return datetime.now(CAIRO) - before >= timedelta(minutes=55)
    except Exception:
        return True


def main():
    previous = load()
    if not due(previous):
        print("Data health check skipped: recent result exists")
        return

    # The shared demo quote endpoint is quota-limited, so only one symbol is checked
    # per hourly health cycle. A real feed can safely expand this later.
    idx = int(previous.get("rotation_index", -1)) + 1
    symbol = SYMBOLS[idx % len(SYMBOLS)]
    now = datetime.now(CAIRO)

    result = {
        "checked_at": now.isoformat(),
        "rotation_index": idx,
        "mode": "LIVE" if provider.has_live_quote else "DELAYED_EVALUATION",
        "quote_source": provider.quote_source_name,
        "history_source": provider.history_source_name,
        "symbol": symbol,
        "status": "UNKNOWN",
        "message": "",
    }

    try:
        h = provider.quote_health(symbol)
        result["quote_price"] = h["quote_price"]
        result["daily_close"] = h["daily_close"]
        result["gap_pct"] = round(h["gap_pct"], 4)
        result["bid"] = h.get("bid")
        result["ask"] = h.get("ask")
        result["is_live"] = bool(h["is_live"])

        # This score is about plumbing/consistency, not whether market data is truly real-time.
        gap = abs(float(h["gap_pct"]))
        if provider.has_live_quote:
            result["status"] = "GREEN" if gap <= 15 else "AMBER"
            result["message"] = "Live-provider request succeeded. Verify exchange entitlement/latency separately."
        else:
            result["status"] = "AMBER" if gap <= 15 else "RED"
            result["message"] = "Fallback quote/history sources responded, but they are not execution-grade live EGX data."
    except Exception as exc:
        result["status"] = "RED"
        result["message"] = f"Data source check failed: {type(exc).__name__}: {exc}"

    save(result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
