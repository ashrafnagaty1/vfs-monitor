# -*- coding: utf-8 -*-
import os
import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(
                "https://visas-fr.tlscontact.com/workflow/appointment-booking/{}/{}".format(
                    BRANCH_CODE, YOUR_ID
                )
            )
            page.wait_for_timeout(5000)

            response = page.request.get(
                "{}/api/slot/active/{}".format(BASE_URL, BRANCH_CODE)
            )

            send_telegram(
                "الاسكندرية\nStatus: {}\nResponse: {}".format(
                    response.status,
                    response.text()[:300]
                )
            )

            if response.status == 200:
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
            else:
                send_telegram("مشكلة في الاتصال - status: {}".format(response.status))

        except Exception as e:
            send_telegram("خطا: {}".format(e))
        finally:
            browser.close()

# تشغيل
check_appointments()
