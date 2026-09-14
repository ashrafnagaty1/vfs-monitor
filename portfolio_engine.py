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


def _r_multiple(entry, exit_price, risk):
    if risk <= 0:
        return 0.0
    return (exit_price - entry) / risk


def _metrics(closed):
    total = len(closed)
    wins = sum(1 for x in closed if float(x.get("r_multiple") or 0) > 0)
    losses = sum(1 for x in closed if float(x.get("r_multiple") or 0) < 0)
    breakeven = total - wins - losses
    total_r = sum(float(x.get("r_multiple") or 0) for x in closed)
    avg_r = total_r / total if total else 0.0
    win_rate = wins / total * 100 if total else 0.0
    best_r = max((float(x.get("r_multiple") or 0) for x in closed), default=0.0)
    worst_r = min((float(x.get("r_multiple") or 0) for x in closed), default=0.0)
    return {
        "closed_trades": total,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate_pct": round(win_rate, 1),
        "total_r": round(total_r, 2),
        "avg_r": round(avg_r, 2),
        "best_r": round(best_r, 2),
        "worst_r": round(worst_r, 2),
    }


def _position_key(item):
    return str(item.get("signal_id") or item.get("symbol") or "").upper()


def _append_event(events, *, now, signal_id, symbol, event, price=None, detail=None):
    key = f"{signal_id}:{event}:{price}:{detail or ''}"
    if any(x.get("event_key") == key for x in events[-100:]):
        return
    events.append({
        "event_key": key,
        "at": now,
        "signal_id": signal_id,
        "symbol": symbol,
        "event": event,
        "price": price,
        "detail": detail,
    })


def update_portfolio(state):
    now = datetime.now(CAIRO).isoformat()
    lifecycle = state.get("trade_lifecycle") or {}
    plans = lifecycle.get("plans") or []
    quote_mode = lifecycle.get("quote_mode") or "DELAYED_EVALUATION"

    old = state.get("signal_portfolio") or {}
    open_positions = {
        _position_key(x): x
        for x in (old.get("open_positions") or [])
        if _position_key(x)
    }
    closed = list(old.get("closed_trades") or [])
    events = list(old.get("events") or [])
    closed_signal_ids = {
        str(x.get("signal_id") or "")
        for x in closed
        if x.get("signal_id")
    }

    # Only confirmed LIVE ENTRY states are admitted. Delayed WATCH data never creates trades.
    if quote_mode == "LIVE":
        for p in plans:
            symbol = str(p.get("symbol") or "").upper()
            signal_id = str(p.get("signal_id") or symbol)
            if not symbol or not signal_id:
                continue
            key = signal_id.upper()

            # A closed signal ID is terminal. It cannot silently reopen while the same
            # lifecycle plan remains in the scanner. A genuinely new setup gets a new ID.
            if p.get("status") == "ENTRY" and key not in open_positions and signal_id not in closed_signal_ids:
                trigger = float(p.get("trigger") or 0)
                risk = float(p.get("risk_per_share") or 0)
                if trigger > 0 and risk > 0:
                    open_positions[key] = {
                        "signal_id": signal_id,
                        "symbol": symbol,
                        "opened_at": now,
                        "entry_price": round(trigger, 4),
                        "risk_per_share": round(risk, 4),
                        "initial_stop": p.get("initial_stop"),
                        "dynamic_stop": p.get("dynamic_stop"),
                        "target1": p.get("target1"),
                        "target2": p.get("target2"),
                        "target3": p.get("target3"),
                        "last_price": p.get("price"),
                        "stage": p.get("stage"),
                        "lifecycle_status": p.get("lifecycle_status") or "ENTRY",
                        "score": p.get("score"),
                        "confidence": p.get("confidence"),
                    }
                    _append_event(
                        events,
                        now=now,
                        signal_id=signal_id,
                        symbol=symbol,
                        event="ENTRY",
                        price=round(trigger, 4),
                        detail="Confirmed from LIVE quote mode",
                    )

            pos = open_positions.get(key)
            if not pos:
                continue

            previous_stage = pos.get("stage")
            pos["last_price"] = p.get("price")
            pos["dynamic_stop"] = p.get("dynamic_stop")
            pos["stage"] = p.get("stage")
            pos["lifecycle_status"] = p.get("lifecycle_status") or pos.get("lifecycle_status")
            entry = float(pos.get("entry_price") or 0)
            risk = float(pos.get("risk_per_share") or 0)
            last_price = float(p.get("price") or 0)
            pos["unrealized_r"] = round(_r_multiple(entry, last_price, risk), 2)

            if p.get("stage") != previous_stage:
                stage_event = {
                    "TARGET1_BREAKEVEN": "T1",
                    "TARGET2_LOCK_1R": "T2",
                    "TARGET3": "T3",
                }.get(p.get("stage"))
                if stage_event:
                    _append_event(
                        events,
                        now=now,
                        signal_id=signal_id,
                        symbol=symbol,
                        event=stage_event,
                        price=p.get(f"target{stage_event[-1]}") if stage_event[-1].isdigit() else last_price,
                        detail=f"Dynamic stop: {p.get('dynamic_stop')}",
                    )

            close_reason = None
            exit_price = None
            if p.get("stage") == "TARGET3":
                close_reason = "T3"
                exit_price = float(p.get("target3") or last_price)
            elif last_price > 0 and float(p.get("dynamic_stop") or 0) > 0 and last_price <= float(p.get("dynamic_stop") or 0):
                close_reason = "STOP_HIT"
                exit_price = float(p.get("dynamic_stop") or last_price)

            if close_reason:
                trade = dict(pos)
                trade.update({
                    "closed_at": now,
                    "exit_price": round(exit_price, 4),
                    "close_reason": close_reason,
                    "lifecycle_status": "CLOSED",
                    "r_multiple": round(_r_multiple(entry, exit_price, risk), 2),
                })
                closed.append(trade)
                closed_signal_ids.add(signal_id)
                _append_event(
                    events,
                    now=now,
                    signal_id=signal_id,
                    symbol=symbol,
                    event="CLOSED",
                    price=round(exit_price, 4),
                    detail=close_reason,
                )
                open_positions.pop(key, None)

    open_list = sorted(open_positions.values(), key=lambda x: x.get("opened_at", ""), reverse=True)
    closed = closed[-200:]
    events = events[-500:]
    perf = _metrics(closed)
    perf["open_positions"] = len(open_list)

    state["signal_portfolio"] = {
        "schema_version": 2,
        "updated_at": now,
        "mode": "LIVE_SIGNAL_TRACKING",
        "quote_mode": quote_mode,
        "disclaimer": (
            "Tracks confirmed LIVE signal entries only. It is not a brokerage account statement, "
            "and delayed/evaluation WATCH data never creates positions or performance records."
        ),
        "open_positions": open_list,
        "closed_trades": closed,
        "events": events,
        "performance": perf,
    }
    return state


def self_test():
    s = {
        "trade_lifecycle": {
            "quote_mode": "DELAYED_EVALUATION",
            "plans": [{"signal_id": "TEST-a1", "symbol": "TEST", "status": "WATCH", "trigger": 100, "risk_per_share": 5}],
        }
    }
    update_portfolio(s)
    assert s["signal_portfolio"]["open_positions"] == []
    assert s["signal_portfolio"]["schema_version"] == 2

    s["trade_lifecycle"] = {
        "quote_mode": "LIVE",
        "plans": [{
            "signal_id": "TEST-a1", "symbol": "TEST", "status": "ENTRY", "lifecycle_status": "T1",
            "trigger": 100, "risk_per_share": 5, "initial_stop": 95, "dynamic_stop": 100,
            "target1": 105, "target2": 110, "target3": 115, "price": 105,
            "stage": "TARGET1_BREAKEVEN", "score": 80, "confidence": "HIGH"
        }],
    }
    update_portfolio(s)
    assert len(s["signal_portfolio"]["open_positions"]) == 1
    assert s["signal_portfolio"]["open_positions"][0]["signal_id"] == "TEST-a1"

    s["trade_lifecycle"]["plans"][0]["price"] = 115
    s["trade_lifecycle"]["plans"][0]["stage"] = "TARGET3"
    s["trade_lifecycle"]["plans"][0]["lifecycle_status"] = "T3"
    s["trade_lifecycle"]["plans"][0]["dynamic_stop"] = 110
    update_portfolio(s)
    assert len(s["signal_portfolio"]["open_positions"]) == 0
    assert s["signal_portfolio"]["performance"]["closed_trades"] == 1
    assert s["signal_portfolio"]["closed_trades"][-1]["r_multiple"] == 3.0
    assert s["signal_portfolio"]["closed_trades"][-1]["lifecycle_status"] == "CLOSED"

    # Same closed signal must not reopen on the next LIVE scanner pass.
    update_portfolio(s)
    assert len(s["signal_portfolio"]["open_positions"]) == 0
    assert s["signal_portfolio"]["performance"]["closed_trades"] == 1

    # A genuinely new signal ID for the same symbol is allowed to open.
    s["trade_lifecycle"]["plans"][0].update({
        "signal_id": "TEST-b2", "price": 101, "stage": "ACTIVE", "lifecycle_status": "ENTRY", "dynamic_stop": 95
    })
    update_portfolio(s)
    assert len(s["signal_portfolio"]["open_positions"]) == 1
    assert s["signal_portfolio"]["open_positions"][0]["signal_id"] == "TEST-b2"


if __name__ == "__main__":
    self_test()
    state = update_portfolio(load_state())
    save_state(state)
    p = state.get("signal_portfolio", {})
    print(f"Portfolio updated: {len(p.get('open_positions', []))} open, {len(p.get('closed_trades', []))} closed")
