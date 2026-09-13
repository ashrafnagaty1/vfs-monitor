import app from "./ticker_wrapper.js";

const VERSION = "timeframes-v1-2026-09-14";

function esc(v){return String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function n(v,d=2){const x=Number(v);return Number.isFinite(x)?x.toFixed(d):"-"}

function aggregate(rows,size){
  if(size<=1) return rows.slice();
  const out=[];
  const offset=rows.length%size;
  let i=0;
  if(offset){
    const g=rows.slice(0,offset);
    out.push({ts:g[0]?.ts,open:Number(g[0]?.open),high:Math.max(...g.map(x=>Number(x.high))),low:Math.min(...g.map(x=>Number(x.low))),close:Number(g.at(-1)?.close),volume:g.reduce((s,x)=>s+Number(x.volume||0),0)});
    i=offset;
  }
  for(;i<rows.length;i+=size){
    const g=rows.slice(i,i+size); if(!g.length) continue;
    out.push({ts:g[0]?.ts,open:Number(g[0]?.open),high:Math.max(...g.map(x=>Number(x.high))),low:Math.min(...g.map(x=>Number(x.low))),close:Number(g.at(-1)?.close),volume:g.reduce((s,x)=>s+Number(x.volume||0),0)});
  }
  return out;
}

function frameRows(rows,tf){
  const base=Array.isArray(rows)?rows:[];
  if(tf==="1W") return aggregate(base,5).slice(-55);
  return base.slice(-55);
}

function chartSvg(rows,t,p){
  if(rows.length<4)return `<div class="chart-empty">لا توجد بيانات كافية لهذا الفريم</div>`;
  const W=820,H=500,top=28,bottom=86,left=16,right=68,cw=W-left-right,ch=H-top-bottom;
  const highs=rows.map(x=>Number(x.high)),lows=rows.map(x=>Number(x.low)),vols=rows.map(x=>Number(x.volume||0));
  const levels=[p?.trigger,p?.dynamic_stop??p?.initial_stop,t?.support_20,t?.support_50,t?.resistance_20,t?.resistance_50,p?.target1,p?.target2,p?.target3].map(Number).filter(Number.isFinite);
  let hi=Math.max(...highs,...levels),lo=Math.min(...lows,...levels);const pad=(hi-lo||1)*.07;hi+=pad;lo-=pad;
  const y=v=>top+(hi-v)/(hi-lo)*ch,maxVol=Math.max(...vols,1),step=cw/rows.length,body=Math.max(3,step*.58);
  let svg=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-label="OHLC chart">`;
  for(let i=0;i<7;i++){const yy=top+i*ch/6,val=hi-i*(hi-lo)/6;svg+=`<line x1="${left}" x2="${W-right}" y1="${yy}" y2="${yy}" stroke="#1b242d" stroke-width="1"/><text x="${W-5}" y="${yy+4}" fill="#7c8b99" font-size="10" text-anchor="end">${n(val,2)}</text>`}
  const line=(value,color,label,dash="5 4",w=1.15)=>{const v=Number(value);if(!Number.isFinite(v)||v<=0)return"";const yy=y(v);return `<line x1="${left}" x2="${W-right}" y1="${yy}" y2="${yy}" stroke="${color}" stroke-width="${w}" stroke-dasharray="${dash}"/><rect x="${W-right+4}" y="${yy-9}" width="57" height="17" rx="2" fill="${color}" opacity=".92"/><text x="${W-6}" y="${yy+3}" fill="#061019" font-size="9" font-weight="700" text-anchor="end">${label} ${n(v,2)}</text>`};
  svg+=line(t.resistance_50,"#ff694f","R2")+line(t.resistance_20,"#ff4d59","R1")+line(t.support_20,"#39d98a","S1")+line(t.support_50,"#24b96d","S2")+line(p?.trigger,"#4aa3ff","TRG","3 3",1.35)+line(p?.dynamic_stop??p?.initial_stop,"#ff3d4f","STOP","3 3",1.35);
  if(p?.target1)svg+=line(p.target1,"#7ed957","T1","2 4",1);if(p?.target2)svg+=line(p.target2,"#78c850","T2","2 4",1);if(p?.target3)svg+=line(p.target3,"#70b94b","T3","2 4",1);
  rows.forEach((r,i)=>{const x=left+step*i+step/2,o=Number(r.open),c=Number(r.close),h=Number(r.high),l=Number(r.low),col=c>=o?"#18c78b":"#ef5350",yy1=y(Math.max(o,c)),yy2=y(Math.min(o,c));svg+=`<line x1="${x}" x2="${x}" y1="${y(h)}" y2="${y(l)}" stroke="${col}" stroke-width="1"/><rect x="${x-body/2}" y="${yy1}" width="${body}" height="${Math.max(1.5,yy2-yy1)}" fill="${col}" rx=".7"/>`;const vh=(Number(r.volume||0)/maxVol)*62;svg+=`<rect x="${x-body/2}" y="${H-16-vh}" width="${body}" height="${vh}" fill="${col}" opacity=".48"/>`});
  const last=rows.at(-1),lastv=Number(last?.close);if(Number.isFinite(lastv))svg+=line(lastv,"#f5c84c","LAST","2 2",1.1);
  return svg+`</svg>`;
}

export default {
  async fetch(req,env,ctx){
    const u=new URL(req.url);
    const res=await app.fetch(req,env,ctx);
    if(req.method!=="GET"||u.pathname!=="/dashboard") return res;
    const ct=res.headers.get("content-type")||""; if(!ct.includes("text/html")) return res;

    let html=await res.text();
    const tf=(u.searchParams.get("tf")||"1D").toUpperCase();
    const supported=tf==="1W"?"1W":"1D";
    let state=null;try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{},details=Array.isArray(snap.details)?snap.details:[],plans=Array.isArray(state?.trade_lifecycle?.plans)?state.trade_lifecycle.plans:[];
    const sym=(u.searchParams.get("s")||snap?.top?.[0]?.symbol||"").toUpperCase();
    const t=details.find(x=>String(x.symbol||"").toUpperCase()===sym)||{},p=plans.find(x=>String(x.symbol||"").toUpperCase()===sym)||{};
    const rows=frameRows(t.chart,supported),last=rows.at(-1)||{};

    const frameCss=`<style>.tf{color:#8fa2b4;text-decoration:none}.tf.disabled{opacity:.38;cursor:not-allowed}.tf.on{background:#1853a6;color:#fff}.frame-note{padding:4px 9px;background:#2d250d;color:#ffd166;border-bottom:1px solid #4f421a;text-align:center}</style>`;
    html=html.replace("</head>",frameCss+"</head>");

    const qs=`s=${encodeURIComponent(sym)}`;
    const controls=`<a class="tf disabled" title="يحتاج بيانات Intraday حقيقية">1m</a><a class="tf disabled" title="يحتاج بيانات Intraday حقيقية">15m</a><a class="tf disabled" title="يحتاج بيانات Intraday حقيقية">30m</a><a class="tf disabled" title="يحتاج بيانات Intraday حقيقية">4h</a><a class="tf ${supported==='1D'?'on':''}" href="/dashboard?${qs}&tf=1D">1D</a><a class="tf ${supported==='1W'?'on':''}" href="/dashboard?${qs}&tf=1W">1W</a>`;
    html=html.replace(/<span class="tf">1m<\/span><span class="tf">15m<\/span><span class="tf">30m<\/span><span class="tf">4h<\/span><span class="tf on">1D<\/span><span class="tf">1W<\/span>/,controls);
    html=html.replace(`${esc(sym)} · 1D · EGX`,`${esc(sym)} · ${supported} · EGX`);

    const chartStart=html.indexOf('<div class="chart">');
    const indStart=html.indexOf('<div class="indicators">',chartStart);
    if(chartStart!==-1&&indStart!==-1){
      const open='<div class="chart">';
      html=html.slice(0,chartStart)+open+chartSvg(rows,t,p)+'</div>'+html.slice(indStart);
    }

    const chartbarStart=html.indexOf('<div class="chartbar">');
    const chartbarEnd=html.indexOf('</div>',chartbarStart);
    if(chartbarStart!==-1&&chartbarEnd!==-1){
      const prev=rows.length>1?Number(rows.at(-2)?.close):Number(last.open),chg=prev?((Number(last.close)-prev)/prev*100):0;
      const bar=`<div class="chartbar"><b>${esc(sym)}</b><span>${supported}</span><span>O ${n(last.open)}</span><span>H ${n(last.high)}</span><span>L ${n(last.low)}</span><span>C ${n(last.close)}</span><span class="${chg>=0?'green':'red'}">${chg>=0?'+':''}${n(chg,2)}%</span></div>`;
      html=html.slice(0,chartbarStart)+bar+html.slice(chartbarEnd+6);
    }

    html=html.replace(/href="\/dashboard\?s=([^"&]+)"/g,`href="/dashboard?s=$1&tf=${supported}"`);
    const unsupported=tf!==supported;
    if(unsupported){html=html.replace('<section class="center">','<section class="center"><div class="frame-note">الفريمات اللحظية 1m / 15m / 30m / 4h تحتاج مصدر Intraday حقيقي؛ لم أعرض بيانات وهمية. المتاح حاليًا 1D و1W.</div>')}
    html=html.replace("</body>",`<div style="display:none">${VERSION}</div></body>`);
    const headers=new Headers(res.headers);headers.set("content-type","text/html; charset=UTF-8");headers.set("cache-control","no-store, no-cache, must-revalidate");
    return new Response(html,{status:res.status,headers});
  }
};
