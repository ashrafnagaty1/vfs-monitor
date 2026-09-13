import app from "./reference_layout_wrapper.js";

const VERSION="interactive-chart-v1-2026-09-14";
export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const res = await app.fetch(req, env, ctx);
    if (req.method !== "GET" || url.pathname !== "/dashboard") return res;
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("text/html")) return res;
    let html = await res.text();
    const css = `<style>
    .live-tools{display:flex;gap:5px;align-items:center;padding:5px 8px;background:#091017;border-bottom:1px solid #20262d;overflow:auto;white-space:nowrap}
    .live-tool{padding:5px 8px;border:1px solid #2a3540;background:#121920;color:#91a3b3;border-radius:3px;font-size:10px;cursor:pointer}
    .live-tool.active{background:#174f91;color:#fff;border-color:#2467b6}
    .chart.interactive-ready{cursor:crosshair;position:relative}
    .chart-overlay-svg{position:absolute;inset:5px 7px;width:calc(100% - 14px);height:calc(100% - 10px);pointer-events:none;z-index:8}
    .chart-tip{position:absolute;z-index:9;pointer-events:none;background:#0a1016e8;border:1px solid #33404c;color:#dbe5ed;padding:4px 6px;border-radius:3px;font-size:9px;display:none}
    </style>`;
    html = html.replace("</head>", css + "</head>");
    const tools = `<div class="live-tools"><span style="color:#66798a">Interactive</span><button class="live-tool" data-live-tool="cursor">Cursor</button><button class="live-tool" data-live-tool="crosshair">Crosshair</button><button class="live-tool" data-live-tool="trend">Trend Line</button><button class="live-tool" data-live-tool="fib">Fibonacci</button><button class="live-tool" data-live-tool="measure">Measure</button><span style="color:#ffd166;font-size:9px">الرسم يعمل داخل الجلسة الحالية</span></div>`;
    html = html.replace('<div class="chartbar">', tools + '<div class="chartbar">');
    const script = `<script>
    (()=>{
      const chart=document.querySelector('.chart');
      if(!chart)return;
      const base=chart.querySelector('svg');
      if(!base)return;
      chart.classList.add('interactive-ready');
      const overlay=document.createElementNS('http://www.w3.org/2000/svg','svg');
      overlay.classList.add('chart-overlay-svg');
      overlay.setAttribute('viewBox', base.getAttribute('viewBox')||'0 0 820 500');
      overlay.setAttribute('preserveAspectRatio','none');
      chart.appendChild(overlay);
      const tip=document.createElement('div'); tip.className='chart-tip'; chart.appendChild(tip);
      let mode='cursor', first=null;
      document.querySelectorAll('[data-live-tool]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.liveTool;first=null;tip.style.display='none';document.querySelectorAll('[data-live-tool]').forEach(x=>x.classList.toggle('active',x===b));}));
      const ns='http://www.w3.org/2000/svg';
      const point=e=>{const r=base.getBoundingClientRect(), vb=base.viewBox.baseVal; return {x:(e.clientX-r.left)/r.width*vb.width,y:(e.clientY-r.top)/r.height*vb.height,cx:e.clientX-r.left,cy:e.clientY-r.top,vw:vb.width,vh:vb.height};};
      const line=(x1,y1,x2,y2,color,dash,temp=false)=>{const el=document.createElementNS(ns,'line');el.setAttribute('x1',x1);el.setAttribute('y1',y1);el.setAttribute('x2',x2);el.setAttribute('y2',y2);el.setAttribute('stroke',color);el.setAttribute('stroke-width','1.25');if(dash)el.setAttribute('stroke-dasharray',dash);if(temp)el.dataset.temp='1';overlay.appendChild(el);return el;};
      const label=(x,y,s,color='#dfe8ef')=>{const el=document.createElementNS(ns,'text');el.setAttribute('x',x);el.setAttribute('y',y);el.setAttribute('fill',color);el.setAttribute('font-size','11');el.textContent=s;overlay.appendChild(el);};
      const clearTemp=()=>overlay.querySelectorAll('[data-temp]').forEach(x=>x.remove());
      chart.addEventListener('mousemove',e=>{if(mode!=='crosshair')return; clearTemp(); const p=point(e); line(p.x,0,p.x,p.vh,'#708090','3 3',true); line(0,p.y,p.vw,p.y,'#708090','3 3',true); tip.style.display='block'; tip.style.left=(p.cx+10)+'px'; tip.style.top=(p.cy+10)+'px'; tip.textContent='X '+p.x.toFixed(1)+' • Y '+p.y.toFixed(1);});
      chart.addEventListener('mouseleave',()=>{if(mode==='crosshair'){clearTemp();tip.style.display='none';}});
      chart.addEventListener('click',e=>{if(!['trend','fib','measure'].includes(mode))return; const p=point(e); if(!first){first=p;tip.style.display='block';tip.style.left=(p.cx+8)+'px';tip.style.top=(p.cy+8)+'px';tip.textContent='حدد النقطة الثانية';return;} if(mode==='trend'){line(first.x,first.y,p.x,p.y,'#4aa3ff','');} else if(mode==='fib'){[0,.236,.382,.5,.618,1].forEach((lv,i)=>{const y=first.y+(p.y-first.y)*lv; const cols=['#49d17d','#67a8ff','#f2c14e','#d77bff','#ff8a65','#49d17d']; line(Math.min(first.x,p.x),y,Math.max(first.x,p.x),y,cols[i],'3 2'); label(Math.max(first.x,p.x)+4,y-2,(lv*100).toFixed(1)+'%');});} else {line(first.x,first.y,p.x,p.y,'#f2c14e','4 3'); const dx=p.x-first.x,dy=p.y-first.y; label((first.x+p.x)/2,(first.y+p.y)/2-6,'Δ '+Math.sqrt(dx*dx+dy*dy).toFixed(1),'#f2c14e');} first=null;tip.style.display='none';});
    })();
    </script>`;
    html = html.replace("</body>", script + `<div style="display:none">${VERSION}</div></body>`);
    const headers = new Headers(res.headers);
    headers.set("content-type","text/html; charset=UTF-8");
    headers.set("cache-control","no-store, no-cache, must-revalidate");
    return new Response(html,{status:res.status,headers});
  }
};
