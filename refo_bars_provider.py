"""Authenticated EOD bars adapter for the private ReFo bars share.

Credentials stay server-side. This provider is DAILY/EOD only: it must never
be used to claim live quotes, Bid/Ask, market depth, intraday bars, or ENTRY
confirmation.
"""
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests


class RefoBarsError(RuntimeError):
    pass


class RefoBarsProvider:
    def __init__(self, timeout=20, session=None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.base_url = (os.environ.get("REFO_BARS_URL") or "").strip()
        self.password = (os.environ.get("REFO_BARS_PASSWORD") or "").strip()
        self.enabled = (
            (os.environ.get("REFO_BARS_ENABLED") or "").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self._authenticated = False
        self._authenticated_at = 0.0
        self.session.headers.update({"User-Agent": "ReFo-EGX-EOD/1.0"})

    @property
    def configured(self):
        return bool(self.enabled and self.base_url and self.password)

    @property
    def source_name(self):
        return "ReFo authenticated bars share (Daily/EOD)"

    def _authenticate(self, force=False):
        if not self.configured:
            raise RefoBarsError("REFO_BARS_NOT_CONFIGURED")
        if self._authenticated and not force and time.time() - self._authenticated_at < 1800:
            return
        response = self.session.post(
            self.base_url,
            data={"file_password": self.password},
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        # The share establishes an authenticated session cookie. Never persist,
        # log, or expose its value.
        if not self.session.cookies:
            raise RefoBarsError("REFO_BARS_AUTH_COOKIE_MISSING")
        self._authenticated = True
        self._authenticated_at = time.time()

    @staticmethod
    def _validate_payload(symbol, payload):
        if not isinstance(payload, dict):
            raise RefoBarsError("REFO_BARS_BAD_PAYLOAD")
        bars = payload.get("bars")
        if payload.get("failed"):
            raise RefoBarsError("REFO_BARS_UPSTREAM_FAILED")
        if not isinstance(bars, list) or not bars:
            raise RefoBarsError("REFO_BARS_NO_BARS")
        clean = []
        for row in bars:
            if not isinstance(row, dict):
                continue
            try:
                date = str(row["date"])
                o = float(row["open"])
                h = float(row["high"])
                l = float(row["low"])
                c = float(row["close"])
                v = float(row.get("volume") or 0)
            except (KeyError, TypeError, ValueError):
                continue
            if h < l or min(o, h, l, c) < 0 or v < 0:
                continue
            clean.append(
                {"date": date, "open": o, "high": h, "low": l, "close": c, "volume": v}
            )
        if not clean:
            raise RefoBarsError("REFO_BARS_NO_VALID_BARS")
        clean.sort(key=lambda x: x["date"])
        return {
            "provider": "ReFo authenticated bars share",
            "mode": "EOD",
            "is_live": False,
            "symbol": symbol,
            "last_refresh_cairo_date": payload.get("lastRefreshCairoDate"),
            "last_refresh_was_post_close": bool(payload.get("lastRefreshWasPostClose")),
            "latest_bar_date": clean[-1]["date"],
            "bars": clean,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

    def history(self, symbol, limit=None):
        symbol = symbol.upper().replace(".CA", "")
        self._authenticate()
        url = f"{self.base_url}?fname=/{quote(symbol, safe='')}.json"
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code in (401, 403):
            self._authenticated = False
            self._authenticate(force=True)
            response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        result = self._validate_payload(symbol, response.json())
        if limit:
            result["bars"] = result["bars"][-int(limit):]
        return result


provider = RefoBarsProvider()
