import json
import os


def _keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


LIVE_SCREEN_URL = os.environ.get("REFO_WEBAPP_URL", "https://refogx-pro.folkhero3.workers.dev/")

MAIN_MENU = _keyboard([
    ["📊 الشاشة اللحظية", "🤖 المساعد الذكي"],
    ["💳 اشتراك / ترقية"],
    ["📈 أسهم المضاربة اليومية", "📊 الصفقات"],
    ["📈 تحليل الأسهم", "🧠 التحليل المتقدم"],
    ["🎯 فرص اليوم", "🚀 الإشارات النشطة"],
    ["📋 قائمة المتابعة", "🚨 تنبيهاتي"],
    ["💼 محفظتي", "📈 تقرير الأداء"],
    ["🗺️ السوق والقطاعات", "⚙️ الإعدادات"],
])
ADVANCED_MENU = _keyboard([
    ["📐 الفني المتقدم", "🧭 Smart Money"],
    ["⏳ التوقع الزمني", "📏 تحليل جان"],
    ["🦋 الهارمونيك", "🌊 موجات إليوت"],
    ["📑 التقارير المالية", "💰 القيمة العادلة"],
    ["🏠 القائمة الرئيسية"],
])
MARKET_MENU = _keyboard([["🗺️ أداء القطاعات", "📊 الشاشة اللحظية"],["🎯 فرص اليوم", "📈 أسهم المضاربة اليومية"],["🏠 القائمة الرئيسية"]])
STOCK_ACTION_MENU = _keyboard([["🔄 تحديث التحليل", "📐 تحليل متقدم للسهم"],["👁️ متابعة الخطة", "🗑️ إلغاء المتابعة"],["📋 قائمة المتابعة", "📊 الشاشة اللحظية"],["🏠 القائمة الرئيسية"]])
PORTFOLIO_MENU = _keyboard([["🚀 الإشارات النشطة", "📈 تقرير الأداء"],["🔄 تحديث المحفظة", "🏠 القائمة الرئيسية"]])
SIGNALS_MENU = _keyboard([["💼 محفظتي", "📈 تقرير الأداء"],["🎯 فرص اليوم", "🏠 القائمة الرئيسية"]])


def _send_keyboard(base,text,chat_id,keyboard):
    if not base.TOKEN:return
    payload={"chat_id":str(chat_id or base.CHAT_ID),"text":text,"parse_mode":"HTML","disable_web_page_preview":True,"reply_markup":json.dumps(keyboard,ensure_ascii=False)}
    r=base.requests.post(f"{base.API}/sendMessage",data=payload,timeout=15);r.raise_for_status()


def _send_live_screen(base,chat_id):
    if not base.TOKEN:return
    markup={"inline_keyboard":[[{"text":"🚀 فتح الشاشة اللحظية","web_app":{"url":LIVE_SCREEN_URL}}]]}
    payload={"chat_id":str(chat_id or base.CHAT_ID),"text":"🖥️ <b>ReFo EGX Terminal Pro</b>\n\nمنصة التداول والتحليل المتقدمة متاحة الآن.\nاضغط على الزر أدناه لفتح الشاشة اللحظية داخل تيليجرام.\n\n📡 بيانات ReFo تعرض مصدرها وحالتها بوضوح؛ TradingView يعمل كمصدر مستقل للشارت.","parse_mode":"HTML","disable_web_page_preview":True,"reply_markup":json.dumps(markup,ensure_ascii=False)}
    r=base.requests.post(f"{base.API}/sendMessage",data=payload,timeout=15);r.raise_for_status()
    _send_keyboard(base,"اختر أداة أخرى من القائمة عند الحاجة.",chat_id,MAIN_MENU)


def _disabled(base,chat_id,title,reason):
    _send_keyboard(base,f"🚧 <b>{title}</b>\n\nالميزة غير مفعلة حاليًا لأن {reason}.\nلن يعرض ReFo نتيجة تقديرية على أنها تحليل حقيقي قبل توفر البيانات/الخوارزمية الموثوقة.",chat_id,ADVANCED_MENU)


def _runtime_state(base):
    try:return base.load_json(base.STATE_FILE,{}) or {}
    except Exception:return {}

def _as_list(v):return v if isinstance(v,list) else list(v.values()) if isinstance(v,dict) else []
def _num(v,d=2):
    try:return f"{float(v):.{d}f}"
    except Exception:return "-"
def _quote_mode_label(m):return "🟢 LIVE مؤكد" if m=="LIVE" else "🟡 DELAYED / EVALUATION"
def _source_label(base,a):
    if a.get("quote_live"):return "🟢 LIVE — مصدر السعر أكد اللحظية"
    try:s=base.load_json(base.STATE_FILE,{}).get("pro_engine_snapshot") or {};src=s.get("quote_source") or "OHLCV / آخر إغلاق متاح"
    except Exception:src="OHLCV / آخر إغلاق متاح"
    return f"🟡 DELAYED / EVALUATION — {src}"
def _rr(e,s,t):
    risk=max(0,float(e)-float(s));return max(0,float(t)-float(e))/risk if risk else 0

def _build_active_signals_text(runtime):
    lc=runtime.get("trade_lifecycle") or {};plans=_as_list(lc.get("plans"));mode=lc.get("quote_mode") or "DELAYED_EVALUATION"
    lines=["🚀 <b>الإشارات والخطط النشطة</b>",f"📡 {_quote_mode_label(mode)}",""]
    if not plans:return "\n".join(lines+["لا توجد خطط نشطة محفوظة حاليًا."])
    rank={"T3":0,"T2":1,"T1":2,"ENTRY":3,"WATCH":4}
    for p in sorted(plans,key=lambda x:(rank.get(str(x.get("lifecycle_status") or x.get("status") or "WATCH"),9),-float(x.get("score") or 0)))[:12]:
        st=str(p.get("lifecycle_status") or p.get("status") or "WATCH");lines += [f"• <b>{p.get('symbol','-')}</b> · {st} · Score {_num(p.get('score'),0)}",f"  Trigger {_num(p.get('trigger'))} · Stop {_num(p.get('dynamic_stop') or p.get('initial_stop'))}",f"  T1 {_num(p.get('target1'))} · T2 {_num(p.get('target2'))} · T3 {_num(p.get('target3'))} · ID <code>{p.get('signal_id','-')}</code>"]
    if mode!="LIVE":lines += ["","⚠️ WATCH لا يتحول إلى ENTRY من مصدر delayed/evaluation."]
    return "\n".join(lines)

def _build_portfolio_text(runtime):
    p=runtime.get("signal_portfolio") or {};mode=p.get("quote_mode") or (runtime.get("trade_lifecycle") or {}).get("quote_mode") or "DELAYED_EVALUATION";op=_as_list(p.get("open_positions"));cl=_as_list(p.get("closed_trades"))
    lines=["💼 <b>محفظة إشارات ReFo</b>",f"📡 {_quote_mode_label(mode)}",f"🟢 مفتوحة: <b>{len(op)}</b> · 📁 مغلقة: <b>{len(cl)}</b>",""]
    for x in op[:10]:lines += [f"📌 <b>{x.get('symbol','-')}</b> · {x.get('lifecycle_status') or x.get('stage') or 'ENTRY'}",f"  Entry {_num(x.get('entry_price'))} · Last {_num(x.get('last_price'))} · Stop {_num(x.get('dynamic_stop') or x.get('initial_stop'))} · P/L {_num(x.get('unrealized_r'))}R"]
    if not op:lines.append("لا توجد مراكز إشارات مفتوحة حاليًا.")
    lines += ["","⚠️ هذه محفظة تتبع إشارات وليست كشف حساب وساطة."]
    return "\n".join(lines)
def _build_performance_text(runtime):
    p=runtime.get("signal_portfolio") or {};x=p.get("performance") or {}
    return f"📈 <b>تقرير أداء إشارات ReFo</b>\n\nالمغلقة: <b>{int(x.get('closed_trades') or 0)}</b> · المفتوحة: <b>{int(x.get('open_positions') or 0)}</b>\n✅ فوز {int(x.get('wins') or 0)} · ❌ خسارة {int(x.get('losses') or 0)}\n🎯 Win rate: <b>{_num(x.get('win_rate_pct'),1)}%</b>\n⚖️ Total R: <b>{_num(x.get('total_r'))}R</b> · Avg R: <b>{_num(x.get('avg_r'))}R</b>\n🏆 Best {_num(x.get('best_r'))}R · Worst {_num(x.get('worst_r'))}R\n\nℹ️ الأداء لا يحتسب WATCH الناتج من delayed/evaluation كصفقة مؤكدة."

def _render_stock_card(base,chat_id,state,symbol,advanced=False):
    sym=base.normalize_symbol(symbol)
    if not sym:_send_keyboard(base,"⚠️ اكتب رمز سهم صحيح مثل <b>COMI</b>.",chat_id,MAIN_MENU);return
    try:
        from pro_engine import analyze;a=analyze(sym)
    except Exception:_send_keyboard(base,f"⚠️ تعذر تحليل <b>{sym}</b> حاليًا.",chat_id,MAIN_MENU);return
    state["last_analysis_symbol"]=sym;price=float(a.get("price") or 0);stop=float(a.get("stop") or 0);tr=float(a.get("res20") or 0);t1=float(a.get("t1") or 0);t2=float(a.get("t2") or 0);t3=float(a.get("t3") or 0);live=bool(a.get("quote_live"));status="ENTRY" if live and tr and price>=tr*.997 else "WATCH"
    lines=[f"📌 <b>ReFo — {sym}</b>",f"{'🟢' if status=='ENTRY' else '🟡'} الحالة: <b>{status}</b>",f"💵 السعر المرجعي <b>{price:.2f}</b> · 🎯 Trigger <b>{tr:.2f}</b>",f"🛑 Stop <b>{stop:.2f}</b>",f"🏁 T1 {t1:.2f} · T2 {t2:.2f} · T3 {t3:.2f}",f"⚖️ RR { _rr(price,stop,t1):.2f}R / {_rr(price,stop,t2):.2f}R / {_rr(price,stop,t3):.2f}R",f"⭐ Score <b>{a.get('score',0)}/100</b> · Confidence {a.get('confidence','-')}",f"💧 Liquidity {float(a.get('liquidity_score') or 0):.0f}/100 · Volume {float(a.get('vr') or 0):.2f}x",f"📐 RSI {float(a.get('rsi') or 0):.1f} · ADX {float(a.get('adx') or 0):.1f} · MFI {float(a.get('mfi') or 0):.1f}",f"📊 S1 {float(a.get('sup20') or 0):.2f} · R1 {tr:.2f}"]
    if advanced:lines += [f"📈 EMA20 {float(a.get('ema20') or 0):.2f} · EMA50 {float(a.get('ema50') or 0):.2f} · EMA200 {float(a.get('ema200') or 0):.2f}",f"🟡 Golden Zone {float(a.get('golden_low') or 0):.2f} — {float(a.get('golden_high') or 0):.2f}",f"⚡ Momentum 5D {float(a.get('mom5') or 0):+.2f}% · 20D {float(a.get('mom20') or 0):+.2f}%",f"🌡️ Volatility {float(a.get('volatility_pct') or 0):.2f}%"]
    why=a.get("why") or []
    if why:lines += ["","🔎 <b>أسباب القراءة</b>"]+[f"• {v}" for v in why[:6]]
    lines += ["",f"📡 {_source_label(base,a)}","⚠️ لا يتحول WATCH إلى ENTRY إلا من مصدر Live مؤكد."]
    _send_keyboard(base,"\n".join(lines),chat_id,STOCK_ACTION_MENU)

def apply(base):
    original=base.handle;base.MAIN_MENU=MAIN_MENU
    def h(chat_id,text,state):
        text=(text or "").strip()
        if text in ("/start","/menu","🏠 القائمة الرئيسية"):
            state.pop("awaiting",None);_send_keyboard(base,"📈 <b>ReFo . EGX Smart Trader</b>\n\nمساعد قرار وتحليل للسوق المصري.\nاختر من القائمة الرئيسية.\n\n⚠️ أي بيانات delayed/evaluation تظل معلّمة بوضوح ولا تُعامل كلحظية.",chat_id,MAIN_MENU);return True
        if text=="📊 الشاشة اللحظية":state.pop("awaiting",None);_send_live_screen(base,chat_id);return True
        if text in ("📈 تحليل الأسهم","🔍 تحليل سهم"):
            state["awaiting"]="analysis";_send_keyboard(base,"📈 اكتب رمز السهم، مثال <b>COMI</b>.",chat_id,MAIN_MENU);return True
        if text=="🧠 التحليل المتقدم":state.pop("awaiting",None);_send_keyboard(base,"🧠 <b>التحليل المتقدم</b>\n\nاختر الأداة. كل وحدة تعرض طبيعة بياناتها وحدودها.",chat_id,ADVANCED_MENU);return True
        if text=="📐 الفني المتقدم":state["awaiting"]="advanced";_send_keyboard(base,"📐 اكتب رمز السهم للتحليل الفني المتقدم.",chat_id,ADVANCED_MENU);return True
        if state.get("awaiting") in ("analysis","advanced"):
            a=state.pop("awaiting");_render_stock_card(base,chat_id,state,text,a=="advanced");return True
        if text=="🔄 تحديث التحليل":
            sym=state.get("last_analysis_symbol");_render_stock_card(base,chat_id,state,sym,False) if sym else _send_keyboard(base,"🔍 حلّل سهمًا أولًا.",chat_id,MAIN_MENU);return True
        if text=="📐 تحليل متقدم للسهم":
            sym=state.get("last_analysis_symbol");_render_stock_card(base,chat_id,state,sym,True) if sym else _send_keyboard(base,"📐 حلّل سهمًا أولًا.",chat_id,ADVANCED_MENU);return True
        if text=="🚀 الإشارات النشطة" or text=="📊 الصفقات":_send_keyboard(base,_build_active_signals_text(_runtime_state(base)),chat_id,SIGNALS_MENU);return True
        if text in ("💼 محفظتي","🔄 تحديث المحفظة"):_send_keyboard(base,_build_portfolio_text(_runtime_state(base)),chat_id,PORTFOLIO_MENU);return True
        if text=="📈 تقرير الأداء":_send_keyboard(base,_build_performance_text(_runtime_state(base)),chat_id,PORTFOLIO_MENU);return True
        if text=="📈 أسهم المضاربة اليومية":return original(chat_id,"🎯 فرص اليوم",state)
        if text=="💳 اشتراك / ترقية":_send_keyboard(base,"💳 <b>الاشتراك / الترقية</b>\n\nلا توجد بوابة دفع مفعلة داخل ReFo حاليًا. لن يتم طلب أي دفع قبل إضافة قناة دفع رسمية وآمنة.",chat_id,MAIN_MENU);return True
        if text=="🗺️ السوق والقطاعات":state.pop("awaiting",None);_send_keyboard(base,"🗺️ <b>السوق والقطاعات</b>\n\nالـBreadth والسيولة الحالية عند عرضها من ReFo هي عينة من universe وليست إحصاء EGX رسميًا إلا بعد ربط Feed شامل.",chat_id,MARKET_MENU);return True
        return original(chat_id,text,state)
    base.handle=h;return base

def self_test():
    assert MAIN_MENU["keyboard"][0]==["📊 الشاشة اللحظية","🤖 المساعد الذكي"]
    assert LIVE_SCREEN_URL.startswith("https://")
    print("bot experience V11 self-test: PASS")

if __name__=="__main__":self_test()
