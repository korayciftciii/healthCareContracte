import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from scraper.sources.hdi.client import HdiRecaptchaTokenManager
import requests

mgr = HdiRecaptchaTokenManager()
token = mgr.get_token()
print("Token (ilk 50):", token[:50])
print("Token uzunlugu:", len(token))

resp = requests.get(
    "https://client.hdisigorta.com.tr/service/bupa/districts",
    params={"provinceId": "1"},
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        "Origin": "https://www.hdisigorta.com.tr",
        "Referer": "https://www.hdisigorta.com.tr/",
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "recaptcha-token": token,
    },
    timeout=20,
)
print("HTTP Status:", resp.status_code)
print("Response:", resp.text[:500])
