const MAIN_KEYBOARD = {
  keyboard: [
    [{ text: "📊 الشاشة اللحظية" }, { text: "🎯 فرص اليوم" }],
    [{ text: "🔍 تحليل سهم" }, { text: "🧠 التحليل المتقدم" }],
    [{ text: "🟡 Golden Zone" }, { text: "🚀 الإشارات النشطة" }],
    [{ text: "🚨 تنبيهاتي" }, { text: "💼 محفظتي" }],
    [{ text: "📈 تقرير الأداء" }, { text: "🔮 فرص بكرة" }],
    [{ text: "🗺️ أداء القطاعات" }, { text: "🤖 المساعد الذكي" }],
    [{ text: "⚙️ الإعدادات" }]
  ],
  resize_keyboard: true,
  is_persistent: true
};

async function tg(env, method, payload = {}) {
  if (!env.TOKEN) throw new Error("Missing TOKEN secret");
  const r = await fetch(`https://api.telegram.org/bot${env.TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await r.json();
  if (!data.ok) throw new Error(data.description || `Telegram ${method} failed`);
  return data.result;
}

async function send(env, chatId, text, extra = {}) {
  return tg(env, "sendMessage", {
    chat_id: chatId,
    text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
    ...extra
  });
}

function isAllowed(env, chatId) {
  return !env.CHAT_ID || String(chatId) === String(env.CHAT_ID);
}

function menuText() {
  return "🤖 <b>EGX Smart Scanner</b>\n\nمتصل عبر Cloudflare Worker Webhook.\nاختر من القائمة بالأسفل.";
}

function esc(v) {
  return String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function n(v, d = 2) {
  const x = Number(v);
  return Number.isFinite(x) ? x.toFixed(d) : "-";
}

async function loadState(env) {
  if (!env.STATE) return null;
  try { return await env.STATE.get("latest", "json"); } catch (_) { return null; }
}

function sourceNote(s) {
  const snap = s?.pro_engine_snapshot;
  if (!snap) return "";
  const delayed = snap.quote_mode && snap.quote_mode !== "LIVE";
  return `\n\n<i>${delayed ? "⚠️ بيانات تقييم/متأخرة وليست لحظية للتنفيذ" : "🟢 مصدر أسعار حي"}\nالمصدر: ${esc(snap.quote_source || "-")}</i>`;
}

function marketWatchText(s) {
  const snap = s?.pro_engine_snapshot;
  if (!snap) return "📊 <b>الشاشة اللحظية</b>\n\nلا توجد لقطة سوق مخزنة حتى الآن.";
  const r = snap.market_regime || {};
  const top = Array.isArray(snap.top) ? snap.top.slice(0, 10) : [];
  let out = `📊 <b>الشاشة اللحظية</b>\n\n`;
  out += `السوق: <b>${esc(r.name || "-")}</b>\n`;
  out += `Breadth: ${n(r.breadth,1)}% | Avg Score: ${n(r.avg_score,1)}\n`;
  out += `آخر تحديث: ${esc(snap.at || "-")}\n\n`;
  if (!top.length) out += "لا توجد أسهم مصنفة حاليًا.";
  else top.forEach((x, i) => {
    out += `${i+1}. <b>${esc(x.symbol)}</b>  ${n(x.price)}  | Score ${n(x.score,0)} | ${esc(x.confidence || "-")}\n`;
  });
  return out + sourceNote(s);
}

function opportunitiesText(s) {
  const plans = Array.isArray(s?.trade_lifecycle?.plans) ? s.trade_lifecycle.plans.slice(0, 8) : [];
  if (!plans.length) return "🎯 <b>فرص اليوم</b>\n\nلا توجد خطط تداول مخزنة حاليًا.";
  let out = "🎯 <b>فرص اليوم / WATCH</b>\n\n";
  plans.forEach((p, i) => {
    out += `${i+1}. <b>${esc(p.symbol)}</b> — ${esc(p.status || "WATCH")}\n`;
    out += `السعر ${n(p.price)} | تفعيل ${n(p.trigger)} | وقف ${n(p.dynamic_stop ?? p.initial_stop)}\n`;
    out += `T1 ${n(p.target1)} | T2 ${n(p.target2)} | Score ${n(p.score,0)}\n\n`;
  });
  return out + sourceNote(s);
}

function tomorrowText(s) {
  const a = Array.isArray(s?.pro_engine_snapshot?.watchlist_next_session) ? s.pro_engine_snapshot.watchlist_next_session.slice(0, 10) : [];
  if (!a.length) return "🔮 <b>فرص الجلسة القادمة</b>\n\nلا توجد قائمة حالية.";
  let out = "🔮 <b>فرص الجلسة القادمة</b>\n\n";
  a.forEach((x, i) => {
    out += `${i+1}. <b>${esc(x.symbol)}</b> | تفعيل ${n(x.trigger)} | وقف ${n(x.stop)} | Score ${n(x.score,0)}\n`;
  });
  return out + sourceNote(s);
}

function signalsText(s) {
  const plans = Array.isArray(s?.trade_lifecycle?.plans) ? s.trade_lifecycle.plans : [];
  const active = plans.filter(p => p.status && p.status !== "WATCH");
  if (!active.length) return "🚀 <b>الإشارات النشطة</b>\n\nلا توجد إشارات ENTRY نشطة حاليًا. البيانات المتأخرة تظل WATCH ولا تتحول إلى ENTRY." + sourceNote(s);
  let out = "🚀 <b>الإشارات النشطة</b>\n\n";
  active.slice(0,10).forEach((p,i) => out += `${i+1}. <b>${esc(p.symbol)}</b> — ${esc(p.status)} | ${n(p.price)}\n`);
  return out + sourceNote(s);
}

function stockText(s, symbol) {
  const sym = symbol.toUpperCase();
  const plans = Array.isArray(s?.trade_lifecycle?.plans) ? s.trade_lifecycle.plans : [];
  const p = plans.find(x => String(x.symbol).toUpperCase() === sym);
  const top = Array.isArray(s?.pro_engine_snapshot?.top) ? s.pro_engine_snapshot.top : [];
  const t = top.find(x => String(x.symbol).toUpperCase() === sym);
  if (!p && !t) return `🔍 لم أجد <b>${esc(sym)}</b> في آخر لقطة للمحرك.`;
  let out = `🔍 <b>تحليل ${esc(sym)}</b>\n\n`;
  if (p) {
    out += `الحالة: <b>${esc(p.status || "WATCH")}</b>\n`;
    out += `السعر: ${n(p.price)}\nالتفعيل: ${n(p.trigger)}\nالوقف: ${n(p.dynamic_stop ?? p.initial_stop)}\n`;
    out += `T1: ${n(p.target1)} | T2: ${n(p.target2)} | T3: ${n(p.target3)}\n`;
    out += `Score: ${n(p.score,0)} | ثقة: ${esc(p.confidence || "-")} | RR T1: ${n(p.rr_to_t1_now)}\n`;
  } else if (t) {
    out += `السعر: ${n(t.price)} | Score: ${n(t.score,0)} | ثقة: ${esc(t.confidence || "-")}\n`;
  }
  return out + sourceNote(s);
}

async function handleMessage(env, message) {
  const chatId = message?.chat?.id;
  const text = (message?.text || "").trim();
  if (!chatId || !text || !isAllowed(env, chatId)) return;

  if (text === "/start" || text === "/menu" || text === "⚙️ الإعدادات") {
    await send(env, chatId, menuText(), { reply_markup: MAIN_KEYBOARD });
    return;
  }

  if (text === "🔍 تحليل سهم") {
    await send(env, chatId, "🔍 <b>تحليل سهم</b>\n\nاكتب مثلًا: <code>تحليل COMI</code>", { reply_markup: MAIN_KEYBOARD });
    return;
  }

  const s = await loadState(env);

  if (text === "📊 الشاشة اللحظية") return send(env, chatId, marketWatchText(s), { reply_markup: MAIN_KEYBOARD });
  if (text === "🎯 فرص اليوم") return send(env, chatId, opportunitiesText(s), { reply_markup: MAIN_KEYBOARD });
  if (text === "🔮 فرص بكرة") return send(env, chatId, tomorrowText(s), { reply_markup: MAIN_KEYBOARD });
  if (text === "🚀 الإشارات النشطة") return send(env, chatId, signalsText(s), { reply_markup: MAIN_KEYBOARD });

  if (/^تحليل\s+/i.test(text)) {
    const symbol = text.split(/\s+/).slice(1).join(" ").toUpperCase();
    return send(env, chatId, stockText(s, symbol), { reply_markup: MAIN_KEYBOARD });
  }

  const fallback = {
    "🧠 التحليل المتقدم": "🧠 <b>التحليل المتقدم</b>\n\nسيتم ربط المؤشرات التفصيلية في المرحلة التالية.",
    "🟡 Golden Zone": "🟡 <b>Golden Zone</b>\n\nسيتم استخراج حالات Golden Zone من لقطة المحرك في التحديث التالي.",
    "🚨 تنبيهاتي": "🚨 <b>تنبيهاتي</b>\n\nربط إدارة التنبيهات مستمر.",
    "💼 محفظتي": "💼 <b>محفظتي</b>\n\nربط المحفظة مستمر.",
    "📈 تقرير الأداء": "📈 <b>تقرير الأداء</b>\n\nربط سجل الصفقات والأداء مستمر.",
    "🗺️ أداء القطاعات": "🗺️ <b>أداء القطاعات</b>\n\nربط خريطة القطاعات مستمر.",
    "🤖 المساعد الذكي": "🤖 <b>المساعد الذكي</b>\n\nسيتم ربط منطق القرار بعد اكتمال مزامنة الحالة."
  };
  if (fallback[text]) return send(env, chatId, fallback[text], { reply_markup: MAIN_KEYBOARD });

  await send(env, chatId, "استخدم الأزرار من القائمة 👇", { reply_markup: MAIN_KEYBOARD });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return Response.json({ ok: true, service: "EGX Smart Scanner Cloudflare Worker", state_binding: !!env.STATE });
    }

    if (request.method === "GET" && url.pathname === "/setup") {
      if (!env.TOKEN) return Response.json({ ok: false, error: "TOKEN secret is missing" }, { status: 500 });
      const webhookUrl = `${url.origin}/telegram`;
      try {
        const result = await tg(env, "setWebhook", { url: webhookUrl, allowed_updates: ["message"] });
        return Response.json({ ok: true, webhook: webhookUrl, result });
      } catch (e) {
        return Response.json({ ok: false, error: String(e.message || e) }, { status: 500 });
      }
    }

    if (request.method === "GET" && url.pathname === "/webhook-info") {
      try {
        const info = await tg(env, "getWebhookInfo", {});
        return Response.json({ ok: true, info });
      } catch (e) {
        return Response.json({ ok: false, error: String(e.message || e) }, { status: 500 });
      }
    }

    if (request.method === "POST" && url.pathname === "/sync") {
      if (!env.STATE) return Response.json({ ok: false, error: "STATE KV binding is missing" }, { status: 500 });
      if (!env.SYNC_SECRET) return Response.json({ ok: false, error: "SYNC_SECRET is missing" }, { status: 500 });
      const auth = request.headers.get("authorization") || "";
      if (auth !== `Bearer ${env.SYNC_SECRET}`) return Response.json({ ok: false, error: "unauthorized" }, { status: 401 });
      try {
        const body = await request.json();
        if (!body || typeof body !== "object") throw new Error("invalid state");
        await env.STATE.put("latest", JSON.stringify(body));
        return Response.json({ ok: true, synced_at: new Date().toISOString() });
      } catch (e) {
        return Response.json({ ok: false, error: String(e.message || e) }, { status: 400 });
      }
    }

    if (request.method === "GET" && url.pathname === "/state-status") {
      const s = await loadState(env);
      return Response.json({ ok: true, has_state: !!s, updated_at: s?.pro_engine_snapshot?.at || null });
    }

    if (request.method === "POST" && url.pathname === "/telegram") {
      let update = {};
      try { update = await request.json(); } catch (_) {}
      try {
        if (update.message) await handleMessage(env, update.message);
        return Response.json({ ok: true });
      } catch (e) {
        console.error(e);
        return Response.json({ ok: false, error: "handler_failed" }, { status: 200 });
      }
    }

    return new Response("Not found", { status: 404 });
  }
};
