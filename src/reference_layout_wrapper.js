import app from "./analysis_tools_wrapper.js";

const VERSION="reference-layout-v7.1-refo-2026-09-14";
const BRAND="ReFo . EGX Smart Trader";

export default {
  async fetch(req,env,ctx){
    const res=await app.fetch(req,env,ctx);
    const u=new URL(req.url);
    if(req.method!=="GET"||u.pathname!=="/dashboard") return res;
    const ct=res.headers.get("content-type")||"";
    if(!ct.includes("text/html")) return res;
    let html=await res.text();

    /* Unified public branding without changing data logic. */
    html=html
      .replaceAll("EGX Smart Terminal",BRAND)
      .replaceAll("EGX SMART TERMINAL",BRAND)
      .replaceAll("EGX Smart Trader",BRAND)
      .replace(/<title>[^<]*<\/title>/i,`<title>${BRAND}</title>`);

    const css=`<style id="reference-v7">
    html,body{width:100%;height:100%;overflow:hidden;background:#05070a!important}
    body{font-family:Tahoma,Arial,sans-serif!important;font-size:10px!important}
    .top{height:151px!important;background:#080b0f!important}
    .bar{height:43px!important;padding:0 9px!important;gap:7px!important}
    .brand{font-size:14px!important;min-width:180px!important}
    .badge{padding:5px 8px!important;height:29px!important;display:flex!important;align-items:center!important}
    .indices{height:43px!important;grid-template-columns:repeat(6,minmax(105px,1fr))!important}
    .idx{padding:4px 7px!important}.idx b{font-size:12px!important}
    .sectorbar{height:36px!important;padding:5px 7px!important;gap:5px!important;align-items:center!important}
    .sector{padding:4px 7px!important;border-radius:4px!important;background:#10161d!important}
    .warn{height:29px!important;padding:6px 9px!important}
    .shell{grid-template-columns:42px 270px minmax(560px,1fr) 325px!important;height:calc(100vh - 151px)!important;min-height:0!important}
    .rail{background:#080c11!important;border-left:1px solid #252b31!important;padding-top:4px!important;gap:2px!important}
    .rail a,.rail span{width:34px!important;height:34px!important;border:0!important;border-radius:2px!important;background:transparent!important;font-size:15px!important}
    .rail .on,.rail a:hover{background:#123d72!important;color:#fff!important;border-right:2px solid #2587ff!important}
    .left{padding:7px!important;background:#090d12!important;border-left:1px solid #262d34!important}
    .stockhead{padding:3px 4px 8px!important}.symbol{font-size:20px!important}.price{font-size:21px!important}
    .tradebtns{margin-top:5px!important}.tradebtn{padding:5px!important}
    .mini-grid{gap:3px!important;margin-top:5px!important}.mini{padding:5px!important}
    .decision{margin-top:5px!important;padding:6px!important;line-height:1.45!important}
    .center{background:#06090d!important;border-left:1px solid #262d34!important}
    .centerhead{height:37px!important;padding:4px 7px!important;gap:4px!important;background:#080c11!important}
    .tf{padding:4px 8px!important;border-radius:2px!important}.tf.on{background:#1764d7!important}
    .analysis-toolbar{height:35px!important;padding:4px 6px!important;gap:3px!important;background:#080b0f!important}
    .anbtn{height:25px!important;padding:5px 7px!important;border-radius:2px!important;background:#0d1218!important}
    .anbtn.on{background:#173e6e!important;border-color:#286cae!important}
    .chartbar{height:28px!important;padding:5px 8px!important;background:#070a0e!important}
    .chart{min-height:0!important;padding:0!important;background:#05070a!important}
    .chart svg{background:#05070a!important}
    .indicator-deck{max-height:168px!important;overflow:hidden!important}.indicator-row{height:80px!important}
    .indicators{height:34px!important;padding:5px 7px!important}
    .analysis-box{display:none!important}
    .right{background:#090d12!important;border-left:1px solid #262d34!important}
    .watchtitle{height:38px!important;padding:8px 9px!important}.filters{padding:5px!important}
    .watchrow{min-height:34px!important;border-bottom:1px solid #171d23!important;padding:3px 5px!important}
    .watchrow.active{background:#10233a!important;border-right:2px solid #1d7fff!important}
    .wname{font-weight:800!important;color:#e7edf2!important}.wname small{font-size:7px!important;color:#667786!important}
    .ticker{height:29px!important;background:#080b0f!important;border-top:1px solid #2a3036!important}
    .ticker-track{height:29px!important;align-items:center!important}
    .ticker-item{padding:0 13px!important;border-left:1px solid #242a30!important}
    .ref-tabs{height:31px;display:flex;align-items:center;gap:2px;padding:3px 6px;border-bottom:1px solid #222a31;background:#090d12}
    .ref-tab{padding:5px 10px;color:#8393a2;border-bottom:2px solid transparent}.ref-tab.on{color:#54a3ff;border-bottom-color:#2788ff;background:#0d1722}
    .ref-search{margin-right:auto;width:180px;height:23px;border:1px solid #27313a;background:#070b0f;color:#8a9aa8;border-radius:2px;padding:3px 7px}
    .ref-left-tabs{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;margin:5px 0;background:#1b2229;border:1px solid #222a31}
    .ref-left-tab{background:#0b1015;color:#748797;text-align:center;padding:6px 2px;font-size:9px}.ref-left-tab.on{background:#12345a;color:#e9f3ff;border-bottom:2px solid #2788ff}
    .ref-footer{position:fixed;bottom:0;left:0;right:0;height:22px;background:#080b0f;border-top:1px solid #222a31;z-index:50;display:flex;align-items:center;padding:0 8px;color:#677786;font-size:8px;direction:ltr}.ref-footer b{color:#9aabb9;margin-right:12px}.ref-footer .live{margin-left:auto;color:#4bd996}
    @media(max-width:1050px){html,body{overflow:auto}.shell{grid-template-columns:38px 230px minmax(540px,1fr) 285px!important;min-width:1090px!important}.top{min-width:1090px}.ref-footer{min-width:1090px}}
    </style>`;
    html=html.replace("</head>",css+"</head>");

    const rightTabs=`<div class="ref-tabs"><span class="ref-tab on">السوق</span><span class="ref-tab">المضاربة</span><span class="ref-tab">التوصيات</span><span class="ref-tab">المفضلة</span><input class="ref-search" placeholder="بحث عن رمز أو اسم شركة..."></div>`;
    html=html.replace('<aside class="right">','<aside class="right">'+rightTabs);

    const leftTabs=`<div class="ref-left-tabs"><div class="ref-left-tab on">نظرة عامة</div><div class="ref-left-tab">الشركة</div><div class="ref-left-tab">أخبار</div><div class="ref-left-tab">التحليلات</div><div class="ref-left-tab">العمق</div></div>`;
    const stockEnd=html.indexOf('</div>',html.indexOf('<div class="stockhead">'));
    if(stockEnd>0) html=html.slice(0,stockEnd+6)+leftTabs+html.slice(stockEnd+6);

    const footer=`<div class="ref-footer"><b>${BRAND}</b><span>بيانات تقييمية/متأخرة — ليست توصية استثمارية</span><span class="live">● متصل &nbsp; | &nbsp; Snapshot / KV</span></div>`;
    html=html.replace('</body>',footer+`<div style="display:none">${VERSION}</div></body>`);

    const headers=new Headers(res.headers);
    headers.set('content-type','text/html; charset=UTF-8');
    headers.set('cache-control','no-store, no-cache, must-revalidate');
    return new Response(html,{status:res.status,headers});
  }
};
