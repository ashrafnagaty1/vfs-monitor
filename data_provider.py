import os
import time
from datetime import datetime, timezone
import requests

from refo_bars_provider import provider as refo_bars_provider


class DataProviderError(RuntimeError):
    pass


class EGXDataProvider:
    """Single gateway for EGX quotes and historical candles.

    Default mode is explicitly non-live:
      - quote: demo.borsa.ashh.me
      - history: Yahoo Finance .CA daily candles

    A real licensed feed can be plugged in later without changing the scanner by
    setting EGX_LIVE_QUOTE_URL_TEMPLATE, for example:
      https://vendor.example/api/quote/{symbol}

    Optional auth environment variables:
      EGX_LIVE_TOKEN
      EGX_LIVE_AUTH_HEADER   (default: Authorization)
      EGX_LIVE_AUTH_PREFIX   (default: Bearer)
    """

    def __init__(self, timeout=15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "EGX-Smart-Scanner/1.0"})
        self.live_template = (os.environ.get("EGX_LIVE_QUOTE_URL_TEMPLATE") or "").strip()
        self.live_token = (os.environ.get("EGX_LIVE_TOKEN") or "").strip()
        self.auth_header = (os.environ.get("EGX_LIVE_AUTH_HEADER") or "Authorization").strip()
        self.auth_prefix = (os.environ.get("EGX_LIVE_AUTH_PREFIX") or "Bearer").strip()
        self.egyx_eod_enabled = (os.environ.get("EGYX_EOD_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}
        self.egyx_base_url = (os.environ.get("EGYX_BASE_URL") or "https://egyx.oratech.dev").rstrip("/")
        self.refo_bars = refo_bars_provider

    @property
    def has_live_quote(self):
        return bool(self.live_template)

    @property
    def quote_source_name(self):
        return "licensed/custom live feed" if self.has_live_quote else "borsa demo (evaluation)"

    @property
    def history_source_name(self):
        return self.refo_bars.source_name if self.refo_bars.configured else "Yahoo Finance EGX .CA daily candles"

    def _live_headers(self):
        headers = {}
        if self.live_token:
            value = f"{self.auth_prefix} {self.live_token}".strip()
            headers[self.auth_header] = value
        return headers

    @staticmethod
    def _first(data, *keys, default=None):
        for key in keys:
            if isinstance(data, dict) and key in data and data[key] is not None:
                return data[key]
        return default

    def _normalize_quote(self, symbol, raw, source, is_live):
        if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
            raw = raw["data"]
        if not isinstance(raw, dict):
            raise DataProviderError("QUOTE_BAD_PAYLOAD")

        price = self._first(raw, "price", "last", "last_price", "close", "LastPrice")
        if price is None:
            raise DataProviderError("QUOTE_MISSING_PRICE")

        def number(*keys, default=None):
            value = self._first(raw, *keys, default=default)
            try:
                return float(value) if value is not None else default
            except (TypeError, ValueError):
                return default

        volume = number("volume", "Volume", "trade_volume", default=0) or 0
        change = number("change", "Change", "net_change", default=0) or 0
        change_percent = self._first(raw, "change_percent", "changePercent", "pct_change", "ChangePercent", default=None)
        if change_percent is None:
            prev = number("previous_close", "prev_close", "PreviousClose")
            p = float(price)
            change_percent = f"{((p / prev - 1) * 100):+.2f}%" if prev else "-"
        elif isinstance(change_percent, (int, float)):
            change_percent = f"{float(change_percent):+.2f}%"

        return {
            "symbol": symbol.upper(),
            "price": float(price),
            "open": number("open", "Open"),
            "high": number("high", "High"),
            "low": number("low", "Low"),
            "volume": int(volume),
            "change": float(change),
            "change_percent": str(change_percent),
            "bid": number("bid", "best_bid", "BestBid"),
            "ask": number("ask", "best_ask", "BestAsk"),
            "source": source,
            "is_live": bool(is_live),
            "received_at": int(time.time()),
            "raw": raw,
        }

    def quote(self, symbol):
        symbol = symbol.upper().replace(".CA", "")
        if self.has_live_quote:
            url = self.live_template.format(symbol=symbol)
            r = self.session.get(url, headers=self._live_headers(), timeout=self.timeout)
            r.raise_for_status()
            return self._normalize_quote(symbol, r.json(), self.quote_source_name, True)

        r = self.session.get(f"https://demo.borsa.ashh.me/demo/quote/{symbol}", timeout=self.timeout)
        if r.status_code == 429:
            raise DataProviderError("DEMO_RATE_LIMIT")
        r.raise_for_status()
        return self._normalize_quote(symbol, r.json(), self.quote_source_name, False)

    def egyx_eod(self, symbol):
        """Optional EGYX EOD enrichment.

        This is never treated as live market data. It is opt-in because a public
        endpoint does not by itself establish redistribution/licensing rights.
        """
        if not self.egyx_eod_enabled:
            return None
        symbol = symbol.upper().replace(".CA", "")
        r = self.session.get(
            f"{self.egyx_base_url}/api/analyze",
            params={"ticker": symbol},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        bars = data.get("bars") if isinstance(data, dict) else None
        if not isinstance(bars, list) or not bars:
            raise DataProviderError("EGYX_EOD_NO_BARS")
        last = bars[-1] if isinstance(bars[-1], dict) else {}
        return {
            "provider": "EGYX / OraTech",
            "mode": "EOD",
            "is_live": False,
            "as_of": data.get("asOf"),
            "ticker": data.get("ticker") or f"{symbol}.CA",
            "name": data.get("name"),
            "sector": data.get("sector"),
            "open": self._first(last, "open"),
            "high": self._first(last, "high"),
            "low": self._first(last, "low"),
            "close": self._first(last, "close"),
            "volume": self._first(last, "volume"),
            "rsi14": self._first(last, "rsi14"),
            "atr14": self._first(last, "atr14"),
            "macd": self._first(last, "macd"),
            "macd_signal": self._first(last, "macdSignal"),
            "macd_hist": self._first(last, "macdHist"),
            "obv": self._first(last, "obv"),
            "cmf20": self._first(last, "cmf20"),
            "stoch_k": self._first(last, "stochK"),
            "stoch_d": self._first(last, "stochD"),
            "ma20": self._first(last, "ma20"),
            "ma50": self._first(last, "ma50"),
            "ma200": self._first(last, "ma200"),
            "ema20": self._first(last, "ema20"),
            "license_status": "UNVERIFIED_REUSE_PERMISSION",
        }

    def history(self, symbol, period="6mo", interval="1d"):
        symbol = symbol.upper().replace(".CA", "")
        if self.refo_bars.configured and interval == "1d":
            # Private share is verified as daily OHLCV only. Keep it non-live.
            limits = {"1mo": 35, "3mo": 90, "6mo": 180, "1y": 370, "2y": 740, "5y": 1850}
            result = self.refo_bars.history(symbol, limit=limits.get(period))
            rows = []
            for bar in result["bars"]:
                dt = datetime.strptime(bar["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                rows.append({
                    "ts": int(dt.timestamp()),
                    "open": bar["open"], "high": bar["high"], "low": bar["low"],
                    "close": bar["close"], "volume": bar["volume"],
                })
            if len(rows) < 35:
                raise DataProviderError("SHORT_HISTORY")
            return rows
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.CA"
        r = self.session.get(
            url,
            params={"range": period, "interval": interval},
            timeout=self.timeout,
        )
        r.raise_for_status()
        result = r.json().get("chart", {}).get("result") or []
        if not result:
            raise DataProviderError("NO_HISTORY")

        root = result[0]
        quote = root.get("indicators", {}).get("quote", [{}])[0]
        timestamps = root.get("timestamp", [])
        closes = quote.get("close", []) or []
        rows = []
        for i in range(len(closes)):
            row = {}
            for key in ("open", "high", "low", "close", "volume"):
                arr = quote.get(key) or []
                row[key] = arr[i] if i < len(arr) else None
            row["ts"] = timestamps[i] if i < len(timestamps) else None
            if all(row[k] is not None for k in ("open", "high", "low", "close")):
                rows.append(row)
        if len(rows) < 35:
            raise DataProviderError("SHORT_HISTORY")
        return rows

    def quote_health(self, symbol):
        """Compare quote to last daily close without pretending to measure exchange latency."""
        q = self.quote(symbol)
        rows = self.history(symbol, period="1mo", interval="1d")
        last_close = float(rows[-1]["close"])
        gap_pct = ((q["price"] / last_close) - 1) * 100 if last_close else 0.0
        return {
            "symbol": symbol.upper(),
            "quote_price": q["price"],
            "daily_close": last_close,
            "gap_pct": gap_pct,
            "quote_source": q["source"],
            "history_source": self.history_source_name,
            "is_live": q["is_live"],
            "bid": q.get("bid"),
            "ask": q.get("ask"),
        }


provider = EGXDataProvider()
