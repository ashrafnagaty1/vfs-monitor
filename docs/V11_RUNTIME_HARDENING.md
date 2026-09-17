# ReFo V11 Runtime Hardening

This patch makes the final Telegram wrapper authoritative for the visible main menu while preserving legacy button compatibility.

- Canonical live-screen label: `🖥️ الشاشة اللحظية`.
- Legacy `📊 الشاشة اللحظية` remains accepted.
- Canonical subscription and advanced-analysis labels match the supplied reference.
- `/start`, `/menu`, and main-menu return are intercepted by the final wrapper so older modules cannot replace the visible menu.
- Live-screen launcher restores the persistent reply keyboard after sending the inline WebApp button.
- TradingView and market-data code are intentionally untouched.
- Delayed/evaluation safety rules are unchanged.
