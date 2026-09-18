import legacyWorker from "../src/tradingview_core_wrapper.js";

const BRAND="ReFo . EGX Smart Trader";
const DEFAULT_WEBAPP="https://refogx-pro.folkhero3.workers.dev/";
const kb=rows=>({keyboard:rows,resize_keyboard:true,is_persistent:true});
const MAIN=kb([
 ["🖥️ الشاشة اللحظية","🤖 المساعد الذكي"],
 ["💳 اشترك الآن / ترقية"],
 ["📈 أسهم المضاربة اليومية","📊 الصفقات"],
 ["📈 تحليل الأسهم","♟️ التحليل المتقدم"],
 ["💼 المحافظ والتنبيهات","👤 حسابي"]
]);
const ADV=kb([
 ["🔮 التوقع الزمني","🌀 التوقع الفركتالي"],
 ["🦋 أنماط الهارمونيك","📐 تحليل جان"],
 ["🌊 موجات إليوت"],
 ["💰 Smart Money","🎯 قناص EGX V2"],
 ["🏠 القائمة الرئيسية"]
]);
const TRADES=kb([
 ["📊 صفقات مفتوحة","✅ تحقق الهدف الأول","✅ تحقق الهدف الثاني"],
 ["✅ تحقق الهدف الثالث","🏠 القائمة الرئيسية"]
]);
const PORT=kb([
 ["💼 محفظتي","⭐ قائمة المتابعة"],
 ["🚨 تنبيهاتي","📈 تقرير الأداء"],
 ["🏠 القائمة الرئيسية"]
]);
const ACCOUNT=kb([
 ["📊 حالة البيانات","⚙️ الإعدادات"],
 ["❓ مساعدة","🏠 القائمة الرئيسية"]
]);
const STOCKS=["COMI","HRHO","TMGH","EFIH","FWRY","SWDY","EAST","ORWE"];
const STOCK_PICK=kb([["📊 COMI","📊 HRHO","📊 TMGH","📊 EFIH"],["📊 FWRY","📊 SWDY","📊 EAST","📊 ORWE"],["✍️ كتابة كود سهم","🏠 القائمة الرئيسية"]]);

function token(e){return e.TELEGRAM_BOT_TOKEN||e.TOKEN||""}
function gate(e){return e.TELEGRAM_CHAT_ID||e.CHAT_ID||""}
function legacyEnv(e){const x=Object.create(e||null);x.TOKEN=e.TOKEN||e.TELEGRAM_BOT_TOKEN;x.CHAT_ID=e.CHAT_ID||e.TELEGRAM_CHAT_ID;return x}
function api(e,m){return `https://api.telegram.org/bot${token(e)}/${m}`}
async function tg(e,m,p){const r=await fetch(api(e,m),{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(p)});const d=await r.json().catch(()=>({}));if(!r.ok||!d.ok)throw new Error(d.description||`Telegram ${m} failed`);return d.result}
async function send(e,c,t,reply_markup){return tg(e,"sendMessage",{chat_id:String(c),text:t,parse_mode:"HTML",disable_web_page_preview:true,...(reply_markup?{reply_markup}:{})})}
const esc=v=>String(v??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const num=(v,d=3)=>{const x=Number(v);return Number.isFinite(x)?x.toFixed(d).replace(/\.0+$/,"").replace(/(\.\d*?)0+$/,"$1"):"—"};
const arr=v=>Array.isArray(v)?v:(v&&typeof v==="object"?Object.values(v):[]);
async function state(e){try{return e.STATE?await e.STATE.get("latest","json"):null}catch{return null}}
const snap=s=>s?.pro_engine_snapshot||{};
const techs=s=>arr(snap(s).top);
const plans=s=>arr(s?.trade_lifecycle?.plans);
const findTech=(s,sym)=>techs(s).find(x=>String(x.symbol||"").toUpperCase()===sym);
const findPlan=(s,sym)=>plans(s).find(x=>String(x.symbol||"").toUpperCase()===sym);
function sourceNote(s){const x=snap(s),live=x.quote_mode==="LIVE";return `\n\n<i>${live?"🟢 LIVE":"⚠️ DELAYED_EVALUATION"} · المصدر: ${esc(x.quote_source||"غير محدد")} · آخر تحديث: ${esc(x.at||"—")}</i>`}
async function showMenu(e,c){return send(e,c,`🚀 <b>${BRAND}</b>\n\nمرحبًا بك في بوت البورصة المصرية.\nاختر من القائمة بالأسفل 👇\n\n⚠️ مساعد قرار وتحليل؛ لا يضمن الربح.`,MAIN)}
async function showLive(e,c){const url=e.REFO_WEBAPP_URL||DEFAULT_WEBAPP;await send(e,c,"🖥️ <b>EGX Terminal Pro</b>\n\nمنصة التداول والتحليل المتقدمة متاحة الآن.\nاضغط لفتح الشاشة اللحظية داخل تيليجرام.\n\n📊 TradingView للشارت، وبيانات ReFo خارج الشارت تعرض مصدرها بوضوح.",{inline_keyboard:[[{text:"🚀 فتح الشاشة اللحظية",web_app:{url}}]]});return send(e,c,"اختر أداة أخرى من القائمة 👇",MAIN)}
function stockCard(s,sym){const t=findTech(s,sym),p=findPlan(s,sym);if(!t&&!p)return `📈 <b>تحليل ${esc(sym)}</b>\n\nلا توجد بيانات موثوقة لهذا السهم في آخر Snapshot.`+sourceNote(s);const price=t?.price??p?.price,score=t?.score??p?.score,status=p?.status||"WATCH";let o=`📈 <b>تحليل السهم — ${esc(sym)}</b>\n━━━━━━━━━━━━━━\n💰 السعر: <b>${num(price)}</b> جنيه\n📌 الحالة: <b>${esc(status)}</b> · Score ${num(score,0)}/100\n`;if(t)o+=`\n📊 <b>الفحص الفني</b>\nRSI ${num(t.rsi,1)} · ADX ${num(t.adx,1)} · MFI ${num(t.mfi,1)}\nVolume ${num(t.volume_ratio,2)}x · Mom5 ${num(t.momentum_5d,2)}% · Mom20 ${num(t.momentum_20d,2)}%\nEMA20 ${num(t.ema20)} · EMA50 ${num(t.ema50)} · EMA200 ${num(t.ema200)}\nS20 ${num(t.support_20)} · R20 ${num(t.resistance_20)} · R50 ${num(t.resistance_50)}\n`;if(p)o+=`\n🎯 <b>خطة المتابعة</b>\nالتفعيل: <b>${num(p.trigger)}</b> · وقف: ${num(p.dynamic_stop??p.initial_stop)}\nT1 ${num(p.target1)} · T2 ${num(p.target2)} · T3 ${num(p.target3)}\nR:R ${num(p.rr_to_t1_now,2)} · البعد ${num(p.distance_to_trigger_pct,2)}%\n`;const why=arr(t?.why).slice(0,4);if(why.length)o+="\n💡 "+why.map(esc).join(" • ");if(snap(s).quote_mode!=="LIVE")o+="\n\n⛔ WATCH المتأخر لا يتحول إلى ENTRY.";return o+sourceNote(s)}
function oppText(s){const a=plans(s).filter(p=>String(p.status).toUpperCase()==="WATCH").sort((a,b)=>Number(b.score||0)-Number(a.score||0)).slice(0,10);let o="🎯 <b>قناص EGX V2 — أفضل الفرص</b>\n━━━━━━━━━━━━━━\n";if(!a.length)return o+"لا توجد فرص WATCH مسجلة حاليًا."+sourceNote(s);a.forEach((p,i)=>{o+=`\n<b>#${i+1} ${esc(p.symbol)}</b> · جودة ${num(p.score,0)}/100\n💰 تفعيل ${num(p.trigger)} · 🛑 ${num(p.dynamic_stop??p.initial_stop)}\n🎯 ${num(p.target1)} / ${num(p.target2)} / ${num(p.target3)}\nR:R ${num(p.rr_to_t1_now,2)} · سيولة ${num(p.liquidity_score,0)}\n`});o+="\n⚠️ الخطة لا تتفعل إلا عند تحقق شرط الدخول من مصدر Live.";return o+sourceNote(s)}
function tradeText(s,stage){const P=s?.signal_portfolio||{},all=[...arr(P.open_positions),...arr(P.closed_trades),...plans(s)],ord={T1:1,T2:2,T3:3};let rows;if(stage==="OPEN")rows=arr(P.open_positions).length?arr(P.open_positions):plans(s).filter(x=>["ENTRY","T1","T2"].includes(String(x.status||x.lifecycle_status).toUpperCase()));else rows=all.filter(x=>ord[String(x.stage||x.status||x.lifecycle_status).toUpperCase()]>=ord[stage]);const title=stage==="OPEN"?"📊 صفقات مفتوحة":`✅ صفقات حققت ${stage}`;let o=`<b>${title}</b>\n━━━━━━━━━━━━━━\n`;if(!rows.length)return o+"لا توجد سجلات مطابقة حاليًا."+sourceNote(s);const seen=new Set();for(const x of rows){const id=x.signal_id||`${x.symbol}:${x.entry_price||x.trigger}`;if(seen.has(id))continue;seen.add(id);o+=`\n🔹 <b>${esc(x.symbol||"—")}</b> · ${esc(x.stage||x.status||"ACTIVE")}\n💰 دخول ${num(x.entry_price??x.trigger)} · 🛑 ${num(x.dynamic_stop??x.initial_stop)}\n🎯 ${num(x.target1)} / ${num(x.target2)} / ${num(x.target3)}\n`;if(seen.size>=18)break}return o+sourceNote(s)}
function advancedMenuText(){return "♟️ <b>التحليل المتقدم</b>\n\nاختر نمط التحليل:\n🔮 التوقع الزمني · 🌀 الفركتالي\n📐 جان · 🦋 الهارمونيك · 🌊 إليوت\n💰 Smart Money · 🎯 EGX V2\n\nكل نتيجة تستخدم بيانات متاحة فعلًا؛ أي محرك غير متوفر في Snapshot سيظهر كغير متاح بدل اختلاق نتيجة."}
function advancedResult(s,kind){const x=snap(s),pre=x.advanced_analysis||s?.advanced_analysis||{},map={"🔮 التوقع الزمني":"temporal","🌀 التوقع الفركتالي":"fractal","📐 تحليل جان":"gann","🦋 أنماط الهارمونيك":"harmonic","🌊 موجات إليوت":"elliott","💰 Smart Money":"smart_money"};const key=map[kind],data=pre?.[key];if(data){return `${kind} <b>— آخر نتيجة مؤكدة</b>\n━━━━━━━━━━━━━━\n<pre>${esc(JSON.stringify(data,null,2).slice(0,3200))}</pre>`+sourceNote(s)}if(kind==="💰 Smart Money"){const a=techs(s).slice(0,8);let o="💰 <b>Smart Money — فحص OHLCV</b>\n━━━━━━━━━━━━━━\n";if(!a.length)return o+"لا توجد بيانات كافية."+sourceNote(s);for(const t of a)o+=`\n<b>${esc(t.symbol)}</b> · Score ${num(t.score,0)} · MFI ${num(t.mfi,1)} · Vol ${num(t.volume_ratio,2)}x · Golden ${t.golden?"YES":"NO"}`;o+="\n\n<i>هذه مؤشرات OHLCV وليست Order Book أو تدفق مؤسسي مؤكد.</i>";return o+sourceNote(s)}return `${kind}\n\n⚠️ محرك ${kind} موجود في طبقة ReFo التحليلية، لكن لا توجد نتيجة منه داخل Snapshot الحالي على Cloudflare. لن أعرض أرقامًا مصطنعة.\n\nاستخدم محرك Python/المزامنة لإرسال النتيجة الموثوقة ثم ستظهر هنا.`+sourceNote(s)}
function portfolioText(s){const p=s?.signal_portfolio||{},open=arr(p.open_positions),closed=arr(p.closed_trades),m=p.performance||{};let o="💼 <b>محفظتي</b>\n━━━━━━━━━━━━━━\n"+`مفتوحة: ${open.length} · مغلقة: ${closed.length}\nWin Rate: ${num(m.win_rate_pct,1)}% · Total R: ${num(m.total_r,2)} · Avg R: ${num(m.avg_r,2)}\n`;open.slice(0,10).forEach(x=>o+=`\n🔹 <b>${esc(x.symbol)}</b> دخول ${num(x.entry_price)} · آخر ${num(x.last_price)} · R ${num(x.unrealized_r,2)}`);return o+sourceNote(s)}
function alertsText(s){const a=arr(s?.trade_alerts).slice(-15).reverse();let o="🚨 <b>التنبيهات الذكية</b>\n━━━━━━━━━━━━━━\n";if(!a.length)return o+"لا توجد تنبيهات مسجلة."+sourceNote(s);a.forEach(x=>o+=`\n• <b>${esc(x.symbol)}</b> · ${esc(x.kind||x.level||"Alert")}\n${esc(x.text||"")} ${esc(x.at||"")}`);return o+sourceNote(s)}
function watchText(s){const a=arr(snap(s).watchlist_next_session||s?.watchlist);let o="⭐ <b>قائمة المتابعة</b>\n━━━━━━━━━━━━━━\n";if(!a.length)return o+"لا توجد قائمة متابعة متاحة في Snapshot الحالي."+sourceNote(s);a.slice(0,20).forEach(x=>o+=`\n• <b>${esc(x.symbol||x)}</b>${x.trigger?` · Trigger ${num(x.trigger)}`:""}`);return o+sourceNote(s)}
function assistantText(s){const a=plans(s).filter(p=>p.status==="WATCH").sort((a,b)=>Number(b.score||0)-Number(a.score||0)).slice(0,5),r=snap(s).market_regime||{};let o=`🤖 <b>المساعد الذكي</b>\n━━━━━━━━━━━━━━\nالسوق: ${esc(r.name||"—")} · Breadth العينة: ${num(r.breadth,1)}%\n\n`;if(!a.length)o+="لا توجد خطط WATCH كافية للتحليل.";else a.forEach((p,i)=>o+=`${i+1}) <b>${esc(p.symbol)}</b> · Score ${num(p.score,0)} · RR ${num(p.rr_to_t1_now,2)} · بعد ${num(p.distance_to_trigger_pct,2)}%\n`);o+="\n💡 اسأل عن سهم عبر «تحليل COMI». التنفيذ يظل مشروطًا بجودة ومصدر البيانات.";return o+sourceNote(s)}
function dataStatus(s){const x=snap(s);return `📊 <b>حالة البيانات</b>\n━━━━━━━━━━━━━━\nMode: <b>${esc(x.quote_mode||"—")}</b>\nQuote source: ${esc(x.quote_source||"—")}\nHistory source: ${esc(x.history_source||"—")}\nUpdated: ${esc(x.at||"—")}\nUniverse: ${techs(s).length} سهم\n\nBid/Ask/Depth/Fundamentals لا تعرض إلا عند وجود مصدر حقيقي.`}
async function delegate(req,e,ctx,u,mapped){const b=structuredClone(u);if(b?.message)b.message.text=mapped;const x=new URL(req.url);x.pathname="/telegram";x.search="";const r=await legacyWorker.fetch(new Request(x.toString(),{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(b)}),legacyEnv(e),ctx);return Response.json({ok:true,delegated:true,legacy_status:r.status})}
async function register(req,e){if(!token(e))return new Response("Missing Telegram bot token",{status:503});const o=new URL(req.url).origin,p={url:`${o}/telegram/webhook`,allowed_updates:["message"],drop_pending_updates:false};if(e.TELEGRAM_WEBHOOK_SECRET)p.secret_token=e.TELEGRAM_WEBHOOK_SECRET;const r=await fetch(api(e,"setWebhook"),{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(p)});return new Response(await r.text(),{status:r.status,headers:{"content-type":"application/json; charset=utf-8"}})}
async function status(e){if(!token(e))return Response.json({ok:false,error:"missing_token"},{status:503});const r=await fetch(api(e,"getWebhookInfo")),d=await r.json().catch(()=>({})),x=d.result||{};return Response.json({ok:!!d.ok,url:x.url||"",pending_update_count:x.pending_update_count||0,last_error_message:x.last_error_message||null})}
async function webhook(req,e,ctx){if(!token(e))return new Response("Missing token",{status:503});if(e.TELEGRAM_WEBHOOK_SECRET&&req.headers.get("X-Telegram-Bot-Api-Secret-Token")!==e.TELEGRAM_WEBHOOK_SECRET)return new Response("Forbidden",{status:403});const u=await req.json().catch(()=>({})),m=u.message||{},c=String(m?.chat?.id||""),t=String(m?.text||"").trim();if(!c||!t)return Response.json({ok:true});if(gate(e)&&c!==String(gate(e)))return Response.json({ok:true});if(["/start","/menu","🏠 القائمة الرئيسية","⬅️ العودة للقائمة الرئيسية"].includes(t)){await showMenu(e,c);return Response.json({ok:true,feature:"main"})}if(["🖥️ الشاشة اللحظية","📊 الشاشة اللحظية"].includes(t)){await showLive(e,c);return Response.json({ok:true,feature:"live"})}const s=await state(e);
 if(t==="📊 الصفقات"){await send(e,c,"📊 <b>الصفقات</b>\nاختر النوع:",TRADES);return Response.json({ok:true})}
 if(t==="📊 صفقات مفتوحة"){await send(e,c,tradeText(s,"OPEN"),TRADES);return Response.json({ok:true})}
 if(t.startsWith("✅ تحقق الهدف")){const st=t.includes("الأول")?"T1":t.includes("الثاني")?"T2":"T3";await send(e,c,tradeText(s,st),TRADES);return Response.json({ok:true})}
 if(t==="♟️ التحليل المتقدم"||t==="🧠 التحليل المتقدم"){await send(e,c,advancedMenuText(),ADV);return Response.json({ok:true})}
 if(["🔮 التوقع الزمني","🌀 التوقع الفركتالي","📐 تحليل جان","🦋 أنماط الهارمونيك","🌊 موجات إليوت","💰 Smart Money"].includes(t)){await send(e,c,advancedResult(s,t),ADV);return Response.json({ok:true})}
 if(t==="🎯 قناص EGX V2"||t==="📈 أسهم المضاربة اليومية"||t==="🎯 فرص اليوم"){await send(e,c,oppText(s),ADV);return Response.json({ok:true})}
 if(t==="📈 تحليل الأسهم"||t==="🔍 تحليل سهم"){await send(e,c,"📈 <b>تحليل الأسهم</b>\nاختر سهمًا أو اكتب: <code>تحليل COMI</code>",STOCK_PICK);return Response.json({ok:true})}
 if(/^📊\s+[A-Z0-9]+$/.test(t)||/^تحليل\s+[A-Za-z0-9.]+$/i.test(t)){const sym=t.replace(/^📊\s+/,"").replace(/^تحليل\s+/i,"").toUpperCase();await send(e,c,stockCard(s,sym),STOCK_PICK);return Response.json({ok:true})}
 if(t==="✍️ كتابة كود سهم"){await send(e,c,"✍️ اكتب مثلًا: <code>تحليل COMI</code>",STOCK_PICK);return Response.json({ok:true})}
 if(t==="💼 المحافظ والتنبيهات"){await send(e,c,"💼 <b>المحافظ والتنبيهات</b>\nاختر الأداة:",PORT);return Response.json({ok:true})}
 if(t==="💼 محفظتي"){await send(e,c,portfolioText(s),PORT);return Response.json({ok:true})}
 if(t==="🚨 تنبيهاتي"){await send(e,c,alertsText(s),PORT);return Response.json({ok:true})}
 if(t==="⭐ قائمة المتابعة"||t==="📋 قائمة المتابعة"){await send(e,c,watchText(s),PORT);return Response.json({ok:true})}
 if(t==="📈 تقرير الأداء")return delegate(req,e,ctx,u,"📈 تقرير الأداء");
 if(t==="🤖 المساعد الذكي"){await send(e,c,assistantText(s),MAIN);return Response.json({ok:true})}
 if(t==="👤 حسابي"){await send(e,c,"👤 <b>حسابي</b>\nإدارة حالة البيانات والإعدادات والمساعدة.",ACCOUNT);return Response.json({ok:true})}
 if(t==="📊 حالة البيانات"){await send(e,c,dataStatus(s),ACCOUNT);return Response.json({ok:true})}
 if(t==="❓ مساعدة"){await send(e,c,"❓ <b>مساعدة</b>\nاستخدم الأزرار كمسار أساسي.\nاختصارات: /start /menu أو «تحليل COMI».\nالشاشة اللحظية تفتح WebApp مباشرة.",ACCOUNT);return Response.json({ok:true})}
 const aliases=new Map([["💳 اشترك الآن / ترقية","💳 اشتراك / ترقية"],["⚙️ الإعدادات","⚙️ الإعدادات"]]);
 return delegate(req,e,ctx,u,aliases.get(t)||t)
}
export default{async fetch(req,e,ctx){const u=new URL(req.url);if(req.method==="GET"&&u.pathname==="/telegram/health")return Response.json({ok:true,service:BRAND,mode:"reference-clone-all-in-one",legacy_routes:"preserved",tradingview_core:"delegated",menus:["main","trades","advanced","portfolio","account"]});if(req.method==="GET"&&u.pathname==="/telegram/status")return status(e);if(req.method==="POST"&&u.pathname==="/telegram/register")return register(req,e);if(req.method==="POST"&&u.pathname==="/telegram/webhook")return webhook(req,e,ctx);return legacyWorker.fetch(req,legacyEnv(e),ctx)}};
