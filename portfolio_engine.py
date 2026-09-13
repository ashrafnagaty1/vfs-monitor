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


def update_portfolio(state):
    now = datetime.now(CAIRO).isoformat()
    lifecycle = state.get("trade_lifecycle") or {}
    plans = lifecycle.get("plans") or []
    quote_mode = lifecycle.get("quote_mode") or "DELAYED_EVALUATION"

    old = state.get("signal_portfolio") or {}
    open_positions = {
        str(x.get("symbol") or "").upper(): x
        for x in (old.get("open_positions") or [])
        if x.get("symbol")
    }
    closed = list(old.get("closed_trades") or [])

    # Only confirmed LIVE ENTRY states are admitted. Delayed WATCH data never creates trades.
    if quote_mode == "LIVE":
        for p in plans:
            symbol = str(p.get("symbol") or "").upper()
            if not symbol:
                continue

            if p.get("status") == "ENTRY" and symbol not in open_positions:
                trigger = float(p.get("trigger") or 0)
                risk = float(p.get("risk_per_share") or 0)
                if trigger > 0 and risk > 0:
                    open_positions[symbol] = {
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
                        "score": p.get("score"),
                        "confidence": p.get("confidence"),
                    }

            pos = open_positions.get(symbol)
            if not pos:
                continue

            pos["last_price"] = p.get("price")
            pos["dynamic_stop"] = p.get("dynamic_stop")
            pos["stage"] = p.get("stage")
            entry = float(pos.get("entry_price") or 0)
            risk = float(pos.get("risk_per_share") or 0)
            last_price = float(p.get("price") or 0)
            pos["unrealized_r"] = round(_r_multiple(entry, last_price, risk), 2)

            close_reason = None
            exit_price = None
            if p.get("stage") == "TARGET3":
                close_reason = "TARGET3"
                exit_price = float(p.get("target3") or last_price)
            elif last_price > 0 and float(p.get("dynamic_stop") or 0) > 0 and last_price <= float(p.get("dynamic_stop") or 0):
                close_reason = "STOP"
                exit_price = float(p.get("dynamic_stop") or last_price)

            if close_reason:
                trade = dict(pos)
                trade.update({
                    "closed_at": now,
                    "exit_price": round(exit_price, 4),
                    "close_reason": close_reason,
                    "r_multiple": round(_r_multiple(entry, exit_price, risk), 2),
                })
                closed.append(trade)
                open_positions.pop(symbol, None)

    open_list = sorted(open_positions.values(), key=lambda x: x.get("opened_at", ""), reverse=True)
    closed = closed[-200:]
    perf = _metrics(closed)
    perf["open_positions"] = len(open_list)

    state["signal_portfolio"] = {
        "updated_at": now,
        "mode": "LIVE_SIGNAL_TRACKING",
        "quote_mode": quote_mode,
        "disclaimer": (
            "Tracks confirmed LIVE signal entries only. It is not a brokerage account statement, "
            "and delayed/evaluation WATCH data never creates positions or performance records."
        ),
        "open_positions": open_list,
        "closed_trades": closed,
        "performance": perf,
    }
    return state


def self_test():
    s = {
        "trade_lifecycle": {
            "quote_mode": "DELAYED_EVALUATION",
            "plans": [{"symbol": "TEST", "status": "WATCH", "trigger": 100, "risk_per_share": 5}],
        }
    }
    update_portfolio(s)
    assert s["signal_portfolio"]["open_positions"] == []

    s["trade_lifecycle"] = {
        "quote_mode": "LIVE",
        "plans": [{
            "symbol": "TEST", "status": "ENTRY", "trigger": 100, "risk_per_share": 5,
            "initial_stop": 95, "dynamic_stop": 100, "target1": 105, "target2": 110,
            "target3": 115, "price": 105, "stage": "TARGET1_BREAKEVEN", "score": 80,
            "confidence": "HIGH"
        }],
    }
    update_portfolio(s)
    assert len(s["signal_portfolio"]["open_positions"]) == 1

    s["trade_lifecycle"]["plans"][0]["price"] = 115
    s["trade_lifecycle"]["plans"][0]["stage"] = "TARGET3"
    s["trade_lifecycle"]["plans"][0]["dynamic_stop"] = 110
    update_portfolio(s)
    assert len(s["signal_portfolio"]["open_positions"]) == 0
    assert s["signal_portfolio"]["performance"]["closed_trades"] == 1
    assert s["signal_portfolio"]["closed_trades"][-1]["r_multiple"] == 3.0


if __name__ == "__main__":
    self_test()
    state = update_portfolio(load_state())
    save_state(state)
    p = state.get("signal_portfolio", {})
    print(f"Portfolio updated: {len(p.get('open_positions', []))} open, {len(p.get('closed_trades', []))} closed")
