import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data_provider import DataProviderError, provider

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
        # The public demo quote service has a very small shared quota. When no
        # licensed live feed is configured, do not burn quota every hour merely
        # for a plumbing health check.
        interval = timedelta(minutes=55 if provider.has_live_quote else 360)
        return datetime.now(CAIRO) - before >= interval
    except Exception:
        return True


def _history_only_health(symbol, result, reason):
    """Verify the historical fallback when the evaluation quote feed is throttled.

    A demo quota exhaustion is a feed-availability degradation, not proof that all
    market data is broken. Keep the status AMBER when Yahoo daily history remains
    available, and reserve RED for cases where the fallback is unavailable too.
    """
    rows = provider.history(symbol, period="1mo", interval="1d")
    last = rows[-1]
    result["status"] = "AMBER"
    result["quote_available"] = False
    result["history_available"] = True
    result["daily_close"] = float(last["close"])
    result["degraded_reason"] = reason
    result["message"] = (
        "Demo quote quota is exhausted, but Yahoo EGX daily history is healthy. "
        "System remains evaluation-only; no ENTRY should be generated without a Live Feed."
    )


def main():
    previous = load()
    if not due(previous):
        print("Data health check skipped: recent result exists")
        return

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
        "quote_available": None,
        "history_available": None,
    }

    try:
        h = provider.quote_health(symbol)
        result["quote_price"] = h["quote_price"]
        result["daily_close"] = h["daily_close"]
        result["gap_pct"] = round(h["gap_pct"], 4)
        result["bid"] = h.get("bid")
        result["ask"] = h.get("ask")
        result["is_live"] = bool(h["is_live"])
        result["quote_available"] = True
        result["history_available"] = True

        gap = abs(float(h["gap_pct"]))
        if provider.has_live_quote:
            result["status"] = "GREEN" if gap <= 15 else "AMBER"
            result["message"] = "Live-provider request succeeded. Verify exchange entitlement/latency separately."
        else:
            result["status"] = "AMBER" if gap <= 15 else "RED"
            result["message"] = "Fallback quote/history sources responded, but they are not execution-grade live EGX data."
    except DataProviderError as exc:
        if str(exc) == "DEMO_RATE_LIMIT" and not provider.has_live_quote:
            try:
                _history_only_health(symbol, result, "DEMO_RATE_LIMIT")
            except Exception as fallback_exc:
                result["status"] = "RED"
                result["quote_available"] = False
                result["history_available"] = False
                result["message"] = (
                    f"Demo quote quota exhausted and historical fallback failed: "
                    f"{type(fallback_exc).__name__}: {fallback_exc}"
                )
        else:
            result["status"] = "RED"
            result["message"] = f"Data source check failed: {type(exc).__name__}: {exc}"
    except Exception as exc:
        result["status"] = "RED"
        result["message"] = f"Data source check failed: {type(exc).__name__}: {exc}"

    save(result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
