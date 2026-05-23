import os
import requests
import time

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

def check_appointments():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = "https://visa.vfsglobal.com/egy/en/fra/login"
        response = requests.get(url, headers=headers, timeout=30)
        
        if "No appointments" not in response.text and "appointment" in response.text.lower():
            send_telegram("🎉 يوجد موعد متاح! افتح الموقع الآن: https://visa.vfsglobal.com/egy/en/fra/login")
        else:
            print("لا توجد مواعيد متاحة")
            
    except Exception as e:
        print(f"خطأ: {e}")

check_appointments()
