"""Timing-window heuristic from trusted daily OHLCV only.

This module estimates *when* a new swing pivot may become statistically plausible
from the spacing of recent confirmed daily swing pivots. It does not forecast price
direction, intraday timing, or fabricate future market data.
"""

from statistics import median


def _f(row, key):
    try:
        return float(row.get(key) or 0)
    except Exception:
        return 0.0


def _pivot_indices(rows, window=3):
    pivots = []
    for i in range(window, len(rows) - window):
        high = _f(rows[i], "high")
        low = _f(rows[i], "low")
        if high <= 0 or low <= 0:
            continue
        neighbors = rows[i-window:i] + rows[i+1:i+1+window]
        highs = [_f(r, "high") for r in neighbors if _f(r, "high") > 0]
        lows = [_f(r, "low") for r in neighbors if _f(r, "low") > 0]
        is_high = bool(highs) and high >= max(highs)
        is_low = bool(lows) and low <= min(lows)
        if is_high or is_low:
            kind = "H" if is_high and not is_low else "L" if is_low and not is_high else "BOTH"
            pivots.append({"index": i, "kind": kind, "price": high if kind == "H" else low})
    return pivots


def _robust_cycle(intervals):
    if not intervals:
        return 0.0, 0.0
    core = sorted(float(x) for x in intervals if x > 0)
    if not core:
        return 0.0, 0.0
    med = float(median(core))
    deviations = [abs(x - med) for x in core]
    mad = float(median(deviations)) if deviations else 0.0
    return med, mad


def analyze_rows(rows):
    clean = [r for r in rows if _f(r, "high") > 0 and _f(r, "low") > 0 and _f(r, "close") > 0]
    if len(clean) < 50:
        raise ValueError("at least 50 valid daily OHLCV rows are required")

    pivots = _pivot_indices(clean)
    if len(pivots) < 5:
        return {
            "timeframe": "1D",
            "price": _f(clean[-1], "close"),
            "pivot_count": len(pivots),
            "status": "INSUFFICIENT_STRUCTURE",
            "method": "daily swing-spacing heuristic",
            "note": "Not enough confirmed daily swing pivots to estimate a timing window safely.",
        }

    recent = pivots[-10:]
    intervals = [recent[i]["index"] - recent[i-1]["index"] for i in range(1, len(recent))]
    cycle, mad = _robust_cycle(intervals)
    last_pivot = recent[-1]
    age = (len(clean) - 1) - int(last_pivot["index"])

    # Wider window when swing spacing is noisy; never claim single-session precision.
    tolerance = max(2, int(round(max(2.0, mad * 1.5))))
    expected = max(2, int(round(cycle)))
    remaining = expected - age
    window_start = max(0, remaining - tolerance)
    window_end = max(window_start, remaining + tolerance)

    dispersion = (mad / cycle) if cycle > 0 else 1.0
    sample_score = min(1.0, len(intervals) / 8.0)
    stability_score = max(0.0, 1.0 - min(1.0, dispersion))
    confidence = int(round(100 * (0.55 * sample_score + 0.45 * stability_score)))

    if remaining < -tolerance:
        phase = "OVERDUE"
    elif window_start <= 0 <= window_end:
        phase = "IN_WINDOW"
    else:
        phase = "AHEAD"

    return {
        "timeframe": "1D",
        "price": _f(clean[-1], "close"),
        "pivot_count": len(pivots),
        "interval_samples": intervals,
        "median_cycle_sessions": cycle,
        "mad_sessions": mad,
        "last_pivot_kind": last_pivot["kind"],
        "last_pivot_age_sessions": age,
        "expected_next_pivot_in_sessions": remaining,
        "window_start_sessions": window_start,
        "window_end_sessions": window_end,
        "confidence_score": confidence,
        "phase": phase,
        "status": "OK",
        "method": "daily swing-spacing heuristic",
        "note": "Timing window only: no direction, price target, intraday time, or certainty is implied.",
    }


def analyze_symbol(symbol):
    from pro_engine import hist
    return analyze_rows(hist(symbol))


def self_test():
    rows = []
    # Deterministic oscillating daily series with roughly 5-session swing spacing.
    pattern = [100, 102, 105, 108, 110, 108, 105, 102, 100, 98]
    for i in range(80):
        c = float(pattern[i % len(pattern)])
        rows.append({"open": c, "high": c + 1.0, "low": c - 1.0, "close": c, "volume": 1000 + i})
    out = analyze_rows(rows)
    assert out["status"] == "OK"
    assert out["median_cycle_sessions"] >= 3
    assert out["confidence_score"] >= 40
    assert out["window_end_sessions"] >= out["window_start_sessions"]
    print("temporal analysis self-test: PASS")


if __name__ == "__main__":
    self_test()
