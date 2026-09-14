import app from "./indicator_wrapper.js";

const VERSION="market-tape-v1-2026-09-14";
function esc(v){return String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function n(v,d=2){const x=Number(v);return Number.isFinite(x)?x.toFixed(d):"-"}
function dailyChange(detail){
  const rows=Array.isArray(detail?.chart)?detail.chart:[];
  if(rows.length<2)return null;
  const a=Number(rows.at(-2)?.close),b=Number(rows.at(-1)?.close);
  return Number.isFinite(a)&&a!==0&&Number.isFinite(b)?((b-a)/a)*100:null;
}

export default {
  async fetch(req,env,ctx){
    const res=await app.fetch(req,env,ctx),url=new URL(req.url);
    if(req.method!=="GET"||url.pathname!=="/dashboard")return res;
    const ct=res.headers.get("content-type")||"";if(!ct.includes("text/html"))return res;
    let html=await res.text(),state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{},top=Array.isArray(snap.top)?snap.top.slice(0,18):[],details=Array.isArray(snap.details)?snap.details:[];
    const dmap=Object.fromEntries(details.map(x=>[String(x.symbol||"").toUpperCase(),x]));
    const items=top.map(x=>{
      const sym=String(x.symbol||"").toUpperCase(),chg=dailyChange(dmap[sym]),pos=Number(chg)>=0;
      return `<a class="mt-item" href="/dashboard?s=${encodeURIComponent(sym)}"><b>${esc(sym)}</b><span>${n(x.price)}</span><em class="${pos?'up':'down'}">${Number.isFinite(chg)?`${pos?'+':''}${n(chg)}%`:'—'}</em></a>`;
    }).join("");
    const mode=snap.quote_mode==='LIVE'?'LIVE':'SNAPSHOT / DELAYED';
    const css=`<style id="market-tape-v1">
      body{padding-bottom:51px!important}
      .ref-footer{bottom:0!important}
      .market-tape{position:fixed;left:0;right:0;bottom:22px;height:29px;background:#070b0f;border-top:1px solid #27303a;border-bottom:1px solid #1d242b;z-index:49;display:flex;align-items:center;direction:ltr;overflow:hidden}
      .mt-mode{height:100%;display:flex;align-items:center;gap:6px;padding:0 10px;background:#0d141b;border-right:1px solid #28313a;color:#8294a4;font-size:8px;white-space:nowrap;z-index:2}
      .mt-mode b{color:${snap.quote_mode==='LIVE'?'#4bd996':'#ffd166'};font-size:8px}
      .mt-viewport{overflow:hidden;flex:1;height:100%;position:relative}
      .mt-track{display:flex;width:max-content;height:100%;align-items:center;animation:marketTapeScroll 42s linear infinite;will-change:transform}
      .market-tape:hover .mt-track{animation-play-state:paused}
      .mt-item{height:100%;display:flex;align-items:center;gap:7px;padding:0 14px;border-right:1px solid #202830;text-decoration:none;color:#9cadbb;font-size:9px;white-space:nowrap}
      .mt-item:hover{background:#101923}.mt-item b{color:#e4edf4}.mt-item span{color:#bdc9d2}.mt-item em{font-style:normal;font-weight:700}.mt-item .up{color:#35d98a}.mt-item .down{color:#ff646b}
      @keyframes marketTapeScroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}
      @media(prefers-reduced-motion:reduce){.mt-track{animation:none}}
    </style>`;
    html=html.replace('</head>',css+'</head>');
    if(items){
      const tape=`<div class="market-tape" aria-label="شريط أسعار السوق"><div class="mt-mode">EGX <b>${mode}</b></div><div class="mt-viewport"><div class="mt-track">${items}${items}</div></div></div>`;
      html=html.replace('</body>',tape+`<div style="display:none">${VERSION}</div></body>`);
    }
    const headers=new Headers(res.headers);headers.set('content-type','text/html; charset=UTF-8');headers.set('cache-control','no-store, no-cache, must-revalidate');return new Response(html,{status:res.status,headers});
  }
};
