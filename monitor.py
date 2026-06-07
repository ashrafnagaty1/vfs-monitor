import os
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TLS_EMAIL = os.environ.get("TLS_EMAIL")
TLS_PASSWORD = os.environ.get("TLS_PASSWORD")

BASE_URL = "https://visas-fr.tlscontact.com"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def login():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    payload = {
        "email": TLS_EMAIL,
        "password": TLS_PASSWORD
    }
    session.post(f"{BASE_URL}/api/auth/login", json=payload, headers=headers)
    return session

def check_appointments(session):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    branches = {
        "الغردقة": "egHRG2fr",
    }
    for branch_name, branch_code in branches.items():
        try:
            url = f"{BASE_URL}/api/slot/active/{branch_code}"
            response = session.get(url, headers=headers, timeout=30)
            data = response.json()
            if data and len(data) > 0:
                send_telegram(f"🎉 ميعاد فرنسا متاح في فرع {branch_name}!\nافتح الموقع الآن: https://visas-fr.tlscontact.com/workflow/appointment-booking/egHRG2fr/26962221?date=2026-09-01")
            else:
                print(f"لا توجد مواعيد في {branch_name}")
        except Exception as e:
            print(f"خطأ في {branch_name}: {e}")

session = login()
send_telegram("✅ البوت بدأ يراقب مواعيد TLS فرنسا - الغردقة!")
check_appointments(session)
