# -*- coding: utf-8 -*-
import os
import requests
from playwright.sync_api import sync_playwright

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TLS_EMAIL = os.environ.get("TLS_EMAIL")
TLS_PASSWORD = os.environ.get("TLS_PASSWORD")

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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="Africa/Cairo"
        )
        page = context.new_page()

        try:
            send_telegram("جاري فتح صفحة اللوجين...")
            page.goto("https://visas-fr.tlscontact.com/login")
            page.wait_for_timeout(5000)

            # نشوف الـ inputs الموجودة
            inputs = page.query_selector_all("input")
            send_telegram("عدد الـ inputs: {}".format(len(inputs)))
            for i in inputs:
                send_telegram("input: type={} name={} placeholder={}".format(
                    i.get_attribute("type"),
                    i.get_attribute("name"),
                    i.get_attribute("placeholder")
                ))

            # نشوف الـ URL الحالي
            send_telegram("URL الحالي: {}".format(page.url))

            # نشوف عنوان الصفحة
            send_telegram("عنوان الصفحة: {}".format(page.title()))

        except Exception as e:
            send_telegram("خطا: {}".format(e))
        finally:
            browser.close()

# تشغيل
check_appointments()
