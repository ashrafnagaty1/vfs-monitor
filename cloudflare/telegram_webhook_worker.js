/**
 * ReFo . EGX Smart Trader — Telegram webhook edge adapter.
 *
 * Free/serverless ingress for Telegram. It deliberately does NOT touch the
 * protected TradingView UI. The existing Python engine remains the source for
 * analysis/scanning; this Worker provides the instant Telegram entry/menu and
 * live-screen launcher without an always-on Python process.
 *
 * Required Worker secret:
 *   TELEGRAM_BOT_TOKEN
 * Optional:
 *   TELEGRAM_CHAT_ID
 *   TELEGRAM_WEBHOOK_SECRET
 *   REFO_WEBAPP_URL
 */

const BRAND = "ReFo . EGX Smart Trader";
const DEFAULT_WEBAPP = "https://refogx-pro.folkhero3.workers.dev/";

const MENU = {
  keyboard: [
    ["🖥️ الشاشة اللحظية", "🤖 المساعد الذكي"],
    ["💳 اشترك الآن / ترقية"],
    ["📈 أسهم المضاربة اليومية", "📊 الصفقات"],
    ["📈 تحليل الأسهم", "♟️ التحليل المتقدم"],
    ["🎯 فرص اليوم", "🚀 الإشارات النشطة"],
    ["📋 قائمة المتابعة", "🚨 تنبيهاتي"],
    ["💼 محفظتي", "📈 تقرير الأداء"],
    ["🗺️ السوق والقطاعات", "⚙️ الإعدادات"],
  ],
  resize_keyboard: true,
  is_persistent: true,
};

function api(env, method) {
  return `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`;
}

async function send(env, chatId, text, replyMarkup) {
  const body = {
    chat_id: String(chatId),
    text,
    parse_mode: "HTML",
    disable_web_page_preview: true,
  };
  if (replyMarkup) body.reply_markup = replyMarkup;
  const r = await fetch(api(env, "sendMessage"), {
    method: "POST",
    headers: {"content-type": "application/json"},
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Telegram sendMessage failed: ${r.status}`);
}

async function showMenu(env, chatId) {
  await send(
    env,
    chatId,
    `📈 <b>${BRAND}</b>\n\nمساعد قرار وتحليل للسوق المصري.\nاختر من القائمة الرئيسية.\n\n⚠️ البيانات المتأخرة تظل معلّمة بوضوح ولا تُعامل كلحظية.`,
    MENU,
  );
}

async function showLive(env, chatId) {
  const url = env.REFO_WEBAPP_URL || DEFAULT_WEBAPP;
  await send(
    env,
    chatId,
    "🖥️ <b>ReFo EGX Terminal Pro</b>\n\nمنصة التداول والتحليل المتقدمة متاحة الآن.\nاضغط على الزر أدناه لفتح الشاشة اللحظية داخل تيليجرام.\n\n📡 TradingView للشارت، وبيانات ReFo خارج الشارت تعرض مصدرها وحالتها بوضوح.",
    {inline_keyboard: [[{text: "🚀 فتح الشاشة اللحظية", web_app: {url}}]]},
  );
  await send(env, chatId, "اختر أداة أخرى من القائمة عند الحاجة.", MENU);
}

async function setWebhook(request, env) {
  if (!env.TELEGRAM_BOT_TOKEN) return new Response("Missing TELEGRAM_BOT_TOKEN", {status: 503});
  const origin = new URL(request.url).origin;
  const payload = {
    url: `${origin}/telegram/webhook`,
    allowed_updates: ["message"],
    drop_pending_updates: false,
  };
  if (env.TELEGRAM_WEBHOOK_SECRET) payload.secret_token = env.TELEGRAM_WEBHOOK_SECRET;
  const r = await fetch(api(env, "setWebhook"), {
    method: "POST",
    headers: {"content-type": "application/json"},
    body: JSON.stringify(payload),
  });
  return new Response(await r.text(), {
    status: r.status,
    headers: {"content-type": "application/json; charset=utf-8"},
  });
}

async function webhook(request, env) {
  if (!env.TELEGRAM_BOT_TOKEN) return new Response("Missing token", {status: 503});
  if (
    env.TELEGRAM_WEBHOOK_SECRET &&
    request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.TELEGRAM_WEBHOOK_SECRET
  ) return new Response("Forbidden", {status: 403});

  const update = await request.json().catch(() => ({}));
  const message = update.message || {};
  const chatId = String((message.chat || {}).id || "");
  const text = String(message.text || "").trim();
  if (!chatId || !text) return Response.json({ok: true});

  if (env.TELEGRAM_CHAT_ID && chatId !== String(env.TELEGRAM_CHAT_ID)) {
    return Response.json({ok: true});
  }

  if (["/start", "/menu", "🏠 القائمة الرئيسية"].includes(text)) {
    await showMenu(env, chatId);
  } else if (["🖥️ الشاشة اللحظية", "📊 الشاشة اللحظية"].includes(text)) {
    await showLive(env, chatId);
  } else {
    // The edge adapter only claims functions it can actually serve. Heavy
    // Python analysis remains separate until its API is wired to this Worker.
    await send(
      env,
      chatId,
      "⏳ هذه الوظيفة مرتبطة بمحرك ReFo التحليلي ولم يتم نقلها إلى الـWebhook بعد.\nاستخدم الشاشة اللحظية أو القائمة الرئيسية حاليًا.",
      MENU,
    );
  }
  return Response.json({ok: true});
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return Response.json({
        ok: true,
        service: BRAND,
        mode: "cloudflare-telegram-webhook",
        tradingview_core: "untouched",
      });
    }
    if (request.method === "POST" && url.pathname === "/telegram/webhook") return webhook(request, env);
    if (request.method === "POST" && url.pathname === "/telegram/register") return setWebhook(request, env);
    return new Response("Not found", {status: 404});
  },
};
