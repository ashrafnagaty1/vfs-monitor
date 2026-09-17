import app from "./stock_panel_wrapper.js";

const VERSION = "tradingview-core-v1-2026-09-17";

function safeSymbol(v){
  const s=String(v||"").toUpperCase().replace(/[^A-Z0-9_.-]/g,"");
  return s || "COMI";
}

export default {
  async fetch(req,env,ctx){
    const res=await app.fetch(req,env,ctx);
    const url=new URL(req.url);
    if(req.method!=="GET" || url.pathname!=="/dashboard") return res;
    const ct=res.headers.get("content-type")||"";
    if(!ct.includes("text/html")) return res;

    let html=await res.text();
    let state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{};
    const details=Array.isArray(snap.details)?snap.details:[];
    const requested=safeSymbol(url.searchParams.get("s"));
    const sym=details.some(x=>safeSymbol(x?.symbol)===requested)
      ? requested
      : safeSymbol(snap?.top?.[0]?.symbol||requested);

    // The historical terminal already loads s3.tradingview.com/tv.js. Add it only if a future
    // upstream layout removes it; do not load multiple chart engines into the protected region.
    if(!html.includes("https://s3.tradingview.com/tv.js")){
      html=html.replace("</head>",'<script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script></head>');
    }

    const css=`<style id="refo-tv-core-style">
      .center{display:flex!important;flex-direction:column!important;min-width:0!important;overflow:hidden!important}
      .centerhead{flex:0 0 auto!important}
      .analysis-toolbar,.live-tools,.indicator-tools,.indicator-deck,.real-indicator-deck,.analysis-box{display:none!important}
      .chartbar{display:none!important}
      .chart{display:block!important;position:relative!important;flex:1 1 auto!important;min-height:360px!important;padding:0!important;overflow:hidden!important;background:#05070a!important}
      #refo_tv_core{position:absolute;inset:0;width:100%;height:100%;background:#05070a;z-index:20}
      #refo_tv_core_status{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#718394;background:#05070a;z-index:19;font-size:11px}
      @media(max-width:900px){.chart{min-height:480px!important}}
    </style>`;
    html=html.replace("</head>",css+"</head>");

    // Replace only the chart contents after every legacy wrapper has finished. This isolates
    // TradingView from ReFo SVG/indicator/drawing overlays while preserving the surrounding UI.
    const marker='<div class="chart"';
    const start=html.indexOf(marker);
    if(start!==-1){
      const openEnd=html.indexOf('>',start);
      const indicators=html.indexOf('<div class="indicators">',openEnd);
      if(openEnd!==-1 && indicators!==-1){
        html=html.slice(0,openEnd+1)+`<div id="refo_tv_core_status">جاري تحميل TradingView…</div><div id="refo_tv_core"></div></div>`+html.slice(indicators);
      }
    }

    const script=`<script id="refo-tv-core-script">(()=>{
      const symbol=${JSON.stringify(sym)};
      const status=document.getElementById('refo_tv_core_status');
      const box=document.getElementById('refo_tv_core');
      if(!box)return;
      function fail(msg){if(status){status.style.zIndex='21';status.textContent=msg;}}
      function boot(){
        if(!window.TradingView || typeof window.TradingView.widget!=='function'){
          fail('تعذر تحميل مكتبة TradingView');
          return;
        }
        try{
          box.innerHTML='';
          new TradingView.widget({
            autosize:true,
            symbol:'EGX:'+symbol,
            interval:'D',
            timezone:'Africa/Cairo',
            theme:'dark',
            style:'1',
            locale:'ar_AE',
            toolbar_bg:'#080c11',
            enable_publishing:false,
            hide_side_toolbar:false,
            allow_symbol_change:true,
            save_image:false,
            container_id:'refo_tv_core',
            studies:['MASimple@tv-basicstudies','Volume@tv-basicstudies']
          });
          if(status)status.remove();
        }catch(e){fail('تعذر تشغيل TradingView داخل الشاشة');}
      }
      if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(boot,0),{once:true});
      else setTimeout(boot,0);
    })();</script>`;
    html=html.replace("</body>",script+`<div style="display:none">${VERSION}</div></body>`);

    const headers=new Headers(res.headers);
    headers.set("content-type","text/html; charset=UTF-8");
    headers.set("cache-control","no-store, no-cache, must-revalidate");
    return new Response(html,{status:res.status,headers});
  }
};
