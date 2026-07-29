import re
import sys

filepath = r"c:\Workspace\healthCareContracte\scraper\sources\hdi\client.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Ekranda headless=False ve PyVirtualDisplay ile değiştirilecek blok
old_block = """        # Docker ortamında GPU kullanılamayacağı için ekliyoruz
        options.add_argument('--disable-gpu')

        import sys
        import shutil
        
        kwargs = {
            'options': options,
            'headless': True
        }
        
        if sys.platform != 'win32':
            # Docker / Linux ortamı: sistemdeki chromium'u kullan
            chromium_path = shutil.which('chromium') or shutil.which('google-chrome')
            driver_path = shutil.which('chromedriver')
            if chromium_path:
                kwargs['browser_executable_path'] = chromium_path
            if driver_path:
                kwargs['driver_executable_path'] = driver_path
        else:
            # Windows (local) ortamı
            kwargs['version_main'] = 150

        driver = uc.Chrome(**kwargs)
        try:
            logger.debug("HDI: webdriver URL'e gidiyor: %s", _PRIME_URL)"""

new_block = """        # Docker ortamında GPU kullanılamayacağı için ekliyoruz
        options.add_argument('--disable-gpu')

        import sys
        import shutil
        
        display = None
        if sys.platform != 'win32':
            try:
                from pyvirtualdisplay import Display
                display = Display(visible=0, size=(1280, 800))
                display.start()
                logger.debug("HDI: PyVirtualDisplay başlatıldı.")
            except ImportError:
                logger.warning("PyVirtualDisplay bulunamadı, Docker'da headless=False çökecektir.")
        
        kwargs = {
            'options': options,
            'headless': False
        }
        
        if sys.platform != 'win32':
            # Docker / Linux ortamı: sistemdeki chromium'u kullan
            chromium_path = shutil.which('chromium') or shutil.which('google-chrome')
            driver_path = shutil.which('chromedriver')
            if chromium_path:
                kwargs['browser_executable_path'] = chromium_path
            if driver_path:
                kwargs['driver_executable_path'] = driver_path
        else:
            # Windows (local) ortamı
            kwargs['version_main'] = 150

        driver = uc.Chrome(**kwargs)
        try:
            logger.debug("HDI: webdriver URL'e gidiyor: %s", _PRIME_URL)"""

if old_block in content:
    content = content.replace(old_block, new_block)
else:
    # Because replace_file_content deleted it, we will just insert it
    missing_pattern = r"options.add_argument\('--disable-gpu'\)\n\n            driver.get\(_PRIME_URL\)"
    new_insertion = new_block + "\n            driver.get(_PRIME_URL)"
    content = re.sub(missing_pattern, new_insertion, content)

# We also need to stop the display in the finally block
finally_block = """        finally:
            try:
                driver.quit()
            except Exception:
                pass"""

finally_new = """        finally:
            try:
                driver.quit()
            except Exception:
                pass
            if 'display' in locals() and display:
                try:
                    display.stop()
                    logger.debug("HDI: PyVirtualDisplay kapatıldı.")
                except Exception:
                    pass"""

content = content.replace(finally_block, finally_new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Patch applied successfully.")
