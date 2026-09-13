import os
import json
import math
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "state.json"
CAIRO = ZoneInfo("Africa/Cairo")

UNIVERSE = [
    "COMI","SWDY","EAST","ABUK","FWRY","TMGH","ORAS","ORHD","ETEL","MFPC","SKPC","JUFO",
    "ISPH","PHDC","EFIH","CIRA","ALCN","AMOC","CCAP","AUTO","ADIB","FAIT","MASR","HELI",
    "DTPP","KABO","AIDC","EPCO","ARCC","ASCM","ETRS","TALM","POUL","NEDA","ZEOT","SNFC"
]


def load_state():
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    with open(STATE_FILE,"w",encoding="utf-8") as f:
        json.dump(s,f,ensure_ascii=False,indent=2)


def send(text):
    if not TOKEN or not CHAT_ID:
        return
    r=requests.post(f"{API}/sendMessage",data={"chat_id":CHAT_ID,"text":text,"parse_mode":"HTML","disable_web_page_preview":True},timeout=20)
    r.raise_for_status()


def hist(sym, rng="6mo"):
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.CA"
    r=requests.get(url,params={"range":rng,"interval":"1d"},headers={"User-Agent":"Mozilla/5.0"},timeout=15)
    r.raise_for_status()
    res=(r.json().get("chart",{}).get("result") or [None])[0]
    if not res: raise RuntimeError("NO_DATA")
    q=res.get("indicators",{}).get("quote",[{}])[0]
    rows=[]
    n=len(q.get("close") or [])
    for i in range(n):
        row={k:((q.get(k) or [None]*n)[i]) for k in ("open","high","low","close","volume")}
        if all(row[k] is not None for k in ("open","high","low","close")):
            rows.append(row)
    if len(rows)<60: raise RuntimeError("SHORT")
    return rows


def ema(v,n):
    k=2/(n+1); out=float(v[0])
    for x in v[1:]: out=float(x)*k+out*(1-k)
    return out


def rsi(v,n=14):
    ds=[v[i]-v[i-1] for i in range(max(1,len(v)-n),len(v))]
    g=sum(max(x,0) for x in ds)/max(1,len(ds)); l=sum(max(-x,0) for x in ds)/max(1,len(ds))
    return 100 if l==0 else 100-100/(1+g/l)


def atr(rows,n=14):
    tr=[]
    for i in range(1,len(rows)):
        h=float(rows[i]["high"]); l=float(rows[i]["low"]); pc=float(rows[i-1]["close"])
        tr.append(max(h-l,abs(h-pc),abs(l-pc)))
    return sum(tr[-n:])/max(1,min(n,len(tr)))


def adx(rows,n=14):
    if len(rows)<n+2:return 0.0
    plus=[]; minus=[]; trs=[]
    for i in range(1,len(rows)):
        up=float(rows[i]["high"])-float(rows[i-1]["high"])
        dn=float(rows[i-1]["low"])-float(rows[i]["low"])
        plus.append(up if up>dn and up>0 else 0)
        minus.append(dn if dn>up and dn>0 else 0)
        h=float(rows[i]["high"]); l=float(rows[i]["low"]); pc=float(rows[i-1]["close"])
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    trn=sum(trs[-n:]); p=100*sum(plus[-n:])/trn if trn else 0; m=100*sum(minus[-n:])/trn if trn else 0
    return 100*abs(p-m)/(p+m) if p+m else 0


def mfi(rows,n=14):
    if len(rows)<n+1:return 50.0
    pos=neg=0.0
    prev=None
    for x in rows[-n-1:]:
        tp=(float(x["high"])+float(x["low"])+float(x["close"]))/3
        flow=tp*float(x.get("volume") or 0)
        if prev is not None:
            if tp>=prev: pos+=flow
            else: neg+=flow
        prev=tp
    if neg==0:return 100.0
    return 100-100/(1+pos/neg)


def analyze(sym):
    rows=hist(sym)
    c=[float(x["close"]) for x in rows]; h=[float(x["high"]) for x in rows]; l=[float(x["low"]) for x in rows]
    v=[float(x.get("volume") or 0) for x in rows]
    p=c[-1]; e20=ema(c[-100:],20); e50=ema(c[-120:],50); e200=ema(c,min(200,len(c)))
    rv=rsi(c); av=atr(rows); ax=adx(rows); mf=mfi(rows)
    res20=max(h[-20:-1]); sup20=min(l[-20:]); res50=max(h[-50:-1]); sup50=min(l[-50:])
    avgvol=sum(v[-21:-1])/max(1,len(v[-21:-1])); vr=v[-1]/avgvol if avgvol else 1
    mom5=(p/c[-6]-1)*100
    mom20=(p/c[-21]-1)*100
    score=0; why=[]
    if p>e20: score+=10; why.append("فوق EMA20")
    if e20>e50: score+=14; why.append("EMA20>EMA50")
    if e50>e200: score+=8; why.append("اتجاه طويل داعم")
    if 48<=rv<=68: score+=12; why.append("RSI صحي")
    if ax>=22: score+=10; why.append("ADX يؤكد الاتجاه")
    if 45<=mf<=80: score+=8; why.append("تدفق سيولة إيجابي")
    if vr>=1.4: score+=16; why.append("حجم قوي")
    elif vr>=1.1: score+=7
    dist=(res20-p)/p*100
    if p>=res20*0.997: score+=14; why.append("اختراق مقاومة")
    elif 0<=dist<=2.5: score+=8; why.append("قريب من التفعيل")
    if mom5>0: score+=4
    if mom20>0: score+=4
    if rv>78: score-=8
    score=max(0,min(100,score))
    risk=max(av*1.2,p*0.02)
    stop=max(sup20*0.995,p-risk)
    unit=max(p-stop,av,p*0.012)
    t1=p+unit; t2=p+2*unit; t3=p+3*unit
    golden_low=max(sup20,e20-av*0.6); golden_high=e20+av*0.25
    golden=golden_low<=p<=golden_high and e20>=e50*0.99 and 35<=rv<=60
    breakout=p>=res20*0.997 and vr>=1.1
    return {"symbol":sym,"price":p,"score":score,"rsi":rv,"adx":ax,"mfi":mf,"vr":vr,"mom5":mom5,"mom20":mom20,
            "res20":res20,"res50":res50,"sup20":sup20,"sup50":sup50,"stop":stop,"t1":t1,"t2":t2,"t3":t3,
            "golden":golden,"golden_low":golden_low,"golden_high":golden_high,"breakout":breakout,"why":why[:5]}


def scan():
    out=[]
    for s in UNIVERSE:
        try: out.append(analyze(s))
        except Exception: pass
    return sorted(out,key=lambda x:(x["score"],x["vr"],x["mom5"]),reverse=True)


def once_key(state,key):
    sent=state.setdefault("pro_engine_sent",{})
    if key in sent:return False
    sent[key]=datetime.now(CAIRO).isoformat(); return True


def event_alerts(state,items):
    now=datetime.now(CAIRO); d=now.date().isoformat(); changed=False
    if now.weekday()>=5:return False
    mins=now.hour*60+now.minute
    if not (600<=mins<=870): return False
    for a in items[:18]:
        if a["breakout"] and a["score"]>=70:
            k=f"breakout:{a['symbol']}:{d}"
            if once_key(state,k):
                send(f"🚀 <b>تفعيل اختراق فني</b>\n\n<b>{a['symbol']}</b>\nالسعر المرجعي {a['price']:.2f}\nScore <b>{a['score']}/100</b>\nVolume {a['vr']:.2f}x | ADX {a['adx']:.1f} | MFI {a['mfi']:.1f}\nT1 {a['t1']:.2f} | T2 {a['t2']:.2f} | T3 {a['t3']:.2f}\n🛑 Stop {a['stop']:.2f}\n\n🔎 {' • '.join(a['why'])}\n\n⚠️ بيانات مرجعية وقد تكون متأخرة.")
                changed=True
        if a["golden"] and a["score"]>=55:
            k=f"golden:{a['symbol']}:{d}"
            if once_key(state,k):
                send(f"🟡 <b>Golden Zone — ارتداد محتمل</b>\n\n<b>{a['symbol']}</b>\nالسعر {a['price']:.2f}\nالمنطقة {a['golden_low']:.2f} — {a['golden_high']:.2f}\nRSI {a['rsi']:.1f} | ADX {a['adx']:.1f} | MFI {a['mfi']:.1f}\nScore {a['score']}/100\nمستوى التفعيل التقريبي {a['res20']:.2f}\n\n⚠️ يحتاج تأكيد سعري/حجمي.")
                changed=True
    return changed


def scheduled_reports(state,items):
    now=datetime.now(CAIRO); d=now.date().isoformat(); mins=now.hour*60+now.minute; changed=False
    if now.weekday()>=5:return False
    if 570<=mins<600 and once_key(state,f"premarket:{d}"):
        top=items[:6]
        lines=["🌅 <b>خريطة ما قبل الجلسة</b>",""]
        for i,a in enumerate(top,1):
            lines.append(f"{i}) <b>{a['symbol']}</b> Score {a['score']} | Trigger {a['res20']:.2f} | Stop {a['stop']:.2f}")
        lines.append("\n⚠️ مرشحون للمراقبة فقط.")
        send("\n".join(lines)); changed=True
    if 865<=mins<=900 and once_key(state,f"close:{d}"):
        top=items[:8]; avg=sum(x["mom5"] for x in items)/max(1,len(items)); green=sum(1 for x in items if x["mom5"]>0)
        lines=["📋 <b>تقرير إغلاق الجلسة</b>",f"زخم السوق التقريبي: {avg:+.2f}% | صاعد {green}/{len(items)}",""]
        for a in top:
            lines.append(f"• <b>{a['symbol']}</b> {a['price']:.2f} | Score {a['score']} | Vol {a['vr']:.1f}x | RSI {a['rsi']:.0f}")
        lines.append("\n🔮 أعلى الدرجات تنتقل لقائمة مراقبة الجلسة القادمة.")
        send("\n".join(lines)); changed=True
    return changed


def health(state,items):
    now=datetime.now(CAIRO); d=now.date().isoformat()
    if len(items)>=10:return False
    k=f"datahealth:{d}"
    if once_key(state,k):
        send(f"⚠️ <b>تنبيه جودة البيانات</b>\nتم تحليل {len(items)} سهم فقط من قائمة السوق. مصدر البيانات الحالي محدود/متأخر؛ تم منع الاعتماد على المسح كإشارة لحظية.")
        return True
    return False


def main():
    state=load_state(); changed=False
    items=scan()
    changed=health(state,items) or changed
    changed=event_alerts(state,items) or changed
    changed=scheduled_reports(state,items) or changed
    state["pro_engine_snapshot"]={"at":datetime.now(CAIRO).isoformat(),"count":len(items),"top":[{"symbol":x["symbol"],"score":x["score"],"price":x["price"]} for x in items[:10]]}
    changed=True
    if changed: save_state(state)


if __name__=="__main__":
    main()
