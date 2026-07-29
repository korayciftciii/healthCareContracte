import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests

def test_uc():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options, headless=False, version_main=150)
    try:
        driver.get('https://www.hdisigorta.com.tr/anlasmali-saglik-kurumlari')
        
        # Wait for reCAPTCHA Enterprise to load
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return typeof grecaptcha !== 'undefined' && typeof grecaptcha.enterprise !== 'undefined'")
        )
        
        print("reCAPTCHA loaded, getting token...")
        
        token = driver.execute_async_script("""
            var callback = arguments[arguments.length - 1];
            grecaptcha.enterprise.ready(function() {
                grecaptcha.enterprise.execute('6LeZ27YrAAAAAD6Xu6XAEmuFhyXUH79iLx3XDPhX', {action: 'search'})
                    .then(function(token) { callback(token); })
                    .catch(function(e) { callback('ERROR: ' + e); });
            });
        """)
        
        print(f"Token length: {len(token)}")
        print(f"Token (first 50): {token[:50]}")
        
        resp = requests.get(
            'https://client.hdisigorta.com.tr/service/bupa/districts',
            params={'provinceId': '1'},
            headers={
                'User-Agent': driver.execute_script("return navigator.userAgent;"),
                'Origin': 'https://www.hdisigorta.com.tr',
                'Referer': 'https://www.hdisigorta.com.tr/',
                'recaptcha-token': token,
            },
            timeout=20,
        )
        print('HTTP Status:', resp.status_code)
        print('Response:', resp.text[:500])
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_uc()
