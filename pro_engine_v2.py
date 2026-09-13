"""EGX Pro Engine v2: enriched persisted snapshot with EGX session awareness."""
from datetime import datetime, timedelta, timezone
from pro_engine import (
    CAIRO, STATE_FILE, provider, load_json, save_state, scan, market_regime,
    build_watchlist, data_health_alert, event_alerts, scheduled_reports,
)
from egxpilot_provider import safe_stock_analysis


EGXPILOT_CACHE_MINUTES = 30
EGXPILOT_TOP_N = 5


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _egxpilot_compact(entry):
    if not entry or not entry.get("ok"):
        return {"ok": False, "error": (entry or {}).get("error")}
    data = entry.get("data") or {}
    scores = data.get("scores") or {}
    bias = data.get("bias") or {}
    signal = data.get("signal") or {}
    confidence = data.get("confidence") or {}
    regime = data.get("regime") or {}
    ind = data.get("keyIndicators") or {}
    macd = ind.get("macd") or {}
    return {
        "ok": True,
        "provider": "EGXpilot",
        "role": "SECONDARY_ANALYSIS_ONLY",
        "canonical_price": False,
        "fetched_at": entry.get("fetched_at"),
        "score": scores.get("composite"),
        "bias": bias.get("direction") or bias.get("label"),
        "signal": signal.get("type"),
        "signal_direction": signal.get("direction"),
        "confidence": confidence.get("score"),
        "regime": regime.get("label"),
        "rsi": ind.get("rsi"),
        "macd": macd.get("MACD"),
        "macd_signal": macd.get("signal"),
        "atr": ind.get("atr"),
        "vwap": ind.get("vwap"),
    }


def enrich_with_egxpilot(state, items):
    """Cache EGXpilot analysis for leading symbols without trusting its price feed."""
    root = state.get("egxpilot") if isinstance(state.get("egxpilot"), dict) else {}
    cache = root.get("analysis_by_symbol") if isinstance(root.get("analysis_by_symbol"), dict) else {}
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(minutes=EGXPILOT_CACHE_MINUTES)
    selected = [x.get("symbol") for x in items[:EGXPILOT_TOP_N] if x.get("symbol")]

    for symbol in selected:
        old = cache.get(symbol) if isinstance(cache.get(symbol), dict) else None
        old_at = _parse_dt((old or {}).get("fetched_at"))
        if old_at and old_at.tzinfo is None:
            old_at = old_at.replace(tzinfo=timezone.utc)
        if old and old_at and old_at >= cutoff:
            continue
        cache[symbol] = safe_stock_analysis(symbol)

    state["egxpilot"] = {
        "provider": "EGXpilot MCP",
        "endpoint": "https://egxpilot.com/api/mcp",
        "role": "SECONDARY_ANALYSIS_ONLY",
        "canonical_price": False,
        "price_note": "EGXpilot currentPrice is not used as the scanner/live quote source until independently verified.",
        "cache_minutes": EGXPILOT_CACHE_MINUTES,
        "updated_at": now_utc.isoformat(),
        "selected_symbols": selected,
        "analysis_by_symbol": cache,
    }
    return cache


def compact_detail(x, egxpilot_cache=None):
    symbol = x["symbol"]
    return {
        "symbol": symbol,
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
        "ema20": round(x.get("ema20", 0), 4),
        "ema50": round(x.get("ema50", 0), 4),
        "ema200": round(x.get("ema200", 0), 4),
        "golden": bool(x["golden"]),
        "golden_low": round(x["golden_low"], 4),
        "golden_high": round(x["golden_high"], 4),
        "breakout": bool(x["breakout"]),
        "setups": list(x.get("setups") or []),
        "why": list(x.get("why") or []),
        "quote_live": bool(x.get("quote_live")),
        "chart": list(x.get("chart") or []),
        "egxpilot": _egxpilot_compact((egxpilot_cache or {}).get(symbol)) if symbol in (egxpilot_cache or {}) else None,
    }


def egx_session(now):
    trading_day = now.weekday() not in (4, 5)
    mins = now.hour * 60 + now.minute
    pre_open = 9 * 60 + 30
    open_min = 10 * 60
    close_min = 14 * 60 + 30
    if not trading_day:
        status = "WEEKEND"
    elif pre_open <= mins < open_min:
        status = "PRE_MARKET"
    elif open_min <= mins <= close_min:
        status = "SESSION"
    else:
        status = "CLOSED"
    return {
        "status": status,
        "trading_day": trading_day,
        "heuristic": True,
        "pre_market_from": "09:30",
        "session_from": "10:00",
        "session_to": "14:30",
        "note": "Sunday-Thursday Cairo-time heuristic; official holidays are not yet calendar-checked.",
    }


def main():
    state = load_json(STATE_FILE, {})
    items = scan()
    now = datetime.now(CAIRO)
    session = egx_session(now)
    data_health_alert(state)
    if session["status"] == "SESSION":
        event_alerts(state, items)
    if session["trading_day"]:
        scheduled_reports(state, items)
    regime = market_regime(items)
    egxpilot_cache = enrich_with_egxpilot(state, items)
    state["pro_engine_snapshot"] = {
        "at": now.isoformat(),
        "count": len(items),
        "quote_mode": "LIVE" if provider.has_live_quote else "DELAYED_EVALUATION",
        "quote_source": provider.quote_source_name,
        "history_source": provider.history_source_name,
        "market_session": session,
        "market_regime": regime,
        "watchlist_next_session": build_watchlist(items),
        "secondary_analysis": {
            "provider": "EGXpilot",
            "role": "SECONDARY_ANALYSIS_ONLY",
            "canonical_price": False,
            "symbols": {s: _egxpilot_compact(egxpilot_cache.get(s)) for s in state["egxpilot"]["selected_symbols"]},
        },
        "top": [compact_detail(x, egxpilot_cache) for x in items[:12]],
        "details": [compact_detail(x, egxpilot_cache) for x in items],
    }
    save_state(state)


if __name__ == "__main__":
    main()
