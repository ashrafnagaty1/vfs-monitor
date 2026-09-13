import enhanced from "./sector_enhanced.js";

const VERSION="market-terminal-v4-server-2026-09-14";
const DASHBOARD_URL="https://vfs-monitor.folkhero3.workers.dev/dashboard";

function esc(v){return String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function n(v,d=2){const x=Number(v);return Number.isFinite(x)?x.toFixed(d):"-"}
function sessionLabel(s){return({SESSION:"🟢 الجلسة مفتوحة",PRE_MARKET:"🟠 ما قبل الجلسة",CLOSED:"⚫ السوق مغلق",WEEKEND:"🔒 عطلة أسبوعية"}[s]||s||"-")}
async function tg(env,chat,text,extra={}){const r=await fetch(`https://api.telegram.org/bot${env.TOKEN}/sendMessage`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({chat_id:chat,text,parse_mode:"HTML",disable_web_page_preview:true,...extra})});return r.ok}

function htmlPage(state,selected){
  const x=state?.pro_engine_snapshot||{};
  const top=Array.isArray(x.top)?x.top:[];
  const details=Array.isArray(x.details)?x.details:top;
  const plans=Array.isArray(state?.trade_lifecycle?.plans)?state.trade_lifecycle.plans:[];
  const planMap=Object.fromEntries(plans.map(p=>[String(p.symbol||"").toUpperCase(),p]));
  const sym=(selected&&details.some(t=>String(t.symbol).toUpperCase()===selected.toUpperCase()))?selected.toUpperCase():(top[0]?.symbol||"");
  const t=details.find(z=>String(z.symbol).toUpperCase()===String(sym).toUpperCase())||{};
  const p=planMap[String(sym).toUpperCase()]||{};
  const r=x.market_regime||{};
  const ses=x.market_session||{};
  const live=x.quote_mode==="LIVE";
  const rows=top.map(z=>{
    const pp=planMap[String(z.symbol).toUpperCase()]||{};
    const cls=String(z.symbol).toUpperCase()===String(sym).toUpperCase()?"sel":"";
    const status=pp.status||"WATCH";
    return `<tr class="${cls}"><td><a href="/dashboard?s=${encodeURIComponent(z.symbol)}">${esc(z.symbol)}</a></td><td>${n(z.price)}</td><td>${n(z.score,0)}</td><td class="${status==='ENTRY'?'entry':'watch'}">${esc(status)}</td><td>${n(pp.trigger)}</td><td>${n(pp.dynamic_stop??pp.initial_stop??z.stop)}</td><td>${n(pp.rr_to_t1_now)}</td><td>${n(z.rsi,1)}</td><td>${n(z.adx,1)}</td><td>${n(z.volume_ratio)}x</td></tr>`
  }).join("");
  const why=Array.isArray(t.why)&&t.why.length?t.why.join(" • "):"—";
  const setups=Array.isArray(t.setups)&&t.setups.length?t.setups.join(" + "):"—";
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta http-equiv="refresh" content="30"><meta name="theme-color" content="#06101c"><title>EGX Smart Terminal</title><style>*{box-sizing:border-box}body{margin:0;background:#06101c;color:#d8e4ef;font-family:Tahoma,Arial,sans-serif}header{position:sticky;top:0;z-index:5;background:#081625;border-bottom:1px solid #17344d;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}.brand{font-weight:900;color:#fff}.ver{font-size:11px;color:#8fb7d9}.wrap{max-width:1250px;margin:auto;padding:12px}.warn{padding:10px 12px;border-radius:10px;margin-bottom:10px;background:${live?'#103322':'#3a2a0c'};border:1px solid ${live?'#245d42':'#735516'};color:${live?'#8ef0b2':'#ffd77a'};font-size:13px}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}.kpi,.panel{background:#0b1928;border:1px solid #17344d;border-radius:12px}.kpi{padding:11px}.kpi small{color:#7f9db7}.kpi b{display:block;margin-top:6px;font-size:18px}.layout{display:grid;grid-template-columns:1.6fr .9fr;gap:10px}.panel{overflow:hidden}.pt{padding:10px 12px;border-bottom:1px solid #17344d;font-weight:700;color:#fff}.scroll{overflow:auto;max-height:66vh}table{border-collapse:collapse;width:100%;min-width:790px;font-size:12px}th{position:sticky;top:0;background:#102238;color:#88a9c5;padding:9px 7px;border-bottom:1px solid #23425d}td{text-align:center;padding:9px 7px;border-bottom:1px solid #122b40}tr.sel{background:#112940}a{color:#fff;text-decoration:none;font-weight:800}.watch{color:#ffd166}.entry{color:#45e08b}.detail{padding:14px}.name{font-size:28px;font-weight:900;color:#fff}.price{font-size:34px;margin:8px 0}.pill{display:inline-block;padding:4px 8px;border-radius:10px;background:#142a3e;margin:2px;font-size:11px}.levels{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-top:10px}.lv{padding:9px;background:#091522;border:1px solid #16324b;border-radius:9px}.lv small{color:#7895ad}.lv b{display:block;margin-top:5px}.reasons{margin-top:12px;font-size:12px;line-height:1.8;color:#adc2d4}.foot{padding:10px;text-align:center;color:#62819b;font-size:11px}@media(max-width:820px){.kpis{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.scroll{max-height:45vh}}</style></head><body><header><div class="brand">EGX SMART TERMINAL</div><div class="ver">${VERSION}</div></header><div class="wrap"><div class="warn">${live?`🟢 مصدر أسعار حي — ${esc(x.quote_source||"-")}`:`⚠️ بيانات تقييم/متأخرة وليست لحظية للتنفيذ — ${esc(x.quote_source||"-")}`}</div><div class="kpis"><div class="kpi"><small>حالة السوق</small><b>${esc(sessionLabel(ses.status))}</b></div><div class="kpi"><small>Market Regime</small><b>${esc(r.name||"-")}</b></div><div class="kpi"><small>Breadth</small><b>${n(r.breadth,1)}%</b></div><div class="kpi"><small>Avg Score</small><b>${n(r.avg_score,1)}</b></div></div><div class="layout"><section class="panel"><div class="pt">Market Watch / الفرص الفنية</div><div class="scroll"><table><thead><tr><th>السهم</th><th>السعر</th><th>Score</th><th>الحالة</th><th>Trigger</th><th>Stop</th><th>RR</th><th>RSI</th><th>ADX</th><th>Vol</th></tr></thead><tbody>${rows||'<tr><td colspan="10">لا توجد بيانات سوق في Snapshot</td></tr>'}</tbody></table></div></section><aside class="panel"><div class="pt">Technical Terminal</div><div class="detail"><div class="name">${esc(sym||"—")}</div><div class="price">${n(t.price)}</div><span class="pill">Score ${n(t.score,0)}</span><span class="pill">${esc(t.confidence||"-")}</span><span class="pill">${esc(p.status||"WATCH")}</span><div class="levels"><div class="lv"><small>Trigger</small><b>${n(p.trigger)}</b></div><div class="lv"><small>Dynamic Stop</small><b>${n(p.dynamic_stop??p.initial_stop??t.stop)}</b></div><div class="lv"><small>T1</small><b>${n(p.target1??t.target1)}</b></div><div class="lv"><small>T2</small><b>${n(p.target2??t.target2)}</b></div><div class="lv"><small>T3</small><b>${n(p.target3??t.target3)}</b></div><div class="lv"><small>RR→T1</small><b>${n(p.rr_to_t1_now)}</b></div><div class="lv"><small>RSI / ADX</small><b>${n(t.rsi,1)} / ${n(t.adx,1)}</b></div><div class="lv"><small>MFI / Vol</small><b>${n(t.mfi,1)} / ${n(t.volume_ratio)}x</b></div></div><div class="reasons"><b>Patterns:</b> ${esc(setups)}<br><b>الأسباب:</b> ${esc(why)}<br><b>Support20:</b> ${n(t.support_20)} &nbsp; <b>Resistance20:</b> ${n(t.resistance_20)}<br><b>Resistance50:</b> ${n(t.resistance_50)}</div></div></aside></div><div class="foot">آخر تحديث: ${esc(x.at||"-")} | تحديث تلقائي كل 30 ثانية</div></div></body></html>`
}

export default {async fetch(req,env,ctx){
  const u=new URL(req.url);
  if(req.method==="GET"&&u.pathname==="/dashboard"){
    let state=null;
    try{state=env.STATE?await env.STATE.get("latest","json"):null}catch(_){state=null}
    if(!state?.pro_engine_snapshot){return new Response(`<!doctype html><meta charset="utf-8"><body style="background:#06101c;color:white;font-family:Tahoma;padding:30px;direction:rtl"><h2>EGX SMART TERMINAL</h2><p>تعذر قراءة Snapshot من KV.</p><p>STATE binding: ${env.STATE?"موجود":"غير موجود"}</p><p>الإصدار: ${VERSION}</p></body>`,{status:503,headers:{"content-type":"text/html; charset=UTF-8","cache-control":"no-store"}})}
    return new Response(htmlPage(state,u.searchParams.get("s")||""),{headers:{"content-type":"text/html; charset=UTF-8","cache-control":"no-store"}})
  }
  if(req.method==="GET"&&u.pathname==="/terminal-status"){
    let raw=null; try{raw=env.STATE?await env.STATE.get("latest"):null}catch(_){raw=null}
    return Response.json({ok:true,version:VERSION,state_binding:!!env.STATE,has_raw_state:!!raw,raw_size:raw?raw.length:0})
  }
  if(req.method==="POST"&&u.pathname==="/telegram"){
    let body=null;try{body=await req.clone().json()}catch(_){body=null}
    const text=body?.message?.text,chat=body?.message?.chat?.id;
    if(text==="📊 الشاشة اللحظية"&&(!env.CHAT_ID||String(chat)===String(env.CHAT_ID))){await tg(env,chat,"📊 <b>EGX Smart Terminal</b>\nافتح الشاشة التفاعلية من الزر بالأسفل.",{reply_markup:{inline_keyboard:[[{text:"فتح الشاشة 📊",web_app:{url:DASHBOARD_URL}}]]}});return Response.json({ok:true,feature:"market-terminal-v4",version:VERSION})}
  }
  return enhanced.fetch(req,env,ctx)
}};
