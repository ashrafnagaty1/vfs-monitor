from pro_engine import ema, rsi, atr, adx, mfi, candle_setup, market_regime
from data_provider import EGXDataProvider


def synthetic_rows(n=80, start=100.0, step=0.5):
    rows = []
    price = start
    for i in range(n):
        o = price
        c = price + step
        h = max(o, c) + 0.4
        l = min(o, c) - 0.3
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": 100000 + i * 1000})
        price = c
    return rows


def main():
    rows = synthetic_rows()
    closes = [x["close"] for x in rows]

    assert ema(closes, 20) > 0
    assert -1e-9 <= rsi(closes) <= 100.000001
    assert atr(rows) > 0
    assert -1e-9 <= adx(rows) <= 100.000001
    assert -1e-9 <= mfi(rows) <= 100.000001
    assert isinstance(candle_setup(rows), list)

    regime = market_regime([
        {"mom5": 2.0, "score": 80},
        {"mom5": 1.0, "score": 75},
        {"mom5": -0.2, "score": 60},
    ])
    assert "name" in regime and "breadth" in regime

    provider = EGXDataProvider()
    normalized = provider._normalize_quote(
        "TEST",
        {"price": 10, "high": 11, "low": 9, "volume": 1234, "previous_close": 9.5},
        "unit-test",
        False,
    )
    assert normalized["price"] == 10.0
    assert normalized["volume"] == 1234
    assert normalized["is_live"] is False

    print("EGX scanner self-test: PASS")


if __name__ == "__main__":
    main()
