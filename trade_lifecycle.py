import json
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_FILE = "state.json"
CAIRO = ZoneInfo("Africa/Cairo")


def load_state(path=STATE_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state, path=STATE_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def build_trade_plan(candidate, current_price=None, quote_mode="DELAYED_EVALUATION"):
    """Build a deterministic WATCH/ENTRY plan without pretending delayed data is live."""
    trigger = float(candidate.get("trigger") or 0)
    initial_stop = float(candidate.get("stop") or 0)
    price = float(current_price if current_price is not None else trigger)

    if trigger <= 0 or initial_stop <= 0 or initial_stop >= trigger:
        return None

    risk = trigger - initial_stop
    t1 = trigger + risk
    t2 = trigger + 2 * risk
    t3 = trigger + 3 * risk
    rr_now = (t1 - price) / max(price - initial_stop, 1e-9) if price > initial_stop else 0.0

    is_live = quote_mode == "LIVE"
    distance_pct = (trigger - price) / trigger * 100

    # Delayed/evaluation feeds never produce an ENTRY state.
    status = "ENTRY" if is_live and price >= trigger else "WATCH"
    activation = "CONFIRMED_LIVE" if status == "ENTRY" else "WAIT_TRIGGER"

    dynamic_stop = initial_stop
    stage = "PRE_ENTRY"
    if status == "ENTRY":
        stage = "ACTIVE"
        if price >= t2:
            dynamic_stop = t1
            stage = "LOCK_1R"
        elif price >= t1:
            dynamic_stop = trigger
            stage = "BREAKEVEN"

    return {
        "symbol": candidate.get("symbol"),
        "status": status,
        "activation": activation,
        "quote_mode": quote_mode,
        "price": round(price, 4),
        "trigger": round(trigger, 4),
        "distance_to_trigger_pct": round(distance_pct, 2),
        "initial_stop": round(initial_stop, 4),
        "dynamic_stop": round(dynamic_stop, 4),
        "target1": round(t1, 4),
        "target2": round(t2, 4),
        "target3": round(t3, 4),
        "risk_per_share": round(risk, 4),
        "rr_to_t1_now": round(rr_now, 2),
        "stage": stage,
        "score": candidate.get("score"),
        "confidence": candidate.get("confidence"),
        "liquidity_score": candidate.get("liquidity_score"),
    }


def enrich_state(state):
    snap = state.get("pro_engine_snapshot") or {}
    watchlist = snap.get("watchlist_next_session") or []
    quote_mode = snap.get("quote_mode") or "DELAYED_EVALUATION"
    top_prices = {
        x.get("symbol"): x.get("price")
        for x in (snap.get("top") or [])
        if x.get("symbol") and x.get("price") is not None
    }

    plans = []
    for candidate in watchlist:
        plan = build_trade_plan(
            candidate,
            current_price=top_prices.get(candidate.get("symbol"), candidate.get("trigger")),
            quote_mode=quote_mode,
        )
        if plan:
            plans.append(plan)

    plans.sort(
        key=lambda x: (
            1 if x["status"] == "ENTRY" else 0,
            float(x.get("score") or 0),
            float(x.get("liquidity_score") or 0),
        ),
        reverse=True,
    )

    state["trade_lifecycle"] = {
        "updated_at": datetime.now(CAIRO).isoformat(),
        "quote_mode": quote_mode,
        "disclaimer": (
            "ENTRY states require a configured live quote provider. "
            "Delayed/evaluation data stays WATCH even if the last price is above trigger."
        ),
        "plans": plans[:12],
    }
    return state


def self_test():
    base = {"symbol": "TEST", "trigger": 100, "stop": 95, "score": 80, "confidence": "HIGH"}
    delayed = build_trade_plan(base, current_price=101, quote_mode="DELAYED_EVALUATION")
    assert delayed["status"] == "WATCH"
    assert delayed["dynamic_stop"] == 95

    entry = build_trade_plan(base, current_price=101, quote_mode="LIVE")
    assert entry["status"] == "ENTRY"
    assert entry["target1"] == 105

    breakeven = build_trade_plan(base, current_price=105, quote_mode="LIVE")
    assert breakeven["stage"] == "BREAKEVEN"
    assert breakeven["dynamic_stop"] == 100

    locked = build_trade_plan(base, current_price=110, quote_mode="LIVE")
    assert locked["stage"] == "LOCK_1R"
    assert locked["dynamic_stop"] == 105


if __name__ == "__main__":
    self_test()
    state = enrich_state(load_state())
    save_state(state)
    print(f"Trade lifecycle updated: {len(state.get('trade_lifecycle', {}).get('plans', []))} plans")
