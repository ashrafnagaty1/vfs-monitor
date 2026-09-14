import base from "./index.js";

const WORKER_VERSION = "market-terminal-v4.0-pro-tv-2026";
const DASHBOARD_URL = "https://vfs-monitor.folkhero3.workers.dev/dashboard";

const SECTORS = {
  ORHD: "عقارات", TMGH: "عقارات", MASR: "عقارات", PHDC: "عقارات", HELI: "عقارات",
  ETEL: "اتصالات", FWRY: "مدفوعات وتكنولوجيا مالية", EFIH: "مدفوعات وتكنولوجيا مالية",
  POUL: "أغذية", JUFO: "أغذية", DOMT: "أغذية", ZEOT: "أغذية", KABO: "منسوجات", ORWE: "منسوجات",
  SKPC: "بتروكيماويات", ABUK: "أسمدة وكيماويات", MFPC: "أسمدة وكيماويات", CCAP: "استثمارات",
  ALCN: "نقل ولوجستيات", SWDY: "صناعة ومعدات", COMI: "بنوك", CIEB: "بنوك", ADIB: "بنوك",
  EPCO: "رعاية صحية", CLHO: "رعاية صحية", ISPH: "رعاية صحية"
};

function esc(v) { return String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function n(v, d = 2) { const x = Number(v); return Number.isFinite(x) ? x.toFixed(d) : "-"; }

async function tg(env, chat, text, extra = {}) {
  const r = await fetch(`https://api.telegram.org/bot${env.TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text, parse_mode: "HTML", disable_web_page_preview: true, ...extra })
  });
  return r.ok;
}

function dashboardHtml() {
  return `<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#06090e">
  <title>EGX Pro Terminal</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #06080c; color: #d0dbe5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, sans-serif; font-size: 11px; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    
    /* Top Header */
    header { background: #0b0f15; border-bottom: 1px solid #1a222c; padding: 6px 12px; display: flex; align-items: center; justify-content: space-between; min-height: 38px; }
    .brand { font-weight: 900; color: #fff; font-size: 13px; display: flex; align-items: center; gap: 8px; }
    .brand span { color: #00e676; font-size: 10px; background: #003314; padding: 2px 6px; border-radius: 4px; border: 1px solid #005a24; }
    .stats-bar { display: flex; gap: 8px; }
    .stat-pill { background: #111720; border: 1px solid #202b38; padding: 3px 8px; border-radius: 4px; font-size: 10px; color: #8fa2b5; }
    .stat-pill b { color: #fff; margin-right: 4px; }

    /* Main Grid Layout */
    .terminal-body { display: grid; grid-template-columns: 280px 1fr 300px; flex: 1; height: calc(100vh - 66px); direction: ltr; }
    
    /* Left: Technical Analysis & Signals */
    .left-panel { background: #080c11; border-right: 1px solid #1a222c; direction: rtl; padding: 10px; overflow-y: auto; }
    .stock-title { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #1a232e; padding-bottom: 8px; }
    .stock-title h1 { font-size: 24px; color: #fff; font-weight: 900; }
    .stock-title .cur-price { font-size: 22px; font-weight: 800; }
    
    .kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin: 10px 0; }
    .kpi-card { background: #0e141c; border: 1px solid #1c2735; padding: 6px 8px; border-radius: 4px; }
    .kpi-card small { color: #6e8294; display: block; font-size: 9px; }
    .kpi-card b { color: #fff; font-size: 12px; margin-top: 2px; display: block; }
    
    .signal-box { background: #0e1724; border: 1px solid #233448; border-radius: 5px; padding: 8px; margin-top: 10px; line-height: 1.6; }
    .signal-box b { color: #4fa3ff; }

    /* Center: TradingView Chart */
    .center-panel { background: #040609; position: relative; display: flex; flex-direction: column; min-width: 0; }
    #tv_chart { width: 100%; height: 100%; flex: 1; }

    /* Right: Market Watchlist */
    .right-panel { background: #090d13; border-left: 1px solid #1a222c; direction: rtl; display: flex; flex-direction: column; overflow: hidden; }
    .panel-header { padding: 8px 10px; border-bottom: 1px solid #1a222c; font-weight: 800; color: #fff; display: flex; justify-content: space-between; align-items: center; }
    .watch-table-header { display: grid; grid-template-columns: 1.2fr 0.9fr 0.7fr 0.7fr; padding: 6px 8px; background: #0d131a; border-bottom: 1px solid #1a222c; color: #6a7c8d; font-weight: bold; font-size: 9px; }
    .watch-list { flex: 1; overflow-y: auto; }
    .watch-item { display: grid; grid-template-columns: 1.2fr 0.9fr 0.7fr 0.7fr; padding: 8px; border-bottom: 1px solid #121820; align-items: center; cursor: pointer; text-decoration: none; color: inherit; }
    .watch-item:hover, .watch-item.active { background: #131c26; }
    .watch-item .sym { font-weight: 800; color: #fff; }
    .watch-item .sym small { display: block; font-size: 8px; color: #627586; font-weight: normal; }
    .watch-item .val { font-family: monospace; }
    
    /* Bottom Ticker */
    footer { height: 28px; background: #070a0e; border-top: 1px solid #19212a; display: flex; align-items: center; padding: 0 10px; overflow: hidden; white-space: nowrap; font-family: monospace; font-size: 10px; gap: 16px; }

    .up { color: #00e676; }
    .down { color: #ff5252; }
  </style>
</head>
<body>
  <header>
    <div class="brand">EGX SMART TERMINAL <span id="sess-status">متصل</span></div>
    <div class="stats-bar">
      <div class="stat-pill">السوق: <b id="regime">—</b></div>
      <div class="stat-pill">Breadth: <b id="breadth">—</b></div>
      <div class="stat-pill">Avg Score: <b id="avgscore">—</b></div>
    </div>
  </header>

  <div class="terminal-body">
    <!-- Left Details -->
    <aside class="left-panel">
      <div class="stock-title">
        <h1 id="det-sym">COMI</h1>
        <div class="cur-price" id="det-price">0.00</div>
      </div>
      <div class="kpi-grid">
        <div class="kpi-card"><small>الدخول (Trigger)</small><b id="det-trg">-</b></div>
        <div class="kpi-card"><small>وقف الخسارة (Stop)</small><b id="det-stop" class="down">-</b></div>
        <div class="kpi-card"><small>الهدف الأول (T1)</small><b id="det-t1" class="up">-</b></div>
        <div class="kpi-card"><small>الهدف الثاني (T2)</small><b id="det-t2" class="up">-</b></div>
        <div class="kpi-card"><small>RSI / ADX</small><b id="det-tech">-</b></div>
        <div class="kpi-card"><small>حجم السيولة</small><b id="det-vol">-</b></div>
      </div>
      <div class="signal-box">
        <div><b>النمط الفني:</b> <span id="det-setup">—</span></div>
        <div style="margin-top:4px;"><b>الأسباب:</b> <span id="det-why">—</span></div>
        <div style="margin-top:4px;"><b>الدعم والمقاومة:</b> <span id="det-sr">—</span></div>
      </div>
    </aside>

    <!-- Center Chart -->
    <main class="center-panel">
      <div id="tv_chart"></div>
    </main>

    <!-- Right Watchlist -->
    <aside class="right-panel">
      <div class="panel-header">
        <span>قائمة الأسهم المتابعة</span>
        <small id="stock-count">0 سهم</small>
      </div>
      <div class="watch-table-header">
        <span>السهم</span>
        <span>السعر</span>
        <span>السيولة</span>
        <span>Score</span>
      </div>
      <div class="watch-list" id="watchlist">
        <!-- Rows dynamically injected -->
      </div>
    </aside>
  </div>

  <footer id="ticker">
    <span>تحميل شريط الأسعار...</span>
  </footer>

  <script>
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }

    var CURRENT_SYM = "COMI";
    var RAW_DATA = null;

    function renderTradingView(symbol) {
      document.getElementById("tv_chart").innerHTML = "";
      new TradingView.widget({
        "autosize": true,
        "symbol": "EGX:" + symbol,
        "interval": "D",
        "timezone": "Africa/Cairo",
        "theme": "dark",
        "style": "1",
        "locale": "ar_AE",
        "toolbar_bg": "#080c11",
        "enable_publishing": false,
        "allow_symbol_change": false,
        "container_id": "tv_chart",
        "studies": [
          "MASimple@tv-basicstudies",
          "Volume@tv-basicstudies"
        ]
      });
    }

    function selectStock(sym) {
      CURRENT_SYM = sym;
      renderTradingView(sym);
      updateDetails(sym);
      
      var items = document.querySelectorAll('.watch-item');
      items.forEach(function(el) {
        el.classList.toggle('active', el.getAttribute('data-s') === sym);
      });
    }

    function updateDetails(sym) {
      if (!RAW_DATA) return;
      var list = RAW_DATA.snapshot.details || RAW_DATA.snapshot.top || [];
      var t = list.find(function(x){ return x.symbol === sym; }) || {};
      var plans = RAW_DATA.plans || [];
      var p = plans.find(function(x){ return x.symbol === sym; }) || {};

      document.getElementById("det-sym").textContent = sym;
      document.getElementById("det-price").textContent = Number(t.price || 0).toFixed(2);
      document.getElementById("det-trg").textContent = p.trigger ? Number(p.trigger).toFixed(2) : "-";
      document.getElementById("det-stop").textContent = (p.dynamic_stop || p.initial_stop || t.stop) ? Number(p.dynamic_stop || p.initial_stop || t.stop).toFixed(2) : "-";
      document.getElementById("det-t1").textContent = (p.target1 || t.target1) ? Number(p.target1 || t.target1).toFixed(2) : "-";
      document.getElementById("det-t2").textContent = (p.target2 || t.target2) ? Number(p.target2 || t.target2).toFixed(2) : "-";
      document.getElementById("det-tech").textContent = (t.rsi ? Number(t.rsi).toFixed(1) : "-") + " / " + (t.adx ? Number(t.adx).toFixed(1) : "-");
      document.getElementById("det-vol").textContent = t.volume_ratio ? (Number(t.volume_ratio).toFixed(1) + "x") : "-";
      document.getElementById("det-setup").textContent = (t.setups && t.setups.length) ? t.setups.join(" + ") : "اتجاه عام";
      document.getElementById("det-why").textContent = (t.why && t.why.length) ? t.why.join(" • ") : "متابعة سيولة";
      document.getElementById("det-sr").textContent = "S: " + (t.support_20 || "-") + " | R: " + (t.resistance_20 || "-");
    }

    async function loadData() {
      try {
        var res = await fetch("/dashboard-state?t=" + Date.now(), { cache: "no-store" });
        var data = await res.json();
        if (!data.ok || !data.snapshot) return;
        RAW_DATA = data;

        var snap = data.snapshot;
        document.getElementById("regime").textContent = (snap.market_regime && snap.market_regime.name) || "-";
        document.getElementById("breadth").textContent = (snap.market_regime && snap.market_regime.breadth ? Number(snap.market_regime.breadth).toFixed(1) + "%" : "-");
        document.getElementById("avgscore").textContent = (snap.market_regime && snap.market_regime.avg_score ? Number(snap.market_regime.avg_score).toFixed(0) : "-");

        var top = snap.top || [];
        document.getElementById("stock-count").textContent = top.length + " سهم";
        
        var container = document.getElementById("watchlist");
        container.innerHTML = "";
        
        var tickerHtml = "";

        top.forEach(function(stock, idx) {
          var row = document.createElement("div");
          row.className = "watch-item" + (stock.symbol === CURRENT_SYM ? " active" : "");
          row.setAttribute("data-s", stock.symbol);
          row.onclick = function() { selectStock(stock.symbol); };

          row.innerHTML = 
            '<div class="sym">' + stock.symbol + '<small>' + (stock.score || 0) + ' pts</small></div>' +
            '<div class="val">' + Number(stock.price || 0).toFixed(2) + '</div>' +
            '<div class="val ' + (stock.volume_ratio >= 1.2 ? 'up' : '') + '">' + Number(stock.volume_ratio || 0).toFixed(1) + 'x</div>' +
            '<div class="val">' + Number(stock.score || 0).toFixed(0) + '</div>';
          
          container.appendChild(row);

          tickerHtml += '<span><b>' + stock.symbol + '</b>: ' + Number(stock.price || 0).toFixed(2) + '</span>';
        });

        document.getElementById("ticker").innerHTML = tickerHtml;

        if (!CURRENT_SYM && top.length > 0) {
          selectStock(top[0].symbol);
        } else {
          updateDetails(CURRENT_SYM);
        }

      } catch (e) {
        console.error("Fetch failed", e);
      }
    }

    window.addEventListener("DOMContentLoaded", function() {
      renderTradingView(CURRENT_SYM);
      loadData();
      setInterval(loadData, 25000);
    });
  </script>
</body>
</html>`;
}

export default {
  async fetch(req, env, ctx) {
    const u = new URL(req.url);

    if (req.method === "GET" && u.pathname === "/sector-version") {
      return Response.json({ ok: true, worker_version: WORKER_VERSION, main: "src/sector_enhanced.js", state_binding: !!env.STATE });
    }

    if (req.method === "GET" && u.pathname === "/dashboard") {
      return new Response(dashboardHtml(), {
        headers: { "content-type": "text/html; charset=UTF-8", "cache-control": "no-store, no-cache, must-revalidate" }
      });
    }

    if (req.method === "GET" && (u.pathname === "/dashboard-state" || u.pathname === "/api/state")) {
      if (!env.STATE) return Response.json({ ok: false, error: "STATE_binding_missing" }, { status: 500 });
      try {
        const raw = await env.STATE.get("latest");
        if (!raw) return Response.json({ ok: false, error: "KV_latest_missing" }, { status: 503 });
        const s = JSON.parse(raw);
        return Response.json({
          ok: true,
          snapshot: s.pro_engine_snapshot || {},
          plans: Array.isArray(s?.trade_lifecycle?.plans) ? s.trade_lifecycle.plans : [],
          alerts: Array.isArray(s?.trade_alerts) ? s.trade_alerts.slice(-20) : []
        });
      } catch (e) {
        return Response.json({ ok: false, error: "state_parse_failed" }, { status: 500 });
      }
    }

    if (req.method === "POST" && u.pathname === "/telegram") {
      let body;
      try { body = await req.clone().json(); } catch (_) { body = null; }
      const text = body?.message?.text, chat = body?.message?.chat?.id;

      if (text === "📊 الشاشة اللحظية" && (!env.CHAT_ID || String(chat) === String(env.CHAT_ID))) {
        await tg(env, chat, "📊 <b>EGX Smart Terminal Pro</b>\nافتح الشاشة التفاعلية الحية من الزر أدناه:", {
          reply_markup: {
            inline_keyboard: [[{ text: "🚀 فتح الشاشة اللحظية", web_app: { url: DASHBOARD_URL } }]]
          }
        });
        return Response.json({ ok: true, feature: "market-terminal-v4.0" });
      }
    }

    return base.fetch(req, env, ctx);
  }
};
