import app from "./interactive_chart_wrapper.js";

const VERSION="indicator-wrapper-v1-2026-09-14";
function aggregate(rows,size){if(size<=1)return rows.slice();const out=[];const offset=rows.length%size;let i=0;if(offset){const g=rows.slice(0,offset);out.push({ts:g[0]?.ts,open:Number(g[0]?.open),high:Math.max(...g.map(x=>Number(x.high))),low:Math.min(...g.map(x=>Number(x.low))),close:Number(g.at(-1)?.close),volume:g.reduce((s,x)=>s+Number(x.volume||0),0)});i=offset;}for(;i<rows.length;i+=size){const g=rows.slice(i,i+size);if(!g.length)continue;out.push({ts:g[0]?.ts,open:Number(g[0]?.open),high:Math.max(...g.map(x=>Number(x.high))),low:Math.min(...g.map(x=>Number(x.low))),close:Number(g.at(-1)?.close),volume:g.reduce((s,x)=>s+Number(x.volume||0),0)});}return out;}
function frameRows(rows,tf){const base=Array.isArray(rows)?rows:[];return tf==="1W"?aggregate(base,5).slice(-55):base.slice(-55)}
function safeJson(v){return JSON.stringify(v).replace(/</g,"\\u003c").replace(/>/g,"\\u003e").replace(/&/g,"\\u0026")}

export default {
  async fetch(req,env,ctx){
    const res=await app.fetch(req,env,ctx),url=new URL(req.url);
    if(req.method!=="GET"||url.pathname!=="/dashboard")return res;
    const ct=res.headers.get("content-type")||"";if(!ct.includes("text/html"))return res;
    let html=await res.text(),state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{},details=Array.isArray(snap.details)?snap.details:[],plans=Array.isArray(state?.trade_lifecycle?.plans)?state.trade_lifecycle.plans:[];
    const sym=(url.searchParams.get("s")||snap?.top?.[0]?.symbol||"").toUpperCase(),tf=(url.searchParams.get("tf")||"1D").toUpperCase()==="1W"?"1W":"1D";
    const t=details.find(x=>String(x.symbol||"").toUpperCase()===sym)||{},p=plans.find(x=>String(x.symbol||"").toUpperCase()===sym)||{},rows=frameRows(t.chart,tf);
    const levels=[p?.trigger,p?.dynamic_stop??p?.initial_stop,t?.support_20,t?.support_50,t?.resistance_20,t?.resistance_50,p?.target1,p?.target2,p?.target3].map(Number).filter(Number.isFinite),highs=rows.map(x=>Number(x.high)).filter(Number.isFinite),lows=rows.map(x=>Number(x.low)).filter(Number.isFinite);
    let hi=Math.max(...highs,...levels,1),lo=Math.min(...lows,...levels,0);const pad=(hi-lo||1)*.07;hi+=pad;lo-=pad;
    const meta={symbol:sym,timeframe:tf,rows:rows.map(r=>({ts:r.ts,open:Number(r.open),high:Number(r.high),low:Number(r.low),close:Number(r.close),volume:Number(r.volume||0)})),hi,lo,W:820,H:500,top:28,bottom:86,left:16,right:68};
    const css=`<style id="indicator-v1">
      .indicator-tools{height:31px;display:flex;align-items:center;gap:4px;padding:3px 7px;background:#080b0f;border-bottom:1px solid #20262d;overflow:auto;white-space:nowrap}
      .ind-tool{height:23px;padding:3px 8px;border:1px solid #28333d;background:#0d141b;color:#8296a8;border-radius:2px;font-size:9px;cursor:pointer}.ind-tool.on{background:#173e6e;color:#e9f3ff;border-color:#2d78bd}.ind-hint{margin-right:auto;color:#607487;font-size:8px}
      .price-indicator-svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:7}
      .real-indicator-deck{display:grid;grid-template-rows:76px 84px;background:#070a0e;border-top:1px solid #20262d;flex:0 0 160px;min-height:160px}
      .real-indicator-panel{position:relative;border-bottom:1px solid #1c242c;min-height:0}.real-indicator-panel:last-child{border-bottom:0}.real-indicator-panel svg{width:100%;height:100%;display:block}.real-ind-label{position:absolute;top:4px;right:7px;z-index:2;font-size:8px;color:#8093a4;background:#071019cc;padding:2px 5px}.real-ind-label b{color:#dce6ee}
      @media(max-height:720px){.real-indicator-deck{grid-template-rows:58px 64px;flex-basis:122px;min-height:122px}}
    </style>`;
    html=html.replace("</head>",css+"</head>");
    const bar=`<div class="indicator-tools"><span style="color:#627789">Indicators</span><button class="ind-tool on" data-ind="ema20">EMA20</button><button class="ind-tool on" data-ind="ema50">EMA50</button><button class="ind-tool" data-ind="bb">Bollinger</button><button class="ind-tool on" data-ind="rsi">RSI 14</button><button class="ind-tool on" data-ind="macd">MACD</button><span class="ind-hint">محسوبة من ${tf==='1W'?'شموع أسبوعية مجمعة من البيانات اليومية':'الشموع اليومية'} الحالية</span></div>`;
    html=html.replace('<div class="chartbar">',bar+'<div class="chartbar">');
    const script=`<script>(()=>{
      const M=${safeJson(meta)},chart=document.querySelector('.chart');if(!chart||!M.rows.length)return;
      const closes=M.rows.map(x=>Number(x.close)),ns='http://www.w3.org/2000/svg';
      const ema=(a,n)=>{const k=2/(n+1),o=[];let v=a[0];for(let i=0;i<a.length;i++){v=i?v+(a[i]-v)*k:a[i];o.push(v)}return o};
      const sma=(a,n,i)=>{if(i<n-1)return null;let s=0;for(let j=i-n+1;j<=i;j++)s+=a[j];return s/n};
      const bb=(a,n=20,m=2)=>a.map((_,i)=>{const mid=sma(a,n,i);if(mid==null)return null;let ss=0;for(let j=i-n+1;j<=i;j++)ss+=(a[j]-mid)**2;const sd=Math.sqrt(ss/n);return{mid,up:mid+m*sd,lo:mid-m*sd}});
      const rsi=a=>{const out=Array(a.length).fill(null);if(a.length<15)return out;let g=0,l=0;for(let i=1;i<=14;i++){const d=a[i]-a[i-1];g+=Math.max(d,0);l+=Math.max(-d,0)}g/=14;l/=14;out[14]=l===0?100:100-100/(1+g/l);for(let i=15;i<a.length;i++){const d=a[i]-a[i-1];g=(g*13+Math.max(d,0))/14;l=(l*13+Math.max(-d,0))/14;out[i]=l===0?100:100-100/(1+g/l)}return out};
      const e20=ema(closes,20),e50=ema(closes,50),bands=bb(closes),fast=ema(closes,12),slow=ema(closes,26),macd=fast.map((v,i)=>v-slow[i]),signal=ema(macd,9),hist=macd.map((v,i)=>v-signal[i]),rsi14=rsi(closes);
      const active={ema20:true,ema50:true,bb:false,rsi:true,macd:true};
      const makeSvg=cls=>{const s=document.createElementNS(ns,'svg');s.setAttribute('viewBox','0 0 820 500');s.setAttribute('preserveAspectRatio','none');s.classList.add(cls);return s};
      const priceSvg=makeSvg('price-indicator-svg');chart.appendChild(priceSvg);
      const deck=document.createElement('div');deck.className='real-indicator-deck';deck.innerHTML='<div class="real-indicator-panel rsi-panel"><span class="real-ind-label">RSI 14 <b class="rsi-val">-</b></span></div><div class="real-indicator-panel macd-panel"><span class="real-ind-label">MACD 12,26,9 <b class="macd-val">-</b></span></div>';chart.insertAdjacentElement('afterend',deck);
      const rsiPanel=deck.querySelector('.rsi-panel'),macdPanel=deck.querySelector('.macd-panel');
      const line=(svg,x1,y1,x2,y2,stroke,w=1,dash='')=>{const e=document.createElementNS(ns,'line');Object.entries({x1,y1,x2,y2,stroke,'stroke-width':w}).forEach(([k,v])=>e.setAttribute(k,v));if(dash)e.setAttribute('stroke-dasharray',dash);svg.appendChild(e)};
      const poly=(svg,vals,yfn,stroke,w=1.2)=>{const pts=[];const cw=M.W-M.left-M.right,step=cw/Math.max(1,M.rows.length);vals.forEach((v,i)=>{if(Number.isFinite(v))pts.push((M.left+i*step+step/2)+','+yfn(v))});if(pts.length<2)return;const e=document.createElementNS(ns,'polyline');e.setAttribute('points',pts.join(' '));e.setAttribute('fill','none');e.setAttribute('stroke',stroke);e.setAttribute('stroke-width',w);svg.appendChild(e)};
      const priceY=v=>M.top+(M.hi-v)/(M.hi-M.lo)*(M.H-M.bottom-M.top);
      const renderPrice=()=>{priceSvg.innerHTML='';if(active.ema20)poly(priceSvg,e20,priceY,'#45a3ff',1.35);if(active.ema50)poly(priceSvg,e50,priceY,'#f0b44d',1.35);if(active.bb){poly(priceSvg,bands.map(x=>x?.up??null),priceY,'#9b7cff',1,'4 3');poly(priceSvg,bands.map(x=>x?.mid??null),priceY,'#7860c9',.8,'');poly(priceSvg,bands.map(x=>x?.lo??null),priceY,'#9b7cff',1,'4 3')}};
      const renderRsi=()=>{rsiPanel.style.display=active.rsi?'block':'none';if(!active.rsi)return;const s=document.createElementNS(ns,'svg');s.setAttribute('viewBox','0 0 820 100');s.setAttribute('preserveAspectRatio','none');rsiPanel.querySelector('svg')?.remove();rsiPanel.appendChild(s);[30,50,70].forEach(v=>line(s,16,100-v,752,100-v,v===50?'#23303b':'#3a2e35',.8,v===50?'2 3':'4 4'));poly(s,rsi14,v=>100-v,'#d58cff',1.25);const last=[...rsi14].reverse().find(Number.isFinite);rsiPanel.querySelector('.rsi-val').textContent=Number.isFinite(last)?last.toFixed(1):'-'};
      const renderMacd=()=>{macdPanel.style.display=active.macd?'block':'none';if(!active.macd)return;const all=[...macd,...signal,...hist].filter(Number.isFinite),mx=Math.max(...all.map(Math.abs),1e-6),y=v=>50-v/mx*40;const s=document.createElementNS(ns,'svg');s.setAttribute('viewBox','0 0 820 100');s.setAttribute('preserveAspectRatio','none');macdPanel.querySelector('svg')?.remove();macdPanel.appendChild(s);line(s,16,50,752,50,'#34414c',.8,'3 3');const cw=736,step=cw/Math.max(1,M.rows.length);hist.forEach((v,i)=>{if(!Number.isFinite(v))return;const e=document.createElementNS(ns,'rect'),yy=y(v);e.setAttribute('x',16+i*step+step*.22);e.setAttribute('width',Math.max(1,step*.55));e.setAttribute('y',Math.min(50,yy));e.setAttribute('height',Math.max(1,Math.abs(50-yy)));e.setAttribute('fill',v>=0?'#2fbf83':'#e85d68');e.setAttribute('opacity','.65');s.appendChild(e)});poly(s,macd,y,'#45a3ff',1.2);poly(s,signal,y,'#f0b44d',1.1);const last=macd.at(-1);macdPanel.querySelector('.macd-val').textContent=Number.isFinite(last)?last.toFixed(3):'-'};
      const syncDeck=()=>{deck.style.display=(active.rsi||active.macd)?'grid':'none';if(active.rsi&&!active.macd)deck.style.gridTemplateRows='1fr';else if(!active.rsi&&active.macd)deck.style.gridTemplateRows='1fr';else deck.style.gridTemplateRows='76px 84px'};
      const render=()=>{renderPrice();renderRsi();renderMacd();syncDeck()};render();
      document.querySelectorAll('[data-ind]').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.ind;active[k]=!active[k];b.classList.toggle('on',active[k]);render()}));
    })();</script>`;
    html=html.replace('</body>',script+`<div style="display:none">${VERSION}</div></body>`);
    const headers=new Headers(res.headers);headers.set('content-type','text/html; charset=UTF-8');headers.set('cache-control','no-store, no-cache, must-revalidate');return new Response(html,{status:res.status,headers});
  }
};
