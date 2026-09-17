import app from "./stock_panel_wrapper.js";

const VERSION = "tradingview-core-v4-isolated-frame-2026-09-17";
const TV_SRC = "https://s3.tradingview.com/tv.js";

function safeSymbol(v){
  const s=String(v||"").toUpperCase().replace(/[^A-Z0-9_.-]/g,"");
  return s || "COMI";
}

function tvPage(sym, test=false){
  const status=test?'<div id="status">جاري اختبار تحميل TradingView…</div>':'';
  const inset=test?'36px 0 0 0':'0';
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReFo TradingView</title><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#05070a;color:#dce3ea;font-family:Tahoma,Arial,sans-serif}#status{position:fixed;top:0;left:0;right:0;z-index:5;padding:8px 12px;background:#101720;border-bottom:1px solid #263443;font-size:12px}#tv{position:absolute;inset:${inset}}.ok{color:#2ecc71}.bad{color:#ff6b6b}</style></head><body>${status}<div id="tv"></div><script>(()=>{const st=document.getElementById('status');function msg(t,c){if(st){st.textContent=t;st.className=c||''}}const s=document.createElement('script');s.src=${JSON.stringify(TV_SRC)};s.async=true;s.onload=()=>{if(!window.TradingView||typeof window.TradingView.widget!=='function'){msg('تم تحميل tv.js لكن TradingView.widget غير متاح','bad');return}msg('تم تحميل TradingView بنجاح','ok');try{new window.TradingView.widget({autosize:true,symbol:'EGX:${sym}',interval:'D',timezone:'Africa/Cairo',theme:'dark',style:'1',locale:'ar_AE',toolbar_bg:'#090d12',enable_publishing:false,hide_side_toolbar:false,allow_symbol_change:true,save_image:false,container_id:'tv',studies:['MASimple@tv-basicstudies','Volume@tv-basicstudies']})}catch(e){msg('TradingView widget error: '+(e&&e.message?e.message:String(e)),'bad')}};s.onerror=()=>msg('فشل تحميل tv.js من s3.tradingview.com','bad');document.head.appendChild(s)})();</script><div style="display:none">${VERSION}</div></body></html>`;
}

export default {
  async fetch(req,env,ctx){
    const url=new URL(req.url);
    if(req.method==="GET" && (url.pathname==="/tv-test" || url.pathname==="/tv-frame")){
      const sym=safeSymbol(url.searchParams.get("s"));
      return new Response(tvPage(sym,url.pathname==="/tv-test"),{headers:{"content-type":"text/html; charset=UTF-8","cache-control":"no-store","x-frame-options":"SAMEORIGIN"}});
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

    // Remove legacy TradingView loader/initializer from the parent dashboard.
    html=html.replace(/<script[^>]+src=["']https:\/\/s3\.tradingview\.com\/tv\.js["'][^>]*><\/script>/gi,'');
    html=html.replace(/function initTV\(\)[\s\S]*?window\.addEventListener\("DOMContentLoaded", initTV\);/g,'');

    const css=`<style id="refo-tv-core-style">.center{display:flex!important;flex-direction:column!important;min-width:0!important;overflow:hidden!important;background:#05070a!important;padding:0!important}.analysis-toolbar,.live-tools,.indicator-tools,.indicator-deck,.real-indicator-deck,.analysis-box,.indicators,.chartbar{display:none!important}#refo_tv_frame{display:block!important;border:0!important;flex:1 1 auto!important;width:100%!important;height:100%!important;min-height:560px!important;background:#05070a!important}@media(max-width:900px){#refo_tv_frame{min-height:500px!important}}</style>`;
    html=html.replace("</head>",css+"</head>");

    // Isolation is intentional: the exact loader proven at /tv-test now owns a same-origin iframe,
    // so legacy ReFo scripts cannot overwrite or remove TradingView's DOM.
    const centerStart=html.indexOf('<section class="center"');
    const rightStart=centerStart!==-1?html.indexOf('<aside class="right"',centerStart):-1;
    if(centerStart!==-1&&rightStart!==-1){
      const centerOpenEnd=html.indexOf('>',centerStart);
      if(centerOpenEnd!==-1){
        const frame=`<iframe id="refo_tv_frame" title="TradingView EGX Chart" src="/tv-frame?s=${encodeURIComponent(sym)}" loading="eager" referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
        html=html.slice(0,centerOpenEnd+1)+frame+'</section>\n\n    '+html.slice(rightStart);
      }
    }

    html=html.replace("</body>",`<div style="display:none">${VERSION}</div></body>`);
    const headers=new Headers(res.headers);
    headers.set("content-type","text/html; charset=UTF-8");
    headers.set("cache-control","no-store, no-cache, must-revalidate");
    return new Response(html,{status:res.status,headers});
  }
};
