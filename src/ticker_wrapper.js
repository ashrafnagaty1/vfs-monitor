import terminal from "./terminal_server.js";

const VERSION = "ticker-motion-v1-2026-09-14";

export default {
  async fetch(req, env, ctx) {
    const u = new URL(req.url);
    const res = await terminal.fetch(req, env, ctx);
    if (req.method !== "GET" || u.pathname !== "/dashboard") return res;

    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("text/html")) return res;

    let html = await res.text();

    const extraStyle = `
<style>
.ticker{overflow:hidden!important;display:block!important;padding:0!important;direction:ltr}
.ticker-track{display:inline-flex;align-items:center;gap:24px;min-width:max-content;height:28px;padding:0 12px;white-space:nowrap;will-change:transform;animation:ticker-left 28s linear infinite}
.ticker:hover .ticker-track{animation-play-state:paused}
@keyframes ticker-left{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.ticker-track{animation-duration:60s}}
</style>`;

    html = html.replace("</head>", `${extraStyle}</head>`);

    const open = '<div class="ticker">';
    const start = html.indexOf(open);
    if (start !== -1) {
      const end = html.indexOf('</div><div class="footer-space">', start);
      if (end !== -1) {
        const innerStart = start + open.length;
        const inner = html.slice(innerStart, end);
        const doubled = `${inner}${inner}`;
        html = html.slice(0, start) + `${open}<div class="ticker-track">${doubled}</div>` + html.slice(end);
      }
    }

    html = html.replace("</body>", `<div style="display:none">${VERSION}</div></body>`);

    const headers = new Headers(res.headers);
    headers.set("content-type", "text/html; charset=UTF-8");
    headers.set("cache-control", "no-store, no-cache, must-revalidate");
    return new Response(html, { status: res.status, headers });
  }
};
