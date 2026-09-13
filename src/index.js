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
  return "🤖 <b>EGX Smart Scanner</b>\n\nالبوت متصل الآن عبر Cloudflare Worker Webhook.\nاختر من القائمة بالأسفل.";
}

async function handleMessage(env, message) {
  const chatId = message?.chat?.id;
  const text = (message?.text || "").trim();
  if (!chatId || !text || !isAllowed(env, chatId)) return;

  if (text === "/start" || text === "/menu" || text === "⚙️ الإعدادات") {
    await send(env, chatId, menuText(), { reply_markup: MAIN_KEYBOARD });
    return;
  }

  const comingSoon = {
    "📊 الشاشة اللحظية": "📊 <b>الشاشة اللحظية</b>\n\nتم نقل واجهة Telegram إلى Cloudflare بنجاح. ربط لقطة السوق الحالية من المحرك جارٍ في المرحلة التالية.",
    "🎯 فرص اليوم": "🎯 <b>فرص اليوم</b>\n\nواجهة الفرص جاهزة، وسيتم ربطها بلقطة Pro Engine الحالية بعد اكتمال النشر.",
    "🔍 تحليل سهم": "🔍 <b>تحليل سهم</b>\n\nاكتب كود السهم بعد كلمة تحليل، مثال:\n<code>تحليل COMI</code>",
    "🧠 التحليل المتقدم": "🧠 <b>التحليل المتقدم</b>\n\nسيتم ربطه بمحرك التحليل الحالي بدون تشغيل فحص السوق بالكامل عند كل ضغطة.",
    "🟡 Golden Zone": "🟡 <b>Golden Zone</b>\n\nواجهة Golden Zone تعمل، وربط البيانات الديناميكية هو الخطوة التالية.",
    "🚀 الإشارات النشطة": "🚀 <b>الإشارات النشطة</b>\n\nسيتم عرض الإشارات من نفس مصدر الحالة الذي يستخدمه المحرك الحالي.",
    "🚨 تنبيهاتي": "🚨 <b>تنبيهاتي</b>\n\nربط التنبيهات الحالية سيتم بعد تأكيد تشغيل الـWebhook.",
    "💼 محفظتي": "💼 <b>محفظتي</b>\n\nربط المحفظة الحالية سيتم بعد تأكيد تشغيل الـWebhook.",
    "📈 تقرير الأداء": "📈 <b>تقرير الأداء</b>\n\nسيتم جلب التقرير من حالة المحرك الحالية.",
    "🔮 فرص بكرة": "🔮 <b>فرص بكرة</b>\n\nسيتم ربط قائمة الجلسة القادمة من Pro Engine.",
    "🗺️ أداء القطاعات": "🗺️ <b>أداء القطاعات</b>\n\nقيد الربط بمخرجات المحرك الحالية.",
    "🤖 المساعد الذكي": "🤖 <b>المساعد الذكي</b>\n\nجاهز كواجهة، وسيتم ربط منطق القرار في المرحلة التالية."
  };

  if (comingSoon[text]) {
    await send(env, chatId, comingSoon[text], { reply_markup: MAIN_KEYBOARD });
    return;
  }

  if (/^تحليل\s+/i.test(text)) {
    const symbol = text.split(/\s+/).slice(1).join(" ").toUpperCase();
    await send(env, chatId, `🔍 تم استلام طلب تحليل <b>${symbol}</b>.\n\nالتنفيذ اللحظي للمحرك الفني سيتم ربطه بعد تثبيت الـWebhook.` , { reply_markup: MAIN_KEYBOARD });
    return;
  }

  await send(env, chatId, "استخدم الأزرار من القائمة 👇", { reply_markup: MAIN_KEYBOARD });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return Response.json({ ok: true, service: "EGX Smart Scanner Cloudflare Worker" });
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
