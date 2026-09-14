import bot_experience


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def _num(value, digits=1):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def _runtime(base):
    try:
        return base.load_json(base.STATE_FILE, {}) or {}
    except Exception:
        return {}


def _quote_label(snapshot):
    mode = str(snapshot.get("quote_mode") or "").upper()
    source = snapshot.get("quote_source") or "OHLCV / آخر Snapshot متاح"
    if mode == "LIVE":
        return f"🟢 LIVE مؤكد — {source}"
    return f"🟡 DELAYED / EVALUATION — {source}"


def _sector(item):
    return str(item.get("sector") or item.get("sector_name") or "غير مصنف").strip()


def _market_metrics(runtime):
    snapshot = runtime.get("pro_engine_snapshot") or {}
    top = _as_list(snapshot.get("top"))
    valid = [x for x in top if x.get("price") is not None]
    positive = []
    negative = []
    liquidity = []
    volume_ratio = []
    scores = []
    for x in valid:
        mom = x.get("momentum_5d", x.get("mom5"))
        try:
            mom = float(mom)
            (positive if mom > 0 else negative).append(x)
        except Exception:
            pass
        for key, bucket in (("liquidity_score", liquidity), ("volume_ratio", volume_ratio), ("score", scores)):
            try:
                value = float(x.get(key))
                bucket.append(value)
            except Exception:
                pass
    breadth = (100.0 * len(positive) / (len(positive) + len(negative))) if (positive or negative) else None
    return {
        "count": len(valid),
        "breadth": breadth,
        "up": len(positive),
        "down": len(negative),
        "avg_liquidity": sum(liquidity) / len(liquidity) if liquidity else None,
        "avg_volume_ratio": sum(volume_ratio) / len(volume_ratio) if volume_ratio else None,
        "avg_score": sum(scores) / len(scores) if scores else None,
    }


def _sector_rows(runtime):
    snapshot = runtime.get("pro_engine_snapshot") or {}
    top = _as_list(snapshot.get("top"))
    groups = {}
    for item in top:
        sec = _sector(item)
        g = groups.setdefault(sec, {"count": 0, "score": [], "mom": [], "liq": []})
        g["count"] += 1
        for keys, bucket in ((("score",), g["score"]), (("momentum_5d", "mom5"), g["mom"]), (("liquidity_score",), g["liq"])):
            value = None
            for key in keys:
                if item.get(key) is not None:
                    value = item.get(key)
                    break
            try:
                bucket.append(float(value))
            except Exception:
                pass
    rows = []
    for sec, g in groups.items():
        rows.append({
            "sector": sec,
            "count": g["count"],
            "score": sum(g["score"]) / len(g["score"]) if g["score"] else 0.0,
            "mom": sum(g["mom"]) / len(g["mom"]) if g["mom"] else 0.0,
            "liq": sum(g["liq"]) / len(g["liq"]) if g["liq"] else 0.0,
        })
    rows.sort(key=lambda x: (x["score"], x["mom"], x["count"]), reverse=True)
    return rows


MARKET_MENU = _keyboard([
    ["📈 ملخص السوق", "💧 سيولة العينة"],
    ["🗺️ ترتيب القطاعات", "📊 الشاشة اللحظية"],
    ["🎯 فرص اليوم", "🔮 فرص بكرة"],
    ["🏠 القائمة الرئيسية"],
])


def _market_text(runtime):
    snapshot = runtime.get("pro_engine_snapshot") or {}
    metrics = _market_metrics(runtime)
    regime = snapshot.get("market_regime") or {}
    lines = [
        "📈 <b>ReFo — ملخص السوق</b>",
        f"📡 {_quote_label(snapshot)}",
        "",
        f"الحالة: <b>{regime.get('name') or '-'}</b>",
        f"Breadth للعينة: <b>{_num(metrics['breadth'])}%</b> · صاعد {metrics['up']} / غير صاعد {metrics['down']}",
        f"Avg Score: {_num(metrics['avg_score'])}/100 · الأسهم المحللة: {metrics['count']}",
        "",
        "ℹ️ Breadth هنا محسوب من الأسهم المتاحة للمحرك فقط، وليس Market Breadth رسميًا لكل البورصة.",
    ]
    return "\n".join(lines)


def _liquidity_text(runtime):
    snapshot = runtime.get("pro_engine_snapshot") or {}
    m = _market_metrics(runtime)
    lines = [
        "💧 <b>السيولة — Sample Based</b>",
        f"📡 {_quote_label(snapshot)}",
        "",
        f"متوسط Liquidity Score: <b>{_num(m['avg_liquidity'])}</b>",
        f"متوسط Volume Ratio: <b>{_num(m['avg_volume_ratio'], 2)}x</b>",
        f"حجم العينة: <b>{m['count']}</b> سهم",
        "",
        "⚠️ لا يعرض ReFo صافي شراء/بيع أجانب أو مؤسسات أو Net Flow لأن مصدرًا موثوقًا لهذه البيانات غير متصل حاليًا.",
        "المعروض مقياس نسبي من OHLCV/حجم التداول للأسهم التي يحللها المحرك فقط.",
    ]
    return "\n".join(lines)


def _sectors_text(runtime):
    snapshot = runtime.get("pro_engine_snapshot") or {}
    rows = _sector_rows(runtime)
    lines = [
        "🗺️ <b>ترتيب القطاعات — عينة ReFo</b>",
        f"📡 {_quote_label(snapshot)}",
        "",
    ]
    if not rows:
        lines.append("لا توجد بيانات قطاعات كافية في آخر Snapshot.")
        return "\n".join(lines)
    for i, x in enumerate(rows[:10], 1):
        trust = "⚠️ عينة ضعيفة" if x["count"] < 2 else ""
        lines.append(
            f"{i}. <b>{x['sector']}</b> · {x['count']} سهم {trust}\n"
            f"   Score {_num(x['score'])} · Mom5 {_num(x['mom'], 2)}% · Liq {_num(x['liq'])}"
        )
    lines.extend([
        "",
        "ℹ️ الترتيب إحصائي داخل universe المتاح فقط؛ القطاع ذو سهم واحد لا يُعلن كـ«الأقوى» بثقة.",
    ])
    return "\n".join(lines)


def apply(base):
    """Add honest sample-based market, liquidity and sector screens."""
    original_handle = base.handle
    bot_experience.MARKET_MENU = MARKET_MENU

    def send(chat_id, text):
        bot_experience._send_keyboard(base, text, chat_id, MARKET_MENU)

    def enhanced_handle(chat_id, text, state):
        text = (text or "").strip()
        if text in ("🗺️ السوق والقطاعات", "📈 ملخص السوق"):
            state.pop("awaiting", None)
            send(chat_id, _market_text(_runtime(base)))
            return True
        if text == "💧 سيولة العينة":
            state.pop("awaiting", None)
            send(chat_id, _liquidity_text(_runtime(base)))
            return True
        if text in ("🗺️ ترتيب القطاعات", "🗺️ أداء القطاعات"):
            state.pop("awaiting", None)
            send(chat_id, _sectors_text(_runtime(base)))
            return True
        return original_handle(chat_id, text, state)

    base.handle = enhanced_handle
    return base


def self_test():
    runtime = {
        "pro_engine_snapshot": {
            "quote_mode": "DELAYED_EVALUATION",
            "quote_source": "daily OHLCV",
            "top": [
                {"symbol": "A", "price": 10, "sector": "عقارات", "score": 80, "momentum_5d": 2, "liquidity_score": 70, "volume_ratio": 1.2},
                {"symbol": "B", "price": 20, "sector": "عقارات", "score": 60, "momentum_5d": -1, "liquidity_score": 50, "volume_ratio": 0.8},
                {"symbol": "C", "price": 30, "sector": "بنوك", "score": 90, "momentum_5d": 3, "liquidity_score": 80, "volume_ratio": 1.5},
            ],
        }
    }
    m = _market_metrics(runtime)
    assert m["count"] == 3 and round(m["breadth"], 1) == 66.7
    assert "Net Flow" in _liquidity_text(runtime)
    sectors = _sector_rows(runtime)
    assert any(x["sector"] == "عقارات" and x["count"] == 2 for x in sectors)
    text = _sectors_text(runtime)
    assert "عينة ReFo" in text and "الأقوى" in text
    print("bot market self-test: PASS")


if __name__ == "__main__":
    self_test()
