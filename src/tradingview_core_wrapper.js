import app from "./stock_panel_wrapper.js";

const VERSION = "tradingview-core-v3-diagnostic-2026-09-17";
const TV_SRC = "https://s3.tradingview.com/tv.js";

function safeSymbol(v){
  const s=String(v||"").toUpperCase().replace(/[^A-Z0-9_.-]/g,"");
  return s || "COMI";
}

function tvTestPage(sym){
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReFo TradingView Test</title><style>html,body{margin:0;width:100%;height:100%;background:#05070a;color:#dce3ea;font-family:Tahoma,Arial,sans-serif}#status{position:fixed;top:0;left:0;right:0;z-index:5;padding:8px 12px;background:#101720;border-bottom:1px solid #263443;font-size:12px}#tv{position:absolute;inset:36px 0 0 0}.ok{color:#2ecc71}.bad{color:#ff6b6b}</style></head><body><div id="status">جاري اختبار تحميل TradingView…</div><div id="tv"></div><script>(()=>{const st=document.getElementById('status');function msg(t,c){st.textContent=t;st.className=c||''}const s=document.createElement('script');s.src=${JSON.stringify(TV_SRC)};s.async=true;s.onload=()=>{if(!window.TradingView||typeof window.TradingView.widget!=='function'){msg('تم تحميل tv.js لكن TradingView.widget غير متاح','bad');return}msg('تم تحميل TradingView بنجاح','ok');try{new window.TradingView.widget({autosize:true,symbol:'EGX:${sym}',interval:'D',timezone:'Africa/Cairo',theme:'dark',style:'1',locale:'ar_AE',enable_publishing:false,hide_side_toolbar:false,allow_symbol_change:true,container_id:'tv'});}catch(e){msg('TradingView widget error: '+(e&&e.message?e.message:String(e)),'bad')}};s.onerror=()=>msg('فشل تحميل tv.js من s3.tradingview.com','bad');document.head.appendChild(s);setTimeout(()=>{if(!window.TradingView)msg('انتهت مهلة التحميل: TradingView مازال غير متاح','bad')},10000)})();</script><div style="display:none">${VERSION}</div></body></html>`;
}

export default {
  async fetch(req,env,ctx){
    const url=new URL(req.url);
    if(req.method==="GET" && url.pathname==="/tv-test"){
      return new Response(tvTestPage(safeSymbol(url.searchParams.get("s"))),{headers:{"content-type":"text/html; charset=UTF-8","cache-control":"no-store"}});
    }

    const res=await app.fetch(req,env,ctx);
    if(req.method!=="GET" || url.pathname!=="/dashboard") return res;
    const ct=res.headers.get("content-type")||"";
    if(!ct.includes("text/html")) return res;

    let html=await res.text();
    let state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{};
    const details=Array.isArray(snap.details)?snap.details:[];
    const requested=safeSymbol(url.searchParams.get("s"));
    const sym=details.some(x=>safeSymbol(x?.symbol)===requested)?requested:safeSymbol(snap?.top?.[0]?.symbol||requested);

    // Remove static legacy loader. v3 loads tv.js explicitly and reports success/failure.
    html=html.replace(/<script[^>]+src=["']https:\/\/s3\.tradingview\.com\/tv\.js["'][^>]*><\/script>/gi,'');

    const css=`<style id="refo-tv-core-style">.center{display:flex!important;flex-direction:column!important;min-width:0!important;overflow:hidden!important;background:#05070a!important}.analysis-toolbar,.live-tools,.indicator-tools,.indicator-deck,.real-indicator-deck,.analysis-box,.indicators,.chartbar{display:none!important}#tradingview_box{position:relative!important;display:block!important;flex:1 1 auto!important;width:100%!important;height:100%!important;min-height:520px!important;overflow:hidden!important;background:#05070a!important}#refo_tv_core_status{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#718394;background:#05070a;z-index:2;font-size:11px}@media(max-width:900px){#tradingview_box{min-height:480px!important}}</style>`;
    html=html.replace("</head>",css+"</head>");

    const centerStart=html.indexOf('<section class="center"');
    const rightStart=centerStart!==-1?html.indexOf('<aside class="right"',centerStart):-1;
    if(centerStart!==-1&&rightStart!==-1){const centerOpenEnd=html.indexOf('>',centerStart);if(centerOpenEnd!==-1){html=html.slice(0,centerOpenEnd+1)+'<div id="tradingview_box"><div id="refo_tv_core_status">جاري تحميل TradingView…</div></div></section>\n\n    '+html.slice(rightStart)}}

    html=html.replace(/function initTV\(\)[\s\S]*?window\.addEventListener\("DOMContentLoaded", initTV\);/g,'');

    const script=`<script id="refo-tv-core-script">(()=>{const symbol=${JSON.stringify(sym)},status=document.getElementById('refo_tv_core_status'),box=document.getElementById('tradingview_box');if(!box)return;function fail(m){if(status){status.style.zIndex='3';status.textContent=m}}function start(){try{if(status)status.remove();new window.TradingView.widget({autosize:true,symbol:'EGX:'+symbol,interval:'D',timezone:'Africa/Cairo',theme:'dark',style:'1',locale:'ar_AE',toolbar_bg:'#090d12',enable_publishing:false,hide_side_toolbar:false,allow_symbol_change:true,save_image:false,container_id:'tradingview_box',studies:['MASimple@tv-basicstudies','Volume@tv-basicstudies']})}catch(e){fail('TradingView widget error: '+(e&&e.message?e.message:String(e)))}}const s=document.createElement('script');s.src=${JSON.stringify(TV_SRC)};s.async=true;s.onload=()=>{if(window.TradingView&&typeof window.TradingView.widget==='function')start();else fail('تم تحميل tv.js لكن TradingView.widget غير متاح')};s.onerror=()=>fail('فشل تحميل tv.js من s3.tradingview.com');document.head.appendChild(s);setTimeout(()=>{if(!window.TradingView)fail('انتهت مهلة تحميل TradingView')},10000)})();</script>`;
    html=html.replace("</body>",script+`<div style="display:none">${VERSION}</div></body>`);

    const headers=new Headers(res.headers);headers.set("content-type","text/html; charset=UTF-8");headers.set("cache-control","no-store, no-cache, must-revalidate");return new Response(html,{status:res.status,headers});
  }
};
