import app from "./reference_layout_wrapper.js";

const VERSION="interactive-chart-v2-2026-09-14";
function aggregate(rows,size){if(size<=1)return rows.slice();const out=[];const offset=rows.length%size;let i=0;if(offset){const g=rows.slice(0,offset);out.push({ts:g[0]?.ts,open:Number(g[0]?.open),high:Math.max(...g.map(x=>Number(x.high))),low:Math.min(...g.map(x=>Number(x.low))),close:Number(g.at(-1)?.close),volume:g.reduce((s,x)=>s+Number(x.volume||0),0)});i=offset;}for(;i<rows.length;i+=size){const g=rows.slice(i,i+size);if(!g.length)continue;out.push({ts:g[0]?.ts,open:Number(g[0]?.open),high:Math.max(...g.map(x=>Number(x.high))),low:Math.min(...g.map(x=>Number(x.low))),close:Number(g.at(-1)?.close),volume:g.reduce((s,x)=>s+Number(x.volume||0),0)});}return out;}
function frameRows(rows,tf){const base=Array.isArray(rows)?rows:[];return tf==="1W"?aggregate(base,5).slice(-55):base.slice(-55)}
function safeJson(v){return JSON.stringify(v).replace(/</g,"\\u003c").replace(/>/g,"\\u003e").replace(/&/g,"\\u0026")}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const res = await app.fetch(req, env, ctx);
    if (req.method !== "GET" || url.pathname !== "/dashboard") return res;
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("text/html")) return res;
    let html = await res.text();

    let state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    const snap=state?.pro_engine_snapshot||{},details=Array.isArray(snap.details)?snap.details:[],plans=Array.isArray(state?.trade_lifecycle?.plans)?state.trade_lifecycle.plans:[];
    const sym=(url.searchParams.get("s")||snap?.top?.[0]?.symbol||"").toUpperCase();
    const tf=(url.searchParams.get("tf")||"1D").toUpperCase()==="1W"?"1W":"1D";
    const t=details.find(x=>String(x.symbol||"").toUpperCase()===sym)||{},p=plans.find(x=>String(x.symbol||"").toUpperCase()===sym)||{};
    const rows=frameRows(t.chart,tf);
    const levels=[p?.trigger,p?.dynamic_stop??p?.initial_stop,t?.support_20,t?.support_50,t?.resistance_20,t?.resistance_50,p?.target1,p?.target2,p?.target3].map(Number).filter(Number.isFinite);
    const highs=rows.map(x=>Number(x.high)).filter(Number.isFinite),lows=rows.map(x=>Number(x.low)).filter(Number.isFinite);
    let hi=Math.max(...highs,...levels,1),lo=Math.min(...lows,...levels,0);const pad=(hi-lo||1)*.07;hi+=pad;lo-=pad;
    const meta={symbol:sym,timeframe:tf,rows:rows.map(r=>({ts:r.ts,open:Number(r.open),high:Number(r.high),low:Number(r.low),close:Number(r.close),volume:Number(r.volume||0)})),hi,lo,W:820,H:500,top:28,bottom:86,left:16,right:68,quoteMode:snap.quote_mode||"DELAYED_EVALUATION"};

    const css = `<style>
    .live-tools{display:flex;gap:4px;align-items:center;padding:4px 7px;background:#080c11;border-bottom:1px solid #20262d;overflow:auto;white-space:nowrap;height:33px}
    .live-tool{padding:4px 7px;border:1px solid #28333d;background:#0e151c;color:#91a3b3;border-radius:2px;font-size:9px;cursor:pointer}
    .live-tool:hover{border-color:#3a5064;color:#dbe6ef}.live-tool.active{background:#174f91;color:#fff;border-color:#2b79cb}
    .live-tool.danger{color:#e18b8f}.live-status{margin-right:auto;color:#627789;font-size:8px}.live-status b{color:#ffd166}
    .chart.interactive-ready{cursor:crosshair;position:relative;user-select:none}
    .chart-overlay-svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:8}
    .chart-tip{position:absolute;z-index:12;pointer-events:none;background:#071019f2;border:1px solid #344657;color:#dbe5ed;padding:6px 8px;border-radius:3px;font-size:9px;display:none;line-height:1.45;box-shadow:0 2px 8px #0008;direction:ltr;text-align:left;min-width:152px}
    .chart-axis-tag{position:absolute;z-index:11;pointer-events:none;background:#263849;color:#fff;padding:2px 5px;border-radius:2px;font-size:8px;display:none}
    .watch-star{justify-self:center;color:#526273;font-size:13px;cursor:pointer;padding:2px;z-index:3}.watch-star.on{color:#f2c14e}.watch-star:hover{color:#ffd86a}
    .watchrow.hidden-row{display:none!important}.ref-search:focus{outline:none;border-color:#2d7cd3;box-shadow:0 0 0 1px #153b64}.ref-tab{cursor:pointer;user-select:none}.ref-tab:hover{color:#b9d8f5}
    .watch-empty{display:none;padding:20px;text-align:center;color:#708395;border-bottom:1px solid #1a222a}.watch-empty.show{display:block}
    </style>`;
    html = html.replace("</head>", css + "</head>");
    const tools = `<div class="live-tools"><span style="color:#66798a">Drawing</span><button class="live-tool active" data-live-tool="crosshair">Crosshair</button><button class="live-tool" data-live-tool="cursor">Cursor</button><button class="live-tool" data-live-tool="trend">Trend Line</button><button class="live-tool" data-live-tool="fib">Fibonacci</button><button class="live-tool" data-live-tool="measure">Measure</button><button class="live-tool danger" data-live-tool="clear">Clear</button><span class="live-status">${tf} <b>${meta.quoteMode==='LIVE'?'LIVE':'DELAYED / SNAPSHOT'}</b></span></div>`;
    html = html.replace('<div class="chartbar">', tools + '<div class="chartbar">');

    const script = `<script>
    (()=>{
      const META=${safeJson(meta)};
      const chart=document.querySelector('.chart');
      const base=chart&&chart.querySelector('svg');
      if(chart&&base){
        chart.classList.add('interactive-ready');
        const ns='http://www.w3.org/2000/svg';
        const overlay=document.createElementNS(ns,'svg');
        overlay.classList.add('chart-overlay-svg');
        overlay.setAttribute('viewBox', base.getAttribute('viewBox')||'0 0 820 500');
        overlay.setAttribute('preserveAspectRatio','none');
        chart.appendChild(overlay);
        const tip=document.createElement('div');tip.className='chart-tip';chart.appendChild(tip);
        const priceTag=document.createElement('div');priceTag.className='chart-axis-tag';chart.appendChild(priceTag);
        let mode='crosshair',first=null,drawings=[];
        const key='egx-drawings:'+META.symbol+':'+META.timeframe;
        try{drawings=JSON.parse(localStorage.getItem(key)||'[]');if(!Array.isArray(drawings))drawings=[]}catch(_){drawings=[]}
        const tools=[...document.querySelectorAll('[data-live-tool]')];
        const setMode=m=>{mode=m;first=null;tip.style.display='none';priceTag.style.display='none';tools.forEach(x=>x.classList.toggle('active',x.dataset.liveTool===m));};
        tools.forEach(b=>b.addEventListener('click',()=>{const m=b.dataset.liveTool;if(m==='clear'){drawings=[];try{localStorage.removeItem(key)}catch(_){};renderDrawings();setMode('crosshair');return;}setMode(m);}));
        const point=e=>{const r=base.getBoundingClientRect(),vb=base.viewBox.baseVal;return{x:(e.clientX-r.left)/r.width*vb.width,y:(e.clientY-r.top)/r.height*vb.height,cx:e.clientX-r.left,cy:e.clientY-r.top,vw:vb.width,vh:vb.height,r};};
        const line=(x1,y1,x2,y2,color,dash,temp=false,w=1.2)=>{const el=document.createElementNS(ns,'line');Object.entries({x1,y1,x2,y2,stroke:color,'stroke-width':w}).forEach(([k,v])=>el.setAttribute(k,v));if(dash)el.setAttribute('stroke-dasharray',dash);if(temp)el.dataset.temp='1';overlay.appendChild(el);return el;};
        const label=(x,y,s,color='#dfe8ef')=>{const el=document.createElementNS(ns,'text');el.setAttribute('x',x);el.setAttribute('y',y);el.setAttribute('fill',color);el.setAttribute('font-size','10');el.textContent=s;overlay.appendChild(el);return el;};
        const clearTemp=()=>overlay.querySelectorAll('[data-temp]').forEach(x=>x.remove());
        const persist=()=>{try{localStorage.setItem(key,JSON.stringify(drawings.slice(-40)))}catch(_){}};
        const renderOne=d=>{if(d.type==='trend')line(d.a.x,d.a.y,d.b.x,d.b.y,'#4aa3ff','',false,1.4);if(d.type==='measure'){line(d.a.x,d.a.y,d.b.x,d.b.y,'#f2c14e','4 3');const pa=priceAt(d.a.y),pb=priceAt(d.b.y),pct=pa?((pb-pa)/pa*100):0;label((d.a.x+d.b.x)/2,(d.a.y+d.b.y)/2-6,'Δ '+(pb-pa).toFixed(2)+' ('+(pct>=0?'+':'')+pct.toFixed(2)+'%)','#f2c14e');}if(d.type==='fib'){[0,.236,.382,.5,.618,1].forEach((lv,i)=>{const y=d.a.y+(d.b.y-d.a.y)*lv,cols=['#49d17d','#67a8ff','#f2c14e','#d77bff','#ff8a65','#49d17d'];line(Math.min(d.a.x,d.b.x),y,Math.max(d.a.x,d.b.x),y,cols[i],'3 2');label(Math.max(d.a.x,d.b.x)+4,y-2,(lv*100).toFixed(1)+'% '+priceAt(y).toFixed(2),cols[i]);});}};
        const renderDrawings=()=>{overlay.querySelectorAll(':not([data-temp])').forEach(x=>x.remove());drawings.forEach(renderOne);};
        const priceAt=y=>META.hi-(Math.max(META.top,Math.min(META.H-META.bottom,y))-META.top)/(META.H-META.bottom-META.top)*(META.hi-META.lo);
        const rowAt=x=>{if(!META.rows.length)return null;const cw=META.W-META.left-META.right,step=cw/META.rows.length,idx=Math.max(0,Math.min(META.rows.length-1,Math.floor((x-META.left)/step)));return META.rows[idx]||null;};
        const fmtTs=ts=>{if(!ts)return'-';const d=new Date(ts);return Number.isNaN(d.getTime())?String(ts).slice(0,16):d.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});};
        renderDrawings();
        chart.addEventListener('mousemove',e=>{if(mode!=='crosshair')return;clearTemp();const p=point(e),price=priceAt(p.y),row=rowAt(p.x);line(p.x,META.top,p.x,META.H-META.bottom,'#708090','3 3',true);line(META.left,p.y,META.W-META.right,p.y,'#708090','3 3',true);tip.style.display='block';tip.style.left=Math.min(p.cx+10,p.r.width-170)+'px';tip.style.top=Math.max(4,Math.min(p.cy+10,p.r.height-90))+'px';tip.innerHTML=row?'<b>'+META.symbol+' · '+META.timeframe+'</b><br>'+fmtTs(row.ts)+'<br>O '+row.open.toFixed(2)+' &nbsp; H '+row.high.toFixed(2)+'<br>L '+row.low.toFixed(2)+' &nbsp; C '+row.close.toFixed(2)+'<br>Vol '+Math.round(row.volume).toLocaleString():'Price '+price.toFixed(2);priceTag.style.display='block';priceTag.style.right='2px';priceTag.style.top=Math.max(4,Math.min(p.cy-9,p.r.height-20))+'px';priceTag.textContent=price.toFixed(2);});
        chart.addEventListener('mouseleave',()=>{if(mode==='crosshair'){clearTemp();tip.style.display='none';priceTag.style.display='none';}});
        chart.addEventListener('click',e=>{if(!['trend','fib','measure'].includes(mode))return;const p=point(e),pt={x:p.x,y:p.y};if(!first){first=pt;tip.style.display='block';tip.style.left=(p.cx+8)+'px';tip.style.top=(p.cy+8)+'px';tip.textContent='حدد النقطة الثانية';return;}drawings.push({type:mode,a:first,b:pt});first=null;tip.style.display='none';persist();renderDrawings();});
      }

      const input=document.querySelector('.ref-search'),tabs=[...document.querySelectorAll('.ref-tab')],rows=[...document.querySelectorAll('.watchrow')];
      if(input&&rows.length){
        const empty=document.createElement('div');empty.className='watch-empty';empty.textContent='لا توجد أسهم مطابقة';rows.at(-1)?.insertAdjacentElement('afterend',empty);
        const favKey='egx-favorites';let fav=[];try{fav=JSON.parse(localStorage.getItem(favKey)||'[]');if(!Array.isArray(fav))fav=[]}catch(_){fav=[]}
        rows.forEach(r=>{const symbol=(r.querySelector('.wname')?.childNodes?.[0]?.textContent||'').trim();r.dataset.symbol=symbol.toUpperCase();const star=document.createElement('span');star.className='watch-star'+(fav.includes(r.dataset.symbol)?' on':'');star.textContent=fav.includes(r.dataset.symbol)?'★':'☆';star.title='إضافة/إزالة من المفضلة';star.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const s=r.dataset.symbol;if(fav.includes(s))fav=fav.filter(x=>x!==s);else fav.push(s);star.classList.toggle('on',fav.includes(s));star.textContent=fav.includes(s)?'★':'☆';try{localStorage.setItem(favKey,JSON.stringify(fav))}catch(_){};apply();});r.appendChild(star);});
        let tab='السوق';
        const apply=()=>{const q=input.value.trim().toLowerCase();let visible=0;rows.forEach(r=>{const text=r.textContent.toLowerCase(),status=(r.querySelector('.wstatus')?.textContent||'').trim().toUpperCase(),vr=parseFloat(r.querySelector('.wvol b')?.textContent)||0;let ok=!q||text.includes(q)||r.dataset.symbol.toLowerCase().includes(q);if(tab==='المضاربة')ok=ok&&(status==='ENTRY'||vr>=1.1);if(tab==='التوصيات')ok=ok&&(status==='ENTRY'||status==='WATCH');if(tab==='المفضلة')ok=ok&&fav.includes(r.dataset.symbol);r.classList.toggle('hidden-row',!ok);if(ok)visible++;});empty.classList.toggle('show',visible===0);const count=document.querySelector('.watchtitle small');if(count)count.textContent=visible+' سهم';};
        input.addEventListener('input',apply);input.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=rows.find(r=>!r.classList.contains('hidden-row'));if(first)location.href=first.href;}});
        tabs.forEach(t=>t.addEventListener('click',()=>{tab=t.textContent.trim();tabs.forEach(x=>x.classList.toggle('on',x===t));apply();}));
        apply();
      }
    })();
    </script>`;
    html = html.replace("</body>", script + `<div style="display:none">${VERSION}</div></body>`);
    const headers = new Headers(res.headers);
    headers.set("content-type","text/html; charset=UTF-8");
    headers.set("cache-control","no-store, no-cache, must-revalidate");
    return new Response(html,{status:res.status,headers});
  }
};
