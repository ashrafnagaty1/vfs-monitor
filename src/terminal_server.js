import enhanced from "./sector_enhanced.js";

const VERSION = "market-terminal-v5.2-egx-pro-layout-2026-09-14";
const DASHBOARD_URL = "https://vfs-monitor.folkhero3.workers.dev/dashboard";

function esc(v) { 
  return String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); 
}

function n(v, d = 2) { 
  const x = Number(v); 
  return Number.isFinite(x) ? x.toFixed(d) : "-"; 
}

function sessionLabel(s) { 
  return ({ SESSION: "🟢 مفتوح", PRE_MARKET: "🟠 ما قبل الجلسة", CLOSED: "⚫ مغلق", WEEKEND: "🔒 عطلة" }[s] || s || "-"); 
}

async function tg(env, chat, text, extra = {}) {
  const r = await fetch(`https://api.telegram.org/bot${env.TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text, parse_mode: "HTML", disable_web_page_preview: true, ...extra })
  });
  return r.ok;
}

const SECTOR_MAP = {
  ORHD: "عقارات", TMGH: "عقارات", MASR: "عقارات", PHDC: "عقارات", HELI: "عقارات",
  ETEL: "اتصالات", FWRY: "تكنولوجيا مالية", EFIH: "تكنولوجيا مالية",
  POUL: "أغذية", ZEOT: "أغذية", JUFO: "أغذية", KABO: "منسوجات",
  SKPC: "بتروكيماويات", CCAP: "استثمارات", ALCN: "نقل", SWDY: "صناعة",
  COMI: "بنوك", ADIB: "بنوك", EPCO: "رعاية صحية"
};

function sectorChips(top) {
  const g = {};
  top.forEach(t => { 
    const s = SECTOR_MAP[t.symbol] || "أخرى"; 
    (g[s] ??= []).push(t); 
  });
  return Object.entries(g).map(([s, a]) => {
    const sc = a.reduce((x, z) => x + Number(z.score || 0), 0) / a.length;
    const m = a.reduce((x, z) => x + Number(z.momentum_5d || 0), 0) / a.length;
    return `<span class="sector ${m >= 0 ? 'pos' : 'neg'}">${esc(s)} <b>${n(sc, 0)}</b> <i>${m >= 0 ? '▲' : '▼'} ${n(Math.abs(m), 1)}%</i></span>`;
  }).join("");
}

function watchRows(top, pmap, sym) {
  return top.map(z => {
    const pp = pmap[String(z.symbol).toUpperCase()] || {};
    const st = pp.status || "WATCH";
    const active = z.symbol === sym ? "active" : "";
    const liq = Number(z.liquidity_score || 0);
    const mom = Number(z.momentum_5d || 0);
    return `<a class="watchrow ${active}" href="/dashboard?s=${encodeURIComponent(z.symbol)}">
      <span class="wname">${esc(z.symbol)}<small>${esc(SECTOR_MAP[z.symbol] || '')}</small></span>
      <span class="wprice ${mom >= 0 ? 'green' : 'red'}">${n(z.price)}</span>
      <span class="wvol"><b>${n(z.volume_ratio)}x</b><i><em style="width:${Math.max(4, Math.min(100, Number(z.volume_ratio || 0) * 28))}%"></em></i></span>
      <span class="wliq">${n(liq, 0)}%</span>
      <span class="wstatus ${st === 'ENTRY' ? 'green' : 'amber'}">${esc(st)}</span>
    </a>`;
  }).join("");
}

function page(state, selected) {
  const x = state?.pro_engine_snapshot || {};
  const top = Array.isArray(x.top) ? x.top : [];
  const details = Array.isArray(x.details) ? x.details : top;
  const plans = Array.isArray(state?.trade_lifecycle?.plans) ? state.trade_lifecycle.plans : [];
  const pmap = Object.fromEntries(plans.map(p => [String(p.symbol || "").toUpperCase(), p]));
  
  const sym = (selected && details.some(t => String(t.symbol).toUpperCase() === selected.toUpperCase()))
    ? selected.toUpperCase()
    : (top[0]?.symbol || "COMI");
    
  const t = details.find(z => String(z.symbol).toUpperCase() === sym) || {};
  const p = pmap[sym] || {};
  const r = x.market_regime || {};
  const ses = x.market_session || {};
  const live = x.quote_mode === "LIVE";
  const change = Number(t.momentum_5d || 0);
  const cclass = change >= 0 ? "green" : "red";
  const why = Array.isArray(t.why) && t.why.length ? t.why.join(" • ") : "—";
  const setups = Array.isArray(t.setups) && t.setups.length ? t.setups.join(" + ") : "—";
  const rr = Number(p.rr_to_t1_now || 0);
  const dist = Number(p.distance_to_trigger_pct || 0);
  const ready = dist <= 1 && Number(t.score || 0) >= 75 && rr >= 1.4 && Number(t.volume_ratio || 0) >= 1.1 && Number(t.adx || 0) >= 20;

  return `<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#06080b">
  <title>EGX Professional Terminal</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; background: #080b0f; color: #dce3ea; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, sans-serif; font-size: 11px; overflow: hidden; }
    .top { background: #0c1015; border-bottom: 1px solid #1c222b; }
    .bar { height: 40px; display: flex; align-items: center; gap: 10px; padding: 0 12px; }
    .brand { font-size: 14px; font-weight: 800; color: #fff; margin-left: auto; letter-spacing: .3px; }
    .brand small { display: block; color: #6f8090; font-size: 8px; font-weight: 400; }
    .badge { padding: 4px 8px; border: 1px solid #232c37; border-radius: 4px; background: #121820; color: #9bb0c4; font-size: 10px; }
    .badge.hot { color: #ffd166; border-color: #5b4618; }
    .indices { display: grid; grid-template-columns: repeat(6, 1fr); gap: 1px; background: #1b232c; border-bottom: 1px solid #1c222b; }
    .idx { background: #0c1015; padding: 5px 8px; text-align: center; }
    .idx small { color: #687989; font-size: 9px; }
    .idx b { display: block; color: #fff; font-size: 12px; margin-top: 2px; }
    .sectorbar { display: flex; gap: 6px; padding: 5px 8px; overflow-x: auto; white-space: nowrap; background: #090d12; border-bottom: 1px solid #181f27; }
    .sector { background: #11171f; border: 1px solid #202b38; padding: 3px 7px; border-radius: 10px; color: #9bb0c4; font-size: 10px; }
    .sector b { color: #5ea4ff; }
    .sector.pos i { color: #2ecc71; font-style: normal; }
    .sector.neg i { color: #e74c3c; font-style: normal; }
    
    .shell { display: grid; grid-template-columns: 40px 270px 1fr 310px; height: calc(100vh - 134px); direction: ltr; }
    .rail, .left, .center, .right { background: #090d12; border-right: 1px solid #1a222b; direction: rtl; }
    .rail { direction: ltr; display: flex; flex-direction: column; align-items: center; padding-top: 6px; gap: 4px; background: #070a0e; border-right: 1px solid #161c24; }
    .rail span, .rail a { width: 30px; height: 30px; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #6e8194; text-decoration: none; border: 1px solid transparent; }
    .rail .on, .rail a:hover { background: #132438; color: #4da3ff; border-color: #1e3a5a; }
    
    .left { padding: 10px; overflow-y: auto; }
    .stockhead { padding-bottom: 8px; border-bottom: 1px solid #1a222b; }
    .symbol { font-size: 22px; font-weight: 800; color: #fff; }
    .price { font-size: 22px; font-weight: 700; margin-top: 2px; }
    .change { font-size: 11px; font-weight: 600; }
    .green { color: #2ecc71; }
    .red { color: #e74c3c; }
    .amber { color: #f1c40f; }
    .chips { margin-top: 6px; }
    .chip { display: inline-block; background: #121820; border: 1px solid #202c3a; border-radius: 3px; padding: 3px 6px; margin: 2px 2px 2px 0; color: #9bb0c4; font-size: 10px; }
    .chip.blue { color: #5ea4ff; }
    .tradebtns { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 8px; }
    .tradebtn { padding: 6px; text-align: center; border-radius: 3px; font-weight: 700; font-size: 10px; cursor: pointer; }
    .buy { background: #0e4c34; color: #72f0b7; border: 1px solid #187350; }
    .sell { background: #4e171b; color: #ffa2a8; border: 1px solid #752329; }
    .mini-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 8px; }
    .mini { background: #0e1319; border: 1px solid #19222c; padding: 6px; border-radius: 3px; }
    .mini small { color: #6c7e8f; display: block; font-size: 9px; }
    .mini b { display: block; margin-top: 2px; color: #fff; font-size: 11px; }
    
    .center { display: flex; flex-direction: column; min-width: 0; position: relative; background: #06080b; }
    #tradingview_box { width: 100%; flex: 1; min-height: 100%; position: relative; }
    
    .right { overflow-y: auto; background: #0a0e13; border-left: 1px solid #1a222b; }
    .watchtitle { height: 36px; padding: 9px 10px; border-bottom: 1px solid #1a222b; font-weight: 800; color: #fff; display: flex; justify-content: space-between; align-items: center; }
    .filters { display: flex; gap: 3px; padding: 6px; border-bottom: 1px solid #171f28; }
    .filter { flex: 1; text-align: center; padding: 4px 0; border-radius: 3px; background: #11171f; color: #788b9c; text-decoration: none; font-size: 9px; }
    .filter.on { background: #17375e; color: #6db1ff; font-weight: bold; }
    .whead, .watchrow { display: grid; grid-template-columns: 1.2fr 0.9fr 0.9fr 0.6fr 0.7fr; align-items: center; gap: 4px; padding: 6px 8px; }
    .whead { color: #586978; border-bottom: 1px solid #161c24; font-size: 9px; font-weight: 600; }
    .watchrow { min-height: 38px; border-bottom: 1px solid #131920; color: #c4d0dc; text-decoration: none; }
    .watchrow:hover, .watchrow.active { background: #121a24; }
    .wname { font-weight: 800; color: #fff; }
    .wname small { display: block; font-size: 8px; color: #5d6f80; font-weight: 400; }
    .wvol b { display: block; font-size: 9px; }
    .wvol i { display: block; height: 3px; background: #1b232c; margin-top: 2px; }
    .wvol em { display: block; height: 3px; background: #2ecc71; }
    
    .ticker { position: fixed; bottom: 0; left: 0; right: 0; height: 26px; background: #080c10; border-top: 1px solid #1c242e; display: flex; gap: 20px; align-items: center; padding: 0 10px; overflow: hidden; white-space: nowrap; z-index: 10; font-family: monospace; font-size: 10px; }
    .ticker b { color: #fff; }
    
    @media (max-width: 900px) {
      .shell { grid-template-columns: 1fr; height: auto; }
      .rail { display: none; }
      .center { height: 480px; }
      .right { height: 420px; }
    }
  </style>
</head>
<body>
  <div class="top">
    <div class="bar">
      <div class="brand">EGX PROFESSIONAL TERMINAL<small>Direct Market Intelligence</small></div>
      <span class="badge hot">السوق ${esc(sessionLabel(ses.status))}</span>
      <span class="badge">${esc(r.name || "-")}</span>
      <span class="badge">Breadth ${n(r.breadth, 1)}%</span>
    </div>
    <div class="indices">
      <div class="idx"><small>EGX30 Proxy</small><b>${esc(r.name || "-")}</b></div>
      <div class="idx"><small>Market Breadth</small><b>${n(r.breadth, 1)}%</b></div>
      <div class="idx"><small>Avg Score</small><b>${n(r.avg_score, 1)}</b></div>
      <div class="idx"><small>Avg Mom 5D</small><b>${n(r.avg_mom, 2)}%</b></div>
      <div class="idx"><small>Universe</small><b>${n(x.count, 0)}</b></div>
      <div class="idx"><small>Data Mode</small><b>${live ? 'LIVE' : 'EVAL'}</b></div>
    </div>
    <div class="sectorbar">${sectorChips(top)}</div>
  </div>

  <div class="shell">
    <nav class="rail">
      <span class="on">▦</span>
      <a href="/dashboard">⌂</a>
      <span>⌕</span>
      <span>☆</span>
      <span>⚡</span>
    </nav>

    <aside class="left">
      <div class="stockhead">
        <div class="symbol">${esc(sym)}</div>
        <div class="price">${n(t.price)} <span class="change ${cclass}">${change >= 0 ? "▲" : "▼"} ${n(Math.abs(change), 2)}%</span></div>
        <div class="chips">
          <span class="chip blue">Score ${n(t.score, 0)}</span>
          <span class="chip">${esc(t.confidence || "-")}</span>
          <span class="chip">${esc(p.status || "WATCH")}</span>
        </div>
        <div class="tradebtns">
          <div class="tradebtn buy">شراء / مراقبة</div>
          <div class="tradebtn sell">خروج / وقف</div>
        </div>
      </div>
      
      <div class="mini-grid">
        <div class="mini"><small>RSI (14)</small><b>${n(t.rsi, 1)}</b></div>
        <div class="mini"><small>ADX (Trend)</small><b>${n(t.adx, 1)}</b></div>
        <div class="mini"><small>MFI (Flow)</small><b>${n(t.mfi, 1)}</b></div>
        <div class="mini"><small>Volume Ratio</small><b>${n(t.volume_ratio)}x</b></div>
        <div class="mini"><small>Trigger Entry</small><b>${n(p.trigger)}</b></div>
        <div class="mini"><small>Dynamic Stop</small><b>${n(p.dynamic_stop ?? p.initial_stop ?? t.stop)}</b></div>
        <div class="mini"><small>Target T1</small><b>${n(p.target1 ?? t.target1)}</b></div>
        <div class="mini"><small>Target T2</small><b>${n(p.target2 ?? t.target2)}</b></div>
        <div class="mini"><small>Support (S1)</small><b>${n(t.support_20)}</b></div>
        <div class="mini"><small>Resistance (R1)</small><b>${n(t.resistance_20)}</b></div>
      </div>
      
      <div style="margin-top:10px;padding:8px;background:#0e141a;border:1px solid #1a242e;border-radius:3px;line-height:1.6">
        <b>النمط الفني:</b> ${esc(setups)}<br>
        <b>الأسباب:</b> ${esc(why)}<br>
        <b>المنطقة الذهبية:</b> ${t.golden ? `${n(t.golden_low)} - ${n(t.golden_high)}` : "غير مفعلة"}
      </div>
    </aside>

    <section class="center">
      <div id="tradingview_box"></div>
    </section>

    <aside class="right">
      <div class="watchtitle">
        <span>قائمة الأسهم / Market</span>
        <span style="font-size:10px;color:#607180">${top.length} سهم</span>
      </div>
      <div class="filters">
        <a class="filter on" href="#">الكل</a>
        <a class="filter" href="#">المضاربة</a>
        <a class="filter" href="#">السيولة</a>
      </div>
      <div class="whead">
        <span>الرمز</span>
        <span>السعر</span>
        <span>الحجم</span>
        <span>السيولة</span>
        <span>الحالة</span>
      </div>
      ${watchRows(top, pmap, sym) || '<div style="padding:20px;color:#5c6e7e;text-align:center">لا توجد بيانات</div>'}
    </aside>
  </div>

  <div class="ticker">
    ${top.slice(0, 15).map(z => `<span><b>${esc(z.symbol)}</b>: ${n(z.price)} <span class="${Number(z.momentum_5d) >= 0 ? 'green' : 'red'}">${Number(z.momentum_5d) >= 0 ? '▲' : '▼'}${n(Math.abs(Number(z.momentum_5d || 0)), 1)}%</span></span>`).join("")}
  </div>

  <script>
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }

    function initTV() {
      if (typeof TradingView === "undefined") return;
      new TradingView.widget({
        "autosize": true,
        "symbol": "EGX:${sym}",
        "interval": "D",
        "timezone": "Africa/Cairo",
        "theme": "dark",
        "style": "1",
        "locale": "ar_AE",
        "toolbar_bg": "#090d12",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "save_image": false,
        "container_id": "tradingview_box",
        "studies": [
          "MASimple@tv-basicstudies",
          "Volume@tv-basicstudies"
        ]
      });
    }

    window.addEventListener("DOMContentLoaded", initTV);
  </script>
</body>
</html>`;
}

export default {
  async fetch(req, env, ctx) {
    const u = new URL(req.url);
    if (req.method === "GET" && u.pathname === "/dashboard") {
      let state = null;
      try {
        state = env.STATE ? await env.STATE.get("latest", "json") : null;
      } catch (_) {
        state = null;
      }
      if (!state?.pro_engine_snapshot) {
        return new Response(`<!doctype html><meta charset="utf-8"><body style="background:#06090d;color:white;font-family:Tahoma;padding:30px;direction:rtl"><h2>EGX SMART TERMINAL</h2><p>تعذر قراءة Snapshot من KV.</p><p>الإصدار: ${VERSION}</p></body>`, {
          status: 503,
          headers: { "content-type": "text/html; charset=UTF-8", "cache-control": "no-store" }
        });
      }
      return new Response(page(state, u.searchParams.get("s") || ""), {
        headers: { "content-type": "text/html; charset=UTF-8", "cache-control": "no-store" }
      });
    }

    if (req.method === "GET" && u.pathname === "/terminal-status") {
      let raw = null;
      try {
        raw = env.STATE ? await env.STATE.get("latest") : null;
      } catch (_) {
        raw = null;
      }
      return Response.json({
        ok: true,
        version: VERSION,
        state_binding: !!env.STATE,
        has_raw_state: !!raw,
        raw_size: raw ? raw.length : 0
      });
    }

    if (req.method === "POST" && u.pathname === "/telegram") {
      let body = null;
      try {
        body = await req.clone().json();
      } catch (_) {
        body = null;
      }
      const text = body?.message?.text, chat = body?.message?.chat?.id;
      if (text === "📊 الشاشة اللحظية" && (!env.CHAT_ID || String(chat) === String(env.CHAT_ID))) {
        await tg(env, chat, "📊 <b>EGX Terminal Pro</b>\nمنصة التداول والتحليل المتقدمة متاحة الآن!\nاضغط على الزر أدناه لفتح الشاشة اللحظية.", {
          reply_markup: {
            inline_keyboard: [[{ text: "🚀 فتح الشاشة اللحظية", web_app: { url: DASHBOARD_URL } }]]
          }
        });
        return Response.json({ ok: true, feature: "market-terminal-v5.2", version: VERSION });
      }
    }

    return enhanced.fetch(req, env, ctx);
  }
};
