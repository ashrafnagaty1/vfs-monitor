"""Conservative Elliott-wave structure heuristic from trusted daily OHLCV only.

This module labels *candidate* impulse and ABC structures from alternating swing
pivots. Elliott counting is inherently subjective, so results expose every pivot,
ratio and rule used instead of presenting an automatic count as certain.
"""


def _f(row, key):
    return float(row.get(key) or 0)


def _ratio(a, b):
    return abs(a) / abs(b) if b else 0.0


def _pivot_candidates(rows, window=3):
    pivots = []
    for i in range(window, len(rows) - window):
        high = _f(rows[i], "high")
        low = _f(rows[i], "low")
        if high <= 0 or low <= 0:
            continue
        neighbors = rows[i-window:i] + rows[i+1:i+1+window]
        if high >= max([_f(r, "high") for r in neighbors] or [high]):
            pivots.append({"index": i, "price": high, "kind": "H"})
        valid_lows = [_f(r, "low") for r in neighbors if _f(r, "low") > 0]
        if low <= min(valid_lows or [low]):
            pivots.append({"index": i, "price": low, "kind": "L"})
    pivots.sort(key=lambda p: (p["index"], 0 if p["kind"] == "L" else 1))
    return pivots


def _compress_alternating(pivots):
    out = []
    for p in pivots:
        if not out:
            out.append(p)
            continue
        prev = out[-1]
        if p["kind"] == prev["kind"]:
            more_extreme = p["price"] > prev["price"] if p["kind"] == "H" else p["price"] < prev["price"]
            if more_extreme:
                out[-1] = p
        elif p["index"] != prev["index"]:
            out.append(p)
    return out


def _impulse_candidate(points):
    if len(points) != 6:
        return None
    kinds = "".join(p["kind"] for p in points)
    if kinds not in ("LHLHLH", "HLHLHL"):
        return None

    prices = [p["price"] for p in points]
    bullish = kinds == "LHLHLH"
    sign = 1.0 if bullish else -1.0
    legs = [(prices[i+1] - prices[i]) * sign for i in range(5)]
    # In trend direction, waves 1/3/5 should be positive and 2/4 retracements negative.
    if not (legs[0] > 0 and legs[1] < 0 and legs[2] > 0 and legs[3] < 0 and legs[4] > 0):
        return None

    w1, w2, w3, w4, w5 = legs
    rules = {
        "wave2_holds_origin": (prices[2] - prices[0]) * sign > 0,
        "wave3_extends_wave1": (prices[3] - prices[1]) * sign > 0,
        "wave3_not_shortest": abs(w3) >= min(abs(w1), abs(w5)),
        "wave4_no_wave1_overlap": (prices[4] - prices[1]) * sign > 0,
        "wave5_advances_wave3": (prices[5] - prices[3]) * sign > 0,
    }
    passed = sum(1 for ok in rules.values() if ok)
    if passed < 4:
        return None

    ratios = {
        "W2/W1": _ratio(w2, w1),
        "W3/W1": _ratio(w3, w1),
        "W4/W3": _ratio(w4, w3),
        "W5/W1": _ratio(w5, w1),
    }
    return {
        "type": "IMPULSE_CANDIDATE",
        "direction": "BULLISH" if bullish else "BEARISH",
        "confidence_score": passed * 20,
        "rules": rules,
        "ratios": ratios,
        "points": [{"label": str(i), **p} for i, p in enumerate(points)],
    }


def _abc_candidate(points):
    if len(points) != 4:
        return None
    kinds = "".join(p["kind"] for p in points)
    if kinds not in ("HLHL", "LHLH"):
        return None
    prices = [p["price"] for p in points]
    # Correction direction is A/C direction.
    bearish = kinds == "HLHL"
    sign = -1.0 if bearish else 1.0
    a = (prices[1] - prices[0]) * sign
    b = (prices[2] - prices[1]) * sign
    c = (prices[3] - prices[2]) * sign
    if not (a > 0 and b < 0 and c > 0):
        return None
    b_a = _ratio(b, a)
    c_a = _ratio(c, a)
    rules = {
        "b_is_retracement": 0.20 <= b_a <= 0.90,
        "c_resumes_correction": c > 0,
        "c_meaningful_vs_a": 0.50 <= c_a <= 2.00,
    }
    passed = sum(1 for ok in rules.values() if ok)
    if passed < 3:
        return None
    return {
        "type": "ABC_CANDIDATE",
        "direction": "BEARISH" if bearish else "BULLISH",
        "confidence_score": int(round(passed / len(rules) * 100)),
        "rules": rules,
        "ratios": {"B/A": b_a, "C/A": c_a},
        "points": [{"label": label, **p} for label, p in zip("0ABC", points)],
    }


def analyze_rows(rows):
    clean = [r for r in rows if _f(r, "high") > 0 and _f(r, "low") > 0 and _f(r, "close") > 0]
    if len(clean) < 50:
        raise ValueError("at least 50 valid OHLCV rows are required")

    pivots = _compress_alternating(_pivot_candidates(clean))
    impulse = None
    # Prefer the freshest valid six-pivot candidate.
    for start in range(max(0, len(pivots) - 16), max(0, len(pivots) - 5)):
        cand = _impulse_candidate(pivots[start:start+6])
        if cand:
            cand["age_bars"] = len(clean) - 1 - cand["points"][-1]["index"]
            if impulse is None or cand["age_bars"] < impulse["age_bars"]:
                impulse = cand

    abc = None
    for start in range(max(0, len(pivots) - 12), max(0, len(pivots) - 3)):
        cand = _abc_candidate(pivots[start:start+4])
        if cand:
            cand["age_bars"] = len(clean) - 1 - cand["points"][-1]["index"]
            if abc is None or cand["age_bars"] < abc["age_bars"]:
                abc = cand

    return {
        "timeframe": "1D",
        "price": _f(clean[-1], "close"),
        "pivot_count": len(pivots),
        "impulse": impulse,
        "abc": abc,
        "method": "swing-pivot Elliott candidate heuristic",
        "note": "Automatic Elliott labels are heuristic and subjective; no future wave is fabricated.",
    }


def analyze_symbol(symbol):
    from pro_engine import hist
    return analyze_rows(hist(symbol))


def self_test():
    bullish = [
        {"index": 0, "price": 100.0, "kind": "L"},
        {"index": 1, "price": 110.0, "kind": "H"},
        {"index": 2, "price": 105.0, "kind": "L"},
        {"index": 3, "price": 122.0, "kind": "H"},
        {"index": 4, "price": 113.0, "kind": "L"},
        {"index": 5, "price": 128.0, "kind": "H"},
    ]
    out = _impulse_candidate(bullish)
    assert out and out["direction"] == "BULLISH" and out["confidence_score"] >= 80
    abc = _abc_candidate([
        {"index": 0, "price": 130.0, "kind": "H"},
        {"index": 1, "price": 118.0, "kind": "L"},
        {"index": 2, "price": 124.0, "kind": "H"},
        {"index": 3, "price": 112.0, "kind": "L"},
    ])
    assert abc and abc["direction"] == "BEARISH"
    print("elliott analysis self-test: PASS")


if __name__ == "__main__":
    self_test()
