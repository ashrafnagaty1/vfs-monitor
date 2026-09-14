"""Deterministic Smart Money Concepts heuristics built only from real daily OHLCV.

These are algorithmic heuristics, not institutional order-flow claims. No bid/ask,
market-depth or intraday data is inferred.
"""


def _f(row, key):
    return float(row.get(key) or 0)


def analyze_rows(rows):
    if len(rows) < 25:
        raise ValueError("at least 25 OHLCV rows are required")

    recent = rows[-25:]
    highs = [_f(x, "high") for x in recent]
    lows = [_f(x, "low") for x in recent]
    closes = [_f(x, "close") for x in recent]
    last = recent[-1]
    price = closes[-1]

    swing_high = max(highs[:-1])
    swing_low = min(lows[:-1])
    equilibrium = (swing_high + swing_low) / 2
    zone = "DISCOUNT" if price < equilibrium else "PREMIUM"

    # Liquidity sweep heuristic: wick beyond a recent 10-day extreme, then close back inside.
    prev10_high = max(_f(x, "high") for x in recent[-11:-1])
    prev10_low = min(_f(x, "low") for x in recent[-11:-1])
    bearish_sweep = _f(last, "high") > prev10_high and price < prev10_high
    bullish_sweep = _f(last, "low") < prev10_low and price > prev10_low

    # Three-candle imbalance / FVG heuristic on daily bars.
    fvgs = []
    for i in range(2, len(recent)):
        a, c = recent[i - 2], recent[i]
        if _f(c, "low") > _f(a, "high"):
            fvgs.append({"type": "BULLISH", "low": _f(a, "high"), "high": _f(c, "low")})
        elif _f(c, "high") < _f(a, "low"):
            fvgs.append({"type": "BEARISH", "low": _f(c, "high"), "high": _f(a, "low")})

    # Order-block heuristic: last opposite candle before a decisive displacement candle.
    ranges = [max(1e-9, _f(x, "high") - _f(x, "low")) for x in recent]
    avg_range = sum(ranges[:-3]) / max(1, len(ranges[:-3]))
    obs = []
    for i in range(1, len(recent)):
        prev, cur = recent[i - 1], recent[i]
        cur_body = abs(_f(cur, "close") - _f(cur, "open"))
        if cur_body < avg_range * 1.15:
            continue
        prev_bear = _f(prev, "close") < _f(prev, "open")
        prev_bull = _f(prev, "close") > _f(prev, "open")
        cur_bull = _f(cur, "close") > _f(cur, "open")
        cur_bear = _f(cur, "close") < _f(cur, "open")
        if prev_bear and cur_bull and _f(cur, "close") > _f(prev, "high"):
            obs.append({"type": "DEMAND", "low": _f(prev, "low"), "high": max(_f(prev, "open"), _f(prev, "close"))})
        elif prev_bull and cur_bear and _f(cur, "close") < _f(prev, "low"):
            obs.append({"type": "SUPPLY", "low": min(_f(prev, "open"), _f(prev, "close")), "high": _f(prev, "high")})

    score = 50
    reasons = []
    if zone == "DISCOUNT":
        score += 8; reasons.append("السعر في النصف Discount من نطاق 25 جلسة")
    if bullish_sweep:
        score += 16; reasons.append("Liquidity sweep صاعد محتمل على قاع 10 جلسات")
    if bearish_sweep:
        score -= 16; reasons.append("Liquidity sweep هابط محتمل على قمة 10 جلسات")
    active_fvg = fvgs[-1] if fvgs else None
    active_ob = obs[-1] if obs else None
    if active_fvg and active_fvg["type"] == "BULLISH": score += 6
    if active_fvg and active_fvg["type"] == "BEARISH": score -= 6
    if active_ob and active_ob["type"] == "DEMAND": score += 8
    if active_ob and active_ob["type"] == "SUPPLY": score -= 8
    score = max(0, min(100, score))

    return {
        "price": price,
        "range_high": swing_high,
        "range_low": swing_low,
        "equilibrium": equilibrium,
        "premium_discount": zone,
        "bullish_sweep": bullish_sweep,
        "bearish_sweep": bearish_sweep,
        "fvg": active_fvg,
        "order_block": active_ob,
        "score": score,
        "reasons": reasons,
        "timeframe": "1D",
        "method": "OHLCV heuristic",
    }


def analyze_symbol(symbol):
    from pro_engine import hist
    return analyze_rows(hist(symbol))


def self_test():
    rows = []
    for i in range(30):
        close = 100 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 1, "low": close - 1, "close": close, "volume": 100000 + i * 1000})
    out = analyze_rows(rows)
    assert out["timeframe"] == "1D"
    assert out["method"] == "OHLCV heuristic"
    assert 0 <= out["score"] <= 100
    print("smart money self-test: PASS")


if __name__ == "__main__":
    self_test()
