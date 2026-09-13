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
    progress_pct = 0.0
    if status == "ENTRY":
        stage = "ACTIVE"
        progress_pct = (price - trigger) / max(t3 - trigger, 1e-9) * 100
        if price >= t3:
            dynamic_stop = t2
            stage = "TARGET3"
        elif price >= t2:
            dynamic_stop = t1
            stage = "TARGET2_LOCK_1R"
        elif price >= t1:
            dynamic_stop = trigger
            stage = "TARGET1_BREAKEVEN"

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
        "progress_to_t3_pct": round(max(0.0, min(100.0, progress_pct)), 1),
        "score": candidate.get("score"),
        "confidence": candidate.get("confidence"),
        "liquidity_score": candidate.get("liquidity_score"),
    }


def _technical_by_symbol(snap):
    return {
        str(x.get("symbol", "")).upper(): x
        for x in (snap.get("top") or [])
        if x.get("symbol")
    }


def _make_alerts(state, plans, snap):
    """Create deduplicated lifecycle alerts. Delayed feeds only create WATCH-type alerts."""
    now = datetime.now(CAIRO).isoformat()
    previous = {
        str(x.get("symbol", "")).upper(): x
        for x in ((state.get("trade_lifecycle") or {}).get("plans") or [])
    }
    tech = _technical_by_symbol(snap)
    seen = state.setdefault("trade_alert_seen", {})
    history = list(state.get("trade_alerts") or [])
    emitted = []

    def emit(symbol, kind, level, text, discriminator):
        key = f"{symbol}:{kind}:{discriminator}"
        if key in seen:
            return
        seen[key] = now
        item = {
            "at": now,
            "symbol": symbol,
            "kind": kind,
            "level": level,
            "text": text,
        }
        emitted.append(item)
        history.append(item)

    for p in plans:
        symbol = str(p.get("symbol") or "").upper()
        if not symbol:
            continue
        t = tech.get(symbol, {})
        prev = previous.get(symbol, {})
        dist = float(p.get("distance_to_trigger_pct") or 999)
        score = float(p.get("score") or 0)
        liq = float(p.get("liquidity_score") or 0)
        rr = float(p.get("rr_to_t1_now") or 0)

        if p.get("status") == "WATCH":
            # These are watch alerts, never execution alerts on delayed data.
            if 0 <= dist <= 0.75 and score >= 68:
                emit(symbol, "NEAR_TRIGGER", "HIGH", f"{symbol} قريب جدًا من Trigger ({dist:.2f}%)", f"{round(dist,1)}")
            elif 0 <= dist <= 1.5 and score >= 65:
                emit(symbol, "APPROACHING_TRIGGER", "MEDIUM", f"{symbol} يقترب من Trigger ({dist:.2f}%)", f"{round(dist,1)}")
            if bool(t.get("golden")):
                emit(symbol, "GOLDEN_ZONE", "MEDIUM", f"{symbol} داخل Golden Zone الفنية", f"{round(float(t.get('golden_low') or 0),2)}:{round(float(t.get('golden_high') or 0),2)}")
            if score >= 80 and liq >= 80 and rr >= 1.4:
                emit(symbol, "STRONG_WATCH", "HIGH", f"{symbol} WATCH قوي: Score {score:.0f}, Liq {liq:.0f}, RR {rr:.2f}", f"{int(score)}:{int(liq)}")
            continue

        # Live-only lifecycle transition alerts.
        if p.get("status") == "ENTRY" and prev.get("status") != "ENTRY":
            emit(symbol, "ENTRY", "HIGH", f"{symbol} تم تأكيد ENTRY من مصدر Live", str(p.get("trigger")))
        if p.get("stage") != prev.get("stage"):
            stage = p.get("stage")
            if stage == "TARGET1_BREAKEVEN":
                emit(symbol, "TARGET1", "HIGH", f"{symbol} وصل T1 — نقل الوقف إلى التعادل", str(p.get("target1")))
            elif stage == "TARGET2_LOCK_1R":
                emit(symbol, "TARGET2", "HIGH", f"{symbol} وصل T2 — قفل 1R", str(p.get("target2")))
            elif stage == "TARGET3":
                emit(symbol, "TARGET3", "HIGH", f"{symbol} وصل T3", str(p.get("target3")))

    state["trade_alerts"] = history[-80:]
    state["trade_alert_seen"] = dict(list(seen.items())[-300:])
    return emitted


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

    new_alerts = _make_alerts(state, plans, snap)
    state["trade_lifecycle"] = {
        "updated_at": datetime.now(CAIRO).isoformat(),
        "quote_mode": quote_mode,
        "disclaimer": (
            "ENTRY states require a configured live quote provider. "
            "Delayed/evaluation data stays WATCH even if the last price is above trigger."
        ),
        "new_alerts_count": len(new_alerts),
        "plans": plans[:12],
    }
    return state


def self_test():
    base = {"symbol": "TEST", "trigger": 100, "stop": 95, "score": 80, "confidence": "HIGH", "liquidity_score": 90}
    delayed = build_trade_plan(base, current_price=101, quote_mode="DELAYED_EVALUATION")
    assert delayed["status"] == "WATCH"
    assert delayed["dynamic_stop"] == 95
    assert delayed["stage"] == "PRE_ENTRY"

    entry = build_trade_plan(base, current_price=101, quote_mode="LIVE")
    assert entry["status"] == "ENTRY"
    assert entry["target1"] == 105

    breakeven = build_trade_plan(base, current_price=105, quote_mode="LIVE")
    assert breakeven["stage"] == "TARGET1_BREAKEVEN"
    assert breakeven["dynamic_stop"] == 100

    locked = build_trade_plan(base, current_price=110, quote_mode="LIVE")
    assert locked["stage"] == "TARGET2_LOCK_1R"
    assert locked["dynamic_stop"] == 105

    target3 = build_trade_plan(base, current_price=115, quote_mode="LIVE")
    assert target3["stage"] == "TARGET3"
    assert target3["dynamic_stop"] == 110


if __name__ == "__main__":
    self_test()
    state = enrich_state(load_state())
    save_state(state)
    print(f"Trade lifecycle updated: {len(state.get('trade_lifecycle', {}).get('plans', []))} plans")
