import base from "./index.js";

const WORKER_VERSION = "market-terminal-v12-integrity-2026";
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
  <title>ReFo . EGX Smart Trader</title>
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

    .market-ribbon{height:25px;display:flex;align-items:center;gap:5px;padding:3px 8px;background:#080d13;border-bottom:1px solid #17212b;overflow-x:auto;white-space:nowrap;direction:ltr}.market-ribbon span{border:1px solid #1c2934;background:#0d141c;padding:2px 6px;color:#718697;font-size:8px}.market-ribbon b{color:#dce7ef;margin-left:3px}.market-ribbon em{font-style:normal;color:#526576;font-size:8px}.chart-toolbar{height:28px;display:flex;align-items:center;gap:3px;padding:3px 7px;background:#070b10;border-bottom:1px solid #17212b;direction:ltr}.chart-toolbar b{color:#fff;margin-right:6px}.chart-toolbar button{background:#0d141c;border:1px solid #1d2934;color:#718596;padding:3px 6px;font-size:8px}.chart-toolbar button.on{background:#17304a;color:#fff;border-color:#31597c}.chart-toolbar span{margin-left:auto;color:#5f7282;font-size:8px}
    /* Main Grid Layout */
    .terminal-body { display: grid; grid-template-columns: 280px 1fr 300px; flex: 1; height: calc(100vh - 119px); direction: ltr; }
    
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
    .watch-item .val { font-family: monospace; }.fav-star{float:left;color:#66798a;font-size:12px;padding:0 3px}.fav-star.on{color:#ffd54f}
    
    /* Bottom Ticker */
    footer { height: 28px; background: #070a0e; border-top: 1px solid #19212a; display: flex; align-items: center; padding: 0 10px; overflow: hidden; white-space: nowrap; font-family: monospace; font-size: 10px; gap: 16px; }

    .ref-stock-tabs,.market-tabs{display:flex;gap:3px;margin:7px 0}.ref-stock-tabs button,.market-tabs>*{flex:1;background:#0d141c;border:1px solid #1d2a36;color:#8093a5;padding:5px 2px;font-size:8px;text-align:center}.ref-stock-tabs button.active,.market-tabs b{color:#fff;border-color:#35516a;background:#122131}.ref-stock-tabs button:disabled{opacity:.35}.left-context{background:#090f15;border:1px solid #17232d;color:#687d8f;padding:5px 7px;font-size:8px;margin-bottom:5px}.market-tabs>*{cursor:pointer}.market-tabs>.active{color:#fff;border-color:#35516a;background:#122131}.market-search{padding:5px 8px;border-bottom:1px solid #18222c}.market-search input{width:100%;background:#070b10;border:1px solid #24313d;color:#dce8f2;padding:6px 8px;outline:none}.up { color: #00e676; }
    .down { color: #ff5252; }
    .stock-actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:7px}.stock-actions button{border:1px solid #273645;background:#101923;color:#a8b8c6;padding:6px;font:inherit}.stock-actions .buy{color:#5bd98b}.stock-actions .sell{color:#ff6b6b}.stock-actions button:disabled{opacity:.4}.plan-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin:6px 0}.plan-strip span{background:#0c131a;border:1px solid #1c2934;padding:5px;color:#708596;font-size:8px}.plan-strip b{display:block;color:#dce8f2;margin-top:2px}.panel-header em{font-style:normal;color:#607589;font-size:8px}.mobile-nav{display:none}
    @media(max-width:760px){
      body{overflow:auto;height:auto;min-height:100vh;padding-bottom:48px}
      header{position:sticky;top:0;z-index:20;padding:6px 8px;align-items:flex-start}.market-ribbon{height:29px}.chart-toolbar{position:sticky;top:38px;z-index:19;overflow-x:auto}.chart-toolbar span{display:none}.brand{font-size:11px}.stats-bar{overflow-x:auto;max-width:68vw;gap:4px}.stat-pill{white-space:nowrap;padding:3px 5px;font-size:8px}
      .terminal-body{display:flex;flex-direction:column;height:auto;direction:rtl}.center-panel{order:1;height:52vh;min-height:330px}.right-panel{order:2;height:44vh;border:0;border-top:1px solid #1a222c}.left-panel{order:3;border:0;border-top:1px solid #1a222c;padding:8px}
      .stock-title h1{font-size:20px}.stock-title .cur-price{font-size:18px}.kpi-grid{grid-template-columns:repeat(3,1fr)}.kpi-card{padding:5px}.signal-box{margin-bottom:8px}
      footer{display:none}.mobile-nav{position:fixed;display:grid;grid-template-columns:repeat(5,1fr);bottom:0;left:0;right:0;height:46px;background:#080d13;border-top:1px solid #25313c;z-index:30;direction:rtl}.mobile-nav button{background:transparent;border:0;color:#8193a3;font:inherit;font-size:9px}.mobile-nav button.active{color:#4fa3ff;font-weight:800}
      .watch-item,.watch-table-header{grid-template-columns:1.1fr .8fr .7fr .6fr}.market-tabs{margin:4px 8px}.panel-header{padding:6px 8px}
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">ReFo . EGX Smart Trader <span id="sess-status">DATA</span></div>
    <div class="stats-bar">
      <div class="stat-pill">السوق: <b id="regime">—</b></div>
      <div class="stat-pill">Breadth: <b id="breadth">—</b></div>
      <div class="stat-pill">Avg Score: <b id="avgscore">—</b></div><div class="stat-pill">Source: <b id="quote-source">—</b></div><div class="stat-pill">Mode: <b id="quote-mode">—</b></div><div class="stat-pill">Updated: <b id="updated-at">—</b></div>
    </div>
  </header>
  <div class="market-ribbon">
    <span>EGX30 <b>—</b></span><span>EGX70 <b>—</b></span><span>EGX100 <b>—</b></span>
    <span>قيمة التداول <b>—</b></span><span>حجم التداول <b>—</b></span><span>الرابحون <b>—</b></span><span>الخاسرون <b>—</b></span>
    <em>المؤشرات واتساع السوق الرسمي يحتاجان مصدر سوق موثوق</em>
  </div>
  <div class="chart-toolbar"><b id="chart-symbol">COMI</b><button data-tf="1">1m</button><button data-tf="15">15m</button><button data-tf="30">30m</button><button data-tf="60">1h</button><button data-tf="240">4h</button><button class="on" data-tf="D">1D</button><button data-tf="W">1W</button><button data-tf="M">1M</button><span>TradingView</span></div>

  <div class="terminal-body">
    <!-- Left Details -->
    <aside class="left-panel">
      <div class="stock-actions"><button class="sell" disabled>بيع</button><button class="buy" disabled>شراء</button><button id="ai-btn">AI تحليل</button></div><div class="stock-title">
        <h1 id="det-sym">COMI</h1>
        <div class="cur-price" id="det-price">0.00</div>
      </div>
      <div class="ref-stock-tabs"><button class="active" data-lefttab="overview">نظرة عامة</button><button data-lefttab="smart">تحليلات ذكية</button><button disabled>العمق</button><button data-lefttab="trades">الصفقات</button><button disabled>أخبار</button></div><div id="left-context" class="left-context">بيانات ReFo الفنية — منفصلة عن أسعار TradingView المعروضة داخل الشارت.</div><div class="kpi-grid">
        <div class="kpi-card"><small>الدخول (Trigger)</small><b id="det-trg">-</b></div>
        <div class="kpi-card"><small>وقف الخسارة (Stop)</small><b id="det-stop" class="down">-</b></div>
        <div class="kpi-card"><small>الهدف الأول (T1)</small><b id="det-t1" class="up">-</b></div>
        <div class="kpi-card"><small>الهدف الثاني (T2)</small><b id="det-t2" class="up">-</b></div>
        <div class="kpi-card"><small>RSI / ADX</small><b id="det-tech">-</b></div>
        <div class="kpi-card"><small>Volume Ratio</small><b id="det-vol">-</b></div><div class="kpi-card"><small>MFI / Score</small><b id="det-mfi">-</b></div><div class="kpi-card"><small>EMA20 / EMA50</small><b id="det-ema">-</b></div><div class="kpi-card"><small>T3</small><b id="det-t3" class="up">-</b></div>
      </div>
      <div class="plan-strip"><span>الحالة <b id="det-stage">—</b></span><span>RR T1 <b id="det-rr">—</b></span><span>Signal <b id="det-signal">—</b></span></div><div class="signal-box">
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
        <span>Market Watch <em id="watch-mode">ReFo</em></span>
        <small id="stock-count">0 سهم</small>
      </div>
      <div class="market-tabs"><b data-mtab="all">السوق</b><span data-mtab="watch">مضاربة</span><span data-mtab="ideas">التوصيات</span><span data-mtab="fav">المفضلة</span></div><div class="market-search"><input id="market-search" placeholder="بحث بالرمز..."></div><div class="watch-table-header">
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

  <nav class="mobile-nav"><button class="active" data-mobile="market">السوق</button><button data-mobile="alerts">التنبيهات</button><button data-mobile="chart">الشارت</button><button data-mobile="ideas">التوصيات</button><button data-mobile="more">المزيد</button></nav>
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
    var CURRENT_INTERVAL = "D";
    var ACTIVE_MARKET_TAB = "all";
    function favKey(){return "refo_favorites_v1"}
    function favorites(){try{return JSON.parse(localStorage.getItem(favKey())||"[]")}catch(_){return []}}
    function isFav(s){return favorites().includes(s)}
    function toggleFav(s){var a=favorites(),i=a.indexOf(s);if(i>=0)a.splice(i,1);else a.push(s);localStorage.setItem(favKey(),JSON.stringify(a));return a.includes(s)}
    function fmt(v,d){if(v===null||v===undefined||v==="")return "—";var x=Number(v);return Number.isFinite(x)?x.toFixed(d==null?2:d):"—"}
    function present(v){return !(v===null||v===undefined||v==="")}
    function applyMarketFilter(){document.querySelectorAll(".watch-item").forEach(function(row){var p=row.getAttribute("data-plan"),fav=row.getAttribute("data-fav")==="1",q=(document.getElementById("market-search")?.value||"").trim().toUpperCase(),match=!q||String(row.getAttribute("data-s")||"").includes(q);var tab=ACTIVE_MARKET_TAB,visible=tab==="all"||((tab==="watch"||tab==="ideas")&&p==="WATCH")||(tab==="fav"&&fav);row.style.display=match&&visible?"":"none";});}

    function renderTradingView(symbol) {
      document.getElementById("tv_chart").innerHTML = "";
      new TradingView.widget({
        "autosize": true,
        "symbol": "EGX:" + symbol,
        "interval": CURRENT_INTERVAL,
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
      var cs=document.getElementById("chart-symbol");if(cs)cs.textContent=sym;
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
      document.getElementById("det-price").textContent = fmt(t.price,2);
      document.getElementById("det-trg").textContent = p.trigger ? Number(p.trigger).toFixed(2) : "-";
      document.getElementById("det-stop").textContent = (p.dynamic_stop || p.initial_stop || t.stop) ? Number(p.dynamic_stop || p.initial_stop || t.stop).toFixed(2) : "-";
      document.getElementById("det-t1").textContent = (p.target1 || t.target1) ? Number(p.target1 || t.target1).toFixed(2) : "-";
      document.getElementById("det-t2").textContent = (p.target2 || t.target2) ? Number(p.target2 || t.target2).toFixed(2) : "-";
      document.getElementById("det-tech").textContent = (t.rsi ? Number(t.rsi).toFixed(1) : "-") + " / " + (t.adx ? Number(t.adx).toFixed(1) : "-");
      document.getElementById("det-vol").textContent = t.volume_ratio ? (Number(t.volume_ratio).toFixed(1) + "x") : "-";
      document.getElementById("det-mfi").textContent = (t.mfi ? Number(t.mfi).toFixed(1) : "-") + " / " + (t.score ? Number(t.score).toFixed(0) : "-");
      document.getElementById("det-ema").textContent = (t.ema20 ? Number(t.ema20).toFixed(2) : "-") + " / " + (t.ema50 ? Number(t.ema50).toFixed(2) : "-");
      document.getElementById("det-t3").textContent = (p.target3 || t.target3) ? Number(p.target3 || t.target3).toFixed(2) : "-";
      document.getElementById("det-stage").textContent = p.status || p.stage || "—";
      document.getElementById("det-signal").textContent = p.signal_id || "-";
      var e=Number(p.entry_price||p.trigger),st=Number(p.dynamic_stop||p.initial_stop),t1=Number(p.target1),risk=e-st;
      document.getElementById("det-rr").textContent = Number.isFinite(e)&&Number.isFinite(st)&&Number.isFinite(t1)&&risk>0 ? ((t1-e)/risk).toFixed(2)+"R" : "-";
      document.getElementById("det-setup").textContent = (t.setups && t.setups.length) ? t.setups.join(" + ") : "—";
      document.getElementById("det-why").textContent = (t.why && t.why.length) ? t.why.join(" • ") : "—";
      document.getElementById("det-sr").textContent = "S20: " + (t.support_20 || "-") + " · S50: " + (t.support_50 || "-") + " | R20: " + (t.resistance_20 || "-") + " · R50: " + (t.resistance_50 || "-");
    }

    async function loadData() {
      try {
        var res = await fetch("/dashboard-state?t=" + Date.now(), { cache: "no-store" });
        var data = await res.json();
        if (!data.ok || !data.snapshot) return;
        RAW_DATA = data;

        var snap = data.snapshot;
        document.getElementById("regime").textContent = (snap.market_regime && snap.market_regime.name) || "-";
        document.getElementById("quote-source").textContent = snap.quote_source || "-";
        document.getElementById("quote-mode").textContent = snap.quote_mode || "DELAYED_EVALUATION";
        document.getElementById("updated-at").textContent = snap.at ? String(snap.at).replace("T"," ").slice(0,19) : "—";
        document.getElementById("sess-status").textContent = snap.quote_mode === "LIVE" ? "LIVE" : "DELAYED";
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
          var plan=(data.plans||[]).find(function(p){return p.symbol===stock.symbol})||{};
          var badge=plan.status==="ENTRY"?"ENTRY":plan.status==="WATCH"?"WATCH":"";
          row.setAttribute("data-s", stock.symbol);
          row.setAttribute("data-plan", badge || "NONE");
          row.setAttribute("data-fav", isFav(stock.symbol) ? "1" : "0");
          row.onclick = function() { selectStock(stock.symbol); };
          row.innerHTML = 
            '<div class="sym">' + stock.symbol + '<span class="fav-star '+(isFav(stock.symbol)?"on":"")+'" title="مفضلة">★</span><small>' + (badge?badge+" · ":"") + (stock.score || 0) + ' pts</small></div>' +
            '<div class="val">' + fmt(stock.price,2) + '</div>' +
            '<div class="val ' + (Number(stock.volume_ratio) >= 1.2 ? 'up' : '') + '">' + (present(stock.volume_ratio)?fmt(stock.volume_ratio,1)+'x':'—') + '</div>' +
            '<div class="val">' + fmt(stock.score,0) + '</div>';
          
          var star=row.querySelector(".fav-star");if(star)star.onclick=function(ev){ev.stopPropagation();var on=toggleFav(stock.symbol);star.classList.toggle("on",on);row.setAttribute("data-fav",on?"1":"0");applyMarketFilter();};
          container.appendChild(row);

          tickerHtml += '<span><b>' + stock.symbol + '</b>: ' + fmt(stock.price,2) + '</span>';
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
      var q = new URLSearchParams(location.search).get("symbol") || new URLSearchParams(location.search).get("s"); if(q) CURRENT_SYM=String(q).toUpperCase().replace(/[^A-Z0-9_.-]/g,"") || "COMI";
      var search=document.getElementById("market-search"); if(search) search.addEventListener("input",applyMarketFilter);
      document.querySelectorAll("[data-lefttab]").forEach(function(b){b.addEventListener("click",function(){document.querySelectorAll("[data-lefttab]").forEach(function(x){x.classList.remove("active")});b.classList.add("active");var k=b.getAttribute("data-lefttab"),ctx=document.getElementById("left-context");if(k==="smart")ctx.textContent="التحليلات الذكية تعرض فقط Setups / Why / Score الناتجة فعليًا من ReFo.";else if(k==="trades")ctx.textContent="الصفقات مرتبطة بخطة lifecycle وSignal ID؛ WATCH المتأخر لا يتحول إلى ENTRY.";else ctx.textContent="بيانات ReFo الفنية — منفصلة عن أسعار TradingView المعروضة داخل الشارت.";});});
      document.querySelectorAll("[data-mtab]").forEach(function(b){b.addEventListener("click",function(){document.querySelectorAll("[data-mtab]").forEach(function(x){x.classList.remove("active")});b.classList.add("active");var k=b.getAttribute("data-mtab");ACTIVE_MARKET_TAB=k;applyMarketFilter();var mode=document.getElementById("watch-mode");if(mode)mode.textContent=k==="all"?"ReFo":k==="watch"?"WATCH":k==="ideas"?"Plans":"مفضلة هذا الجهاز";});});
      document.querySelectorAll("[data-tf]").forEach(function(b){b.addEventListener("click",function(){CURRENT_INTERVAL=b.getAttribute("data-tf")||"D";document.querySelectorAll("[data-tf]").forEach(function(x){x.classList.remove("on")});b.classList.add("on");renderTradingView(CURRENT_SYM);});});
      var ai=document.getElementById("ai-btn"); if(ai) ai.addEventListener("click",function(){var box=document.querySelector(".signal-box");if(box)box.scrollIntoView({behavior:"smooth",block:"center"});});
      document.querySelectorAll("[data-mobile]").forEach(function(b){b.addEventListener("click",function(){document.querySelectorAll("[data-mobile]").forEach(function(x){x.classList.remove("active")});b.classList.add("active");var k=b.getAttribute("data-mobile");var target=k==="chart"?document.querySelector(".center-panel"):k==="market"?document.querySelector(".right-panel"):k==="alerts"?document.querySelector(".left-panel"):null;if(target)target.scrollIntoView({behavior:"smooth",block:"start"});});});
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
        return Response.json({ ok: true, feature: "market-terminal-v12.0" });
      }
    }

    return base.fetch(req, env, ctx);
  }
};
