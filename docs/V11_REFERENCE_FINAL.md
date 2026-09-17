# ReFo V11 Reference Final

This branch consolidates the latest Telegram/reference-screen feedback into one release candidate.

## Telegram experience
- Main menu follows the supplied reference ordering: live screen + assistant, subscription placeholder, daily speculation + trades, stock analysis + advanced analysis, then ReFo-specific opportunities/watchlist/alerts/portfolio/performance/market/settings.
- `📊 الشاشة اللحظية` sends a Telegram WebApp inline button pointing to `REFO_WEBAPP_URL`, defaulting to `https://refogx-pro.folkhero3.workers.dev/`.
- Stock cards remain source-aware and never promote delayed WATCH to ENTRY.
- Existing real modules remain in the chain: Smart Money, Gann, Harmonic, Elliott, Temporal, opportunities, market, personal portfolio, assistant and reports.

## Runtime
- Always-on service now runs `pro_engine_v2.py` by default so the richer `pro_engine_snapshot` used by the terminal/API is refreshed every engine cycle. Override with `REFO_ENGINE_SCRIPT` if needed.

## Data integrity
- TradingView is not scraped and is not treated as the source for custom side panels.
- Bid/Ask/depth/official EGX indices/fundamentals stay unavailable until a verified feed is connected.
- Delayed/evaluation data remains explicitly labeled.

## Deployment safety
This work is isolated on `refo-v11-reference-final` until tests/workflows pass and it is intentionally merged.