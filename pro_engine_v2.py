"""EGX Pro Engine v2: enriched persisted snapshot with EGX session awareness."""
from datetime import datetime
from pro_engine import (
    CAIRO, STATE_FILE, provider, load_json, save_state, scan, market_regime,
    build_watchlist, data_health_alert, event_alerts, scheduled_reports,
)


def compact_detail(x):
    return {
        "symbol": x["symbol"],
        "price": round(x["price"], 4),
        "close_price": round(x["close_price"], 4),
        "score": x["score"],
        "confidence": x["confidence"],
        "rsi": round(x["rsi"], 2),
        "adx": round(x["adx"], 2),
        "mfi": round(x["mfi"], 2),
        "volume_ratio": round(x["vr"], 2),
        "liquidity_score": round(x["liquidity_score"], 2),
        "volatility_pct": round(x["volatility_pct"], 2),
        "momentum_5d": round(x["mom5"], 2),
        "momentum_20d": round(x["mom20"], 2),
        "resistance_20": round(x["res20"], 4),
        "resistance_50": round(x["res50"], 4),
        "support_20": round(x["sup20"], 4),
        "support_50": round(x["sup50"], 4),
        "stop": round(x["stop"], 4),
        "target1": round(x["t1"], 4),
        "target2": round(x["t2"], 4),
        "target3": round(x["t3"], 4),
        "golden": bool(x["golden"]),
        "golden_low": round(x["golden_low"], 4),
        "golden_high": round(x["golden_high"], 4),
        "breakout": bool(x["breakout"]),
        "setups": list(x.get("setups") or []),
        "why": list(x.get("why") or []),
        "quote_live": bool(x.get("quote_live")),
    }


def egx_session(now):
    # Python weekday: Mon=0 ... Fri=4, Sat=5, Sun=6. EGX trades Sun-Thu.
    trading_day = now.weekday() not in (4, 5)
    mins = now.hour * 60 + now.minute
    if not trading_day:
        status = "WEEKEND"
    elif mins < 600:
        status = "PRE_MARKET"
    elif mins <= 870:
        status = "SESSION"
    else:
        status = "CLOSED"
    return {
        "status": status,
        "trading_day": trading_day,
        "heuristic": True,
        "note": "Sunday-Thursday session heuristic; official holidays are not yet calendar-checked.",
    }


def main():
    state = load_json(STATE_FILE, {})
    items = scan()
    now = datetime.now(CAIRO)
    session = egx_session(now)

    data_health_alert(state)
    # Old pro_engine helpers assume Mon-Fri. Gate them here so Friday/Saturday never fire.
    if session["trading_day"]:
        event_alerts(state, items)
        scheduled_reports(state, items)

    regime = market_regime(items)
    state["pro_engine_snapshot"] = {
        "at": now.isoformat(),
        "count": len(items),
        "quote_mode": "LIVE" if provider.has_live_quote else "DELAYED_EVALUATION",
        "quote_source": provider.quote_source_name,
        "history_source": provider.history_source_name,
        "market_session": session,
        "market_regime": regime,
        "watchlist_next_session": build_watchlist(items),
        "top": [compact_detail(x) for x in items[:12]],
        "details": [compact_detail(x) for x in items],
    }
    save_state(state)


if __name__ == "__main__":
    main()
