# -*- coding: utf-8 -*-
import os
import requests

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TLS_COOKIES = os.environ.get("TLS_COOKIES")

BASE_URL = "https://visas-fr.tlscontact.com"
BRANCH_CODE = "egALY2fr"
YOUR_ID = "25781145"

def send_telegram(message):
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(TOKEN)
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("خطا تيليجرام: {}".format(e))

def check_appointments():
    try:
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://visas-fr.tlscontact.com/",
            "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cookie": TLS_COOKIES
        }

        url = "{}/api/slot/active/{}".format(BASE_URL, BRANCH_CODE)
        response = session.get(url, headers=headers, timeout=30)

        send_telegram(
            "الاسكندرية\nStatus: {}\nResponse: {}".format(
                response.status_code,
                response.text[:300]
            )
        )

        if response.status_code == 403 or response.status_code == 401:
            send_telegram("انتهت الجلسة - محتاج تجدد الكوكيز!")
            return

        data = response.json()
        if data and len(data) > 0:
            send_telegram(
                "ميعاد متاح في الاسكندرية!\n"
                "افتح الان بسرعة:\n"
                "https://visas-fr.tlscontact.com/workflow/appointment-booking/{}/{}".format(
                    BRANCH_CODE, YOUR_ID
                )
            )
        else:
            send_telegram("لا مواعيد في الاسكندرية دلوقتي")

    except Exception as e:
        send_telegram("خطا: {}".format(e))

# تشغيل
check_appointments()
