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


def _tech_map(state):
    snap = state.get("pro_engine_snapshot") or {}
    return {
        str(x.get("symbol") or "").upper(): x
        for x in (snap.get("details") or snap.get("top") or [])
        if x.get("symbol")
    }


def assess_plan(plan, technical=None):
    technical = technical or {}
    quote_mode = str(plan.get("quote_mode") or "DELAYED_EVALUATION")
    rr = float(plan.get("rr_to_t1_now") or 0)
    liq = float(plan.get("liquidity_score") or 0)
    distance = float(plan.get("distance_to_trigger_pct") or 999)
    rsi = float(technical.get("rsi") or 50)
    adx = float(technical.get("adx") or 0)
    volume_ratio = float(technical.get("volume_ratio") or 0)

    blockers = []
    warnings = []

    if quote_mode != "LIVE":
        blockers.append("NO_LIVE_FEED")
    if rr < 1.30:
        blockers.append("LOW_RR")
    if liq < 35:
        warnings.append("LOW_LIQUIDITY")
    if rsi >= 78:
        blockers.append("OVERHEATED_RSI")
    elif rsi >= 74:
        warnings.append("HIGH_RSI")
    if adx < 18:
        warnings.append("WEAK_TREND")
    if volume_ratio and volume_ratio < 0.75:
        warnings.append("WEAK_VOLUME")
    if distance > 3:
        warnings.append("FAR_FROM_TRIGGER")

    quality = 100
    quality -= 25 if rr < 1.30 else 0
    quality -= 18 if liq < 35 else 0
    quality -= 20 if rsi >= 78 else (8 if rsi >= 74 else 0)
    quality -= 10 if adx < 18 else 0
    quality -= 8 if volume_ratio and volume_ratio < 0.75 else 0
    quality -= 8 if distance > 3 else 0
    quality = max(0, min(100, quality))

    if blockers:
        decision = "BLOCKED"
    elif warnings:
        decision = "CAUTION"
    else:
        decision = "PASS"

    return {
        "decision": decision,
        "quality_score": quality,
        "blockers": blockers,
        "warnings": warnings,
        "execution_ready": quote_mode == "LIVE" and not blockers,
        "metrics": {
            "rr": round(rr, 2),
            "liquidity": round(liq, 1),
            "rsi": round(rsi, 1),
            "adx": round(adx, 1),
            "volume_ratio": round(volume_ratio, 2),
            "distance_to_trigger_pct": round(distance, 2),
        },
    }


def apply_guard(state):
    now = datetime.now(CAIRO).isoformat()
    lifecycle = state.get("trade_lifecycle") or {}
    plans = lifecycle.get("plans") or []
    tech = _tech_map(state)

    seen = state.setdefault("trade_alert_seen", {})
    history = list(state.get("trade_alerts") or [])
    counts = {"PASS": 0, "CAUTION": 0, "BLOCKED": 0}

    def emit(symbol, kind, level, text, discriminator):
        key = f"{symbol}:{kind}:{discriminator}"
        if key in seen:
            return
        seen[key] = now
        history.append({
            "at": now,
            "symbol": symbol,
            "kind": kind,
            "level": level,
            "text": text,
        })

    for plan in plans:
        symbol = str(plan.get("symbol") or "").upper()
        guard = assess_plan(plan, tech.get(symbol, {}))
        plan["guard"] = guard
        counts[guard["decision"]] += 1

        metrics = guard["metrics"]
        blockers = set(guard["blockers"])
        warnings = set(guard["warnings"])

        # Warnings are informational WATCH safety gates, never execution claims.
        if "OVERHEATED_RSI" in blockers:
            emit(
                symbol,
                "OVERHEATED_WATCH",
                "MEDIUM",
                f"{symbol} قريب من التفعيل لكن RSI مرتفع ({metrics['rsi']:.1f}) — تجنب مطاردة السعر حتى يهدأ الزخم",
                f"rsi:{int(metrics['rsi'])}",
            )
        if "LOW_RR" in blockers and 0 <= metrics["distance_to_trigger_pct"] <= 2:
            emit(
                symbol,
                "LOW_RR_WARNING",
                "MEDIUM",
                f"{symbol} قريب من Trigger لكن RR إلى T1 منخفض ({metrics['rr']:.2f})",
                f"rr:{round(metrics['rr'], 1)}",
            )
        if "LOW_LIQUIDITY" in warnings and 0 <= metrics["distance_to_trigger_pct"] <= 2:
            emit(
                symbol,
                "LIQUIDITY_CAUTION",
                "LOW",
                f"{symbol} قريب من Trigger لكن درجة السيولة منخفضة ({metrics['liquidity']:.0f})",
                f"liq:{int(metrics['liquidity'])}",
            )

    lifecycle["plans"] = plans
    state["trade_lifecycle"] = lifecycle
    state["trade_alerts"] = history[-100:]
    state["trade_alert_seen"] = dict(list(seen.items())[-400:])
    state["signal_guard"] = {
        "updated_at": now,
        "quote_mode": lifecycle.get("quote_mode") or "DELAYED_EVALUATION",
        "policy": (
            "Execution-ready requires LIVE quotes, RR >= 1.30 and no overheating blocker. "
            "Delayed/evaluation plans remain analysis-only WATCH regardless of score."
        ),
        "counts": counts,
    }
    return state


def self_test():
    delayed = {
        "symbol": "TEST", "quote_mode": "DELAYED_EVALUATION", "rr_to_t1_now": 2.0,
        "liquidity_score": 90, "distance_to_trigger_pct": 0.5,
    }
    g = assess_plan(delayed, {"rsi": 60, "adx": 30, "volume_ratio": 1.5})
    assert g["decision"] == "BLOCKED"
    assert "NO_LIVE_FEED" in g["blockers"]
    assert not g["execution_ready"]

    live_good = dict(delayed, quote_mode="LIVE")
    g = assess_plan(live_good, {"rsi": 60, "adx": 30, "volume_ratio": 1.5})
    assert g["decision"] == "PASS"
    assert g["execution_ready"]

    hot = dict(live_good)
    g = assess_plan(hot, {"rsi": 81, "adx": 45, "volume_ratio": 2.0})
    assert g["decision"] == "BLOCKED"
    assert "OVERHEATED_RSI" in g["blockers"]

    weak_rr = dict(live_good, rr_to_t1_now=1.1)
    g = assess_plan(weak_rr, {"rsi": 60, "adx": 30, "volume_ratio": 1.2})
    assert "LOW_RR" in g["blockers"]
    assert not g["execution_ready"]


if __name__ == "__main__":
    self_test()
    state = apply_guard(load_state())
    save_state(state)
    print("Signal guard updated:", state.get("signal_guard", {}).get("counts", {}))
