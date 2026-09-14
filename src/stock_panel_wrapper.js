import app from "./market_tape_wrapper.js";

const VERSION="stock-panel-v1-2026-09-14";
function esc(v){return String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function n(v,d=2){const x=Number(v);return Number.isFinite(x)?x.toFixed(d):"—"}

export default {
  async fetch(req,env,ctx){
    const res=await app.fetch(req,env,ctx),url=new URL(req.url);
    if(req.method!=="GET"||url.pathname!=="/dashboard")return res;
    const ct=res.headers.get("content-type")||"";if(!ct.includes("text/html"))return res;
    let html=await res.text(),state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{},details=Array.isArray(snap.details)?snap.details:[],top=Array.isArray(snap.top)?snap.top:[];
    const requested=String(url.searchParams.get("s")||"").toUpperCase();
    const sym=(requested&&details.some(x=>String(x.symbol||"").toUpperCase()===requested))?requested:String(top[0]?.symbol||"").toUpperCase();
    const d=details.find(x=>String(x.symbol||"").toUpperCase()===sym)||{};
    const plans=Array.isArray(state?.trade_lifecycle?.plans)?state.trade_lifecycle.plans:[];
    const p=plans.find(x=>String(x.symbol||"").toUpperCase()===sym)||{};
    const status=esc(p.status||"WATCH"),source=snap.quote_mode==='LIVE'?'LIVE':'SNAPSHOT / DELAYED';
    const analytics=`<div class="ref-left-panel" data-panel="analytics" hidden>
      <div class="sp-title">التحليل الفني <small>${esc(sym)}</small></div>
      <div class="sp-grid">
        <div><small>RSI 14</small><b>${n(d.rsi,1)}</b></div><div><small>ADX</small><b>${n(d.adx,1)}</b></div>
        <div><small>Volume Ratio</small><b>${n(d.volume_ratio,2)}x</b></div><div><small>Liquidity</small><b>${n(d.liquidity_score,0)}%</b></div>
        <div><small>Momentum 5D</small><b>${n(d.momentum_5d,2)}%</b></div><div><small>Score</small><b>${n(d.score,0)}/100</b></div>
        <div><small>Support 20</small><b>${n(d.support_20)}</b></div><div><small>Resistance 20</small><b>${n(d.resistance_20)}</b></div>
        <div><small>Trigger</small><b>${n(p.trigger)}</b></div><div><small>Dynamic Stop</small><b>${n(p.dynamic_stop??p.initial_stop)}</b></div>
      </div>
      <div class="sp-plan"><b>${status}</b><span>T1 ${n(p.target1)} · T2 ${n(p.target2)} · T3 ${n(p.target3)}</span><em>${source}</em></div>
      <div class="sp-note">هذه قراءات خوارزمية من OHLCV المتاح، وليست بيانات عمق سوق أو تنفيذ لحظي.</div>
    </div>`;
    const replacement=`<div class="ref-left-tabs" role="tablist" aria-label="تفاصيل السهم">
      <button class="ref-left-tab on" type="button" data-sp-tab="overview">نظرة عامة</button>
      <button class="ref-left-tab" type="button" data-sp-tab="analytics">التحليلات</button>
      <button class="ref-left-tab disabled" type="button" disabled title="يتطلب Fundamentals موثوقة">الشركة</button>
      <button class="ref-left-tab disabled" type="button" disabled title="لا يوجد News Feed موثوق متصل حاليًا">أخبار</button>
      <button class="ref-left-tab disabled" type="button" disabled title="يتطلب Live Bid/Ask وMarket Depth حقيقي">العمق</button>
    </div>${analytics}`;
    html=html.replace(/<div class="ref-left-tabs">[\s\S]*?<\/div>/,replacement);
    const css=`<style id="stock-panel-v1">
      .ref-left-tabs{grid-template-columns:repeat(5,1fr)!important}.ref-left-tab{border:0;cursor:pointer;font-family:inherit}.ref-left-tab.disabled{opacity:.38;cursor:not-allowed;background:#080c10!important;color:#586673!important}.ref-left-panel{margin:5px 0 8px;padding:7px;background:#0a1016;border:1px solid #26313b}.sp-title{font-weight:800;color:#dce8f2;margin-bottom:6px}.sp-title small{float:left;color:#718597}.sp-grid{display:grid;grid-template-columns:1fr 1fr;gap:3px}.sp-grid>div{padding:5px;background:#0d151d;border:1px solid #1e2a34}.sp-grid small{display:block;color:#708495;font-size:8px}.sp-grid b{display:block;margin-top:2px;color:#e8f0f6;font-size:10px}.sp-plan{margin-top:5px;padding:6px;background:#0c141b;border:1px solid #21303b;display:grid;gap:3px}.sp-plan b{color:#ffd166}.sp-plan span{color:#a9bac7}.sp-plan em{font-style:normal;color:#6f8495;font-size:8px}.sp-note{margin-top:5px;color:#728697;font-size:8px;line-height:1.45}
    </style>`;
    const script=`<script id="stock-panel-script">(()=>{const tabs=[...document.querySelectorAll('[data-sp-tab]')],panel=document.querySelector('[data-panel="analytics"]');if(!tabs.length||!panel)return;const left=document.querySelector('.left');const original=[...left.children].filter(x=>!x.classList.contains('ref-left-tabs')&&!x.classList.contains('ref-left-panel'));tabs.forEach(t=>t.addEventListener('click',()=>{tabs.forEach(x=>x.classList.remove('on'));t.classList.add('on');const analytics=t.dataset.spTab==='analytics';panel.hidden=!analytics;original.forEach(x=>x.style.display=analytics?'none':'');}));})();</script>`;
    html=html.replace('</head>',css+'</head>').replace('</body>',script+`<div style="display:none">${VERSION}</div></body>`);
    const headers=new Headers(res.headers);headers.set('content-type','text/html; charset=UTF-8');headers.set('cache-control','no-store, no-cache, must-revalidate');return new Response(html,{status:res.status,headers});
  }
};
