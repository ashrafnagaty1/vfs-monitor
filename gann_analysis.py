"""Conservative Gann-style reference analysis built only from real daily OHLCV.

This module does not claim cycle prediction or intraday precision. It derives
transparent price reference levels from the latest trusted daily close and
summarises trend context from the supplied OHLCV history.
"""

import math


def _f(row, key):
    return float(row.get(key) or 0)


def _sma(values, n):
    if not values:
        return 0.0
    sample = values[-min(n, len(values)):]
    return sum(sample) / len(sample)


def _sq9_level(price, turns):
    """Square-of-Nine style price transform; turns are eighth-turn increments."""
    if price <= 0:
        return 0.0
    root = math.sqrt(price)
    shifted = max(0.0, root + turns / 8.0)
    return shifted * shifted


def analyze_rows(rows):
    if len(rows) < 30:
        raise ValueError("at least 30 OHLCV rows are required")

    clean = [r for r in rows if _f(r, "close") > 0]
    if len(clean) < 30:
        raise ValueError("not enough valid OHLCV rows")

    closes = [_f(r, "close") for r in clean]
    highs = [_f(r, "high") for r in clean]
    lows = [_f(r, "low") for r in clean]
    price = closes[-1]

    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    if price > sma20 and sma20 >= sma50:
        trend = "UP"
    elif price < sma20 and sma20 <= sma50:
        trend = "DOWN"
    else:
        trend = "SIDEWAYS"

    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    midpoint = (recent_high + recent_low) / 2.0

    # Use transparent Square-of-Nine style eighth-turn references around price.
    supports = sorted({_sq9_level(price, -1), _sq9_level(price, -2), _sq9_level(price, -4)}, reverse=True)
    resistances = sorted({_sq9_level(price, 1), _sq9_level(price, 2), _sq9_level(price, 4)})
    supports = [x for x in supports if 0 < x < price]
    resistances = [x for x in resistances if x > price]

    position = 50.0
    if recent_high > recent_low:
        position = 100.0 * (price - recent_low) / (recent_high - recent_low)
        position = max(0.0, min(100.0, position))

    score = 50
    reasons = []
    if trend == "UP":
        score += 15
        reasons.append("السعر أعلى متوسط 20 والمتوسط القصير غير أضعف من متوسط 50")
    elif trend == "DOWN":
        score -= 15
        reasons.append("السعر أسفل متوسط 20 والمتوسط القصير غير أقوى من متوسط 50")
    else:
        reasons.append("الاتجاه اليومي مختلط/عرضي وفق متوسطات 20 و50")

    if price >= midpoint:
        score += 5
        reasons.append("السعر في النصف العلوي من نطاق آخر 20 جلسة")
    else:
        score -= 5
        reasons.append("السعر في النصف السفلي من نطاق آخر 20 جلسة")

    score = max(0, min(100, score))

    return {
        "price": price,
        "timeframe": "1D",
        "method": "Gann-style OHLCV reference heuristic",
        "trend": trend,
        "sma20": sma20,
        "sma50": sma50,
        "range_low": recent_low,
        "range_high": recent_high,
        "range_position_pct": position,
        "supports": supports[:3],
        "resistances": resistances[:3],
        "score": score,
        "reasons": reasons,
    }


def analyze_symbol(symbol):
    from pro_engine import hist
    return analyze_rows(hist(symbol))


def self_test():
    rows = []
    for i in range(60):
        close = 20 + i * 0.15
        rows.append({
            "open": close - 0.05,
            "high": close + 0.30,
            "low": close - 0.30,
            "close": close,
            "volume": 100000 + i * 1000,
        })
    out = analyze_rows(rows)
    assert out["timeframe"] == "1D"
    assert out["trend"] == "UP"
    assert out["supports"] and all(x < out["price"] for x in out["supports"])
    assert out["resistances"] and all(x > out["price"] for x in out["resistances"])
    assert 0 <= out["score"] <= 100
    print("gann analysis self-test: PASS")


if __name__ == "__main__":
    self_test()
