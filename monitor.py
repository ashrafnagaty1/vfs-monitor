import os
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TLS_EMAIL = os.environ.get("TLS_EMAIL")
TLS_PASSWORD = os.environ.get("TLS_PASSWORD")

BASE_URL = "https://visas-fr.tlscontact.com"
BRANCH_CODE = "egALY2fr"
YOUR_ID = "25781145"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print(f"خطأ تيليجرام: {e}")

def login():
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://visas-fr.tlscontact.com",
            "Referer": "https://visas-fr.tlscontact.com/",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive"
        }
        res = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TLS_EMAIL, "password": TLS_PASSWORD},
            headers=headers,
            timeout=30
        )
        if res.status_code == 200:
            send_telegram("✅ تم تسجيل الدخول بنجاح")
            return session
        else:
            send_telegram(f"❌ فشل اللوجين - status: {res.status_code}\n{res.text[:200]}")
            return None
    except Exception as e:
        send_telegram(f"❌ خطأ في اللوجين: {e}")
        return None

def check_appointments(session):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Referer": "https://visas-fr.tlscontact.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        url = f"{BASE_URL}/api/slot/active/{BRANCH_CODE}"
        response = session.get(url, headers=headers, timeout=30)

        send_telegram(
            f"🔍 الإسكندرية\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text[:200]}"
        )

        if response.status_code == 401:
            send_telegram("⚠️ انتهت الجلسة!")
            return

        data = response.json()
        if data and len(data) > 0:
            send_telegram(
                f"🎉 ميعاد متاح في الإسكندرية!\n"
                f"افتح الآن بسرعة 👇\n"
                f"https://visas-fr.tlscontact.com/workflow/appointment-booking/{BRANCH_CODE}/{YOUR_ID}"
            )
        else:
            send_telegram("😔 لا مواعيد ف
