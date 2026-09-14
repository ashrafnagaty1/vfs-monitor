"""Conservative harmonic XABCD detector using trusted daily OHLCV only.

The detector extracts alternating swing pivots from daily highs/lows and compares
completed XABCD structures with broad, documented Fibonacci ratio tolerances.
It does not fabricate intraday pivots or claim a future reversal is guaranteed.
"""


def _f(row, key):
    return float(row.get(key) or 0)


def _ratio(a, b):
    return abs(a) / abs(b) if b else 0.0


def _near(value, target, tol=0.12):
    return target * (1.0 - tol) <= value <= target * (1.0 + tol)


def _between(value, lo, hi, pad=0.08):
    return lo * (1.0 - pad) <= value <= hi * (1.0 + pad)


def _pivot_candidates(rows, window=3):
    pivots = []
    for i in range(window, len(rows) - window):
        high = _f(rows[i], "high")
        low = _f(rows[i], "low")
        if high <= 0 or low <= 0:
            continue
        left = rows[i-window:i]
        right = rows[i+1:i+1+window]
        if high >= max([_f(r, "high") for r in left + right] or [high]):
            pivots.append({"index": i, "price": high, "kind": "H"})
        if low <= min([_f(r, "low") for r in left + right if _f(r, "low") > 0] or [low]):
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
            better = p["price"] > prev["price"] if p["kind"] == "H" else p["price"] < prev["price"]
            if better:
                out[-1] = p
        elif p["index"] != prev["index"]:
            out.append(p)
    return out


def _classify(points):
    x, a, b, c, d = [p["price"] for p in points]
    xa, ab, bc, cd = a-x, b-a, c-b, d-c
    if not all([xa, ab, bc, cd]) or xa * ab >= 0 or ab * bc >= 0 or bc * cd >= 0:
        return None

    ab_xa = _ratio(ab, xa)
    bc_ab = _ratio(bc, ab)
    cd_bc = _ratio(cd, bc)
    ad_xa = _ratio(d-a, xa)

    matches = []
    # Completed-pattern heuristics; tolerance is deliberately broad enough for market data,
    # but every displayed ratio is exposed to the user.
    if _near(ab_xa, 0.618) and _between(bc_ab, 0.382, 0.886) and _between(cd_bc, 1.13, 1.618) and _near(ad_xa, 0.786, 0.15):
        matches.append(("Gartley", 4))
    if _between(ab_xa, 0.382, 0.50) and _between(bc_ab, 0.382, 0.886) and _between(cd_bc, 1.618, 2.618) and _near(ad_xa, 0.886, 0.15):
        matches.append(("Bat", 4))
    if _near(ab_xa, 0.786, 0.15) and _between(bc_ab, 0.382, 0.886) and _between(cd_bc, 1.618, 2.618) and _between(ad_xa, 1.18, 1.45):
        matches.append(("Butterfly", 4))
    if _between(ab_xa, 0.382, 0.618) and _between(bc_ab, 0.382, 0.886) and _between(cd_bc, 2.24, 3.618) and _between(ad_xa, 1.50, 1.75):
        matches.append(("Crab", 4))
    if not matches:
        return None

    pattern = matches[0][0]
    direction = "BULLISH" if points[-1]["kind"] == "L" else "BEARISH"
    return {
        "pattern": pattern,
        "direction": direction,
        "ratios": {"AB/XA": ab_xa, "BC/AB": bc_ab, "CD/BC": cd_bc, "AD/XA": ad_xa},
    }


def analyze_rows(rows):
    clean = [r for r in rows if _f(r, "high") > 0 and _f(r, "low") > 0 and _f(r, "close") > 0]
    if len(clean) < 40:
        raise ValueError("at least 40 valid OHLCV rows are required")

    pivots = _compress_alternating(_pivot_candidates(clean))
    found = []
    for i in range(max(0, len(pivots)-14), len(pivots)-4):
        pts = pivots[i:i+5]
        match = _classify(pts)
        if match:
            match["points"] = [{"label": label, **p} for label, p in zip("XABCD", pts)]
            match["age_bars"] = len(clean) - 1 - pts[-1]["index"]
            found.append(match)

    found.sort(key=lambda m: m["age_bars"])
    latest = found[0] if found else None
    price = _f(clean[-1], "close")
    return {
        "timeframe": "1D",
        "price": price,
        "pivot_count": len(pivots),
        "pattern": latest,
        "method": "completed XABCD Fibonacci-ratio heuristic",
        "note": "Algorithmic pattern detection from daily OHLCV; not a guaranteed reversal signal.",
    }


def analyze_symbol(symbol):
    from pro_engine import hist
    return analyze_rows(hist(symbol))


def self_test():
    # Validate classifier deterministically with a textbook-like bullish Gartley geometry.
    pts = [
        {"index": 0, "price": 100.0, "kind": "L"},
        {"index": 1, "price": 120.0, "kind": "H"},
        {"index": 2, "price": 107.64, "kind": "L"},
        {"index": 3, "price": 115.0, "kind": "H"},
        {"index": 4, "price": 104.3, "kind": "L"},
    ]
    out = _classify(pts)
    assert out and out["pattern"] == "Gartley" and out["direction"] == "BULLISH"
    assert 0.55 < out["ratios"]["AB/XA"] < 0.70
    rows = []
    for i in range(60):
        c = 20 + i * 0.1
        rows.append({"open": c, "high": c+0.3, "low": c-0.3, "close": c, "volume": 100000})
    scan = analyze_rows(rows)
    assert scan["timeframe"] == "1D" and scan["price"] > 0
    print("harmonic analysis self-test: PASS")


if __name__ == "__main__":
    self_test()
