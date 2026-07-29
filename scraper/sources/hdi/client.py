from __future__ import annotations

import logging
import time
import random
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.exceptions import ScraperHTTPError, ScraperParseError

logger = logging.getLogger(__name__)

_BASE_URL = "https://client.hdisigorta.com.tr/service/bupa"
_REFERER_URL = "https://www.hdisigorta.com.tr/"
_PRIME_URL = "https://www.hdisigorta.com.tr/anlasmali-saglik-kurumlari"

# reCAPTCHA Enterprise site key (HDI'ya ait)
_RECAPTCHA_SITE_KEY = "6LeZ27YrAAAAAD6Xu6XAEmuFhyXUH79iLx3XDPhX"
# Token ~120s geçerli; 90s'de yeniliyoruz
_TOKEN_TTL_SECONDS = 90


class HdiRecaptchaTokenManager:
    """Playwright ile reCAPTCHA Enterprise token üretir ve cache'ler.

    HDI'nın sitesi Google reCAPTCHA Enterprise v3 kullanır. Token JavaScript
    ortamında üretilmek zorunda (grecaptcha.enterprise.execute()), dolayısıyla
    headless Chromium gerekir.

    Token ~120s geçerlidir; biz 90s'de önceden yenileriz. İş parçacığı güvenli
    (lock ile korunur) — aynı anda iki thread token isterse sadece biri üretir,
    diğeri bekler.
    """

    def __init__(self):
        self._token: str | None = None
        self._token_fetched_at: float = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        """Geçerli bir reCAPTCHA Enterprise token döner; gerekirse yeniler."""
        with self._lock:
            age = time.monotonic() - self._token_fetched_at
            if self._token and age < _TOKEN_TTL_SECONDS:
                return self._token
            self._token = self._fetch_token()
            self._token_fetched_at = time.monotonic()
            return self._token

    def invalidate(self) -> None:
        """Token'ı geçersiz kılar — bir sonraki get_token() yeniden üretir."""
        with self._lock:
            self._token = None
            self._token_fetched_at = 0.0

    @staticmethod
    def _fetch_token() -> str:
        """undetected-chromedriver ile HDI sayfasını açar ve
        grecaptcha.enterprise.execute() çağrısıyla gerçek token üretir.
        
        Playwright reCAPTCHA v3 tarafından bot olarak tespit edildiği için (low score 0.0),
        bypass için undetected-chromedriver kullanılır.
        """
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.support.ui import WebDriverWait
        except ImportError as exc:
            raise ScraperHTTPError(
                "undetected-chromedriver kurulu değil. "
                "'pip install undetected-chromedriver selenium' komutunu çalıştırın."
            ) from exc

        logger.info("HDI: reCAPTCHA Enterprise token üretiliyor (undetected-chromedriver)...")

        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
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
            chromium_path = shutil.which('chromium') or shutil.which('google-chrome')
            driver_path = shutil.which('chromedriver')
            if chromium_path:
                kwargs['browser_executable_path'] = chromium_path
            if driver_path:
                kwargs['driver_executable_path'] = driver_path
        else:
            kwargs['version_main'] = 150

        driver = uc.Chrome(**kwargs)
        
        try:
            logger.debug("HDI: webdriver URL'e gidiyor: %s", _PRIME_URL)
            driver.get(_PRIME_URL)

            logger.debug("HDI: grecaptcha.enterprise nesnesi bekleniyor...")
            WebDriverWait(driver, 25).until(
                lambda d: d.execute_script(
                    "return typeof window.grecaptcha !== 'undefined' "
                    "&& typeof window.grecaptcha.enterprise !== 'undefined'"
                )
            )
            logger.debug("HDI: grecaptcha.enterprise yüklendi. İnsan davranışı simülasyonu başlatılıyor...")

            from selenium.webdriver.common.action_chains import ActionChains
            import random
            import time

            try:
                for _ in range(3):
                    scroll_y = random.randint(200, 700)
                    driver.execute_script(f"window.scrollBy(0, {scroll_y});")
                    time.sleep(random.uniform(0.5, 1.5))
                    action = ActionChains(driver)
                    action.move_by_offset(random.randint(10, 100), random.randint(10, 100)).perform()
                    time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                logger.warning("HDI: İnsan davranışı simülasyonunda hata: %s", e)

            logger.debug("HDI: reCAPTCHA execute() çağrılıyor...")
            token = driver.execute_async_script(f"""
                var callback = arguments[arguments.length - 1];
                var timer = setTimeout(function() {{
                    callback('TIMEOUT');
                }}, 25000);
                
                grecaptcha.enterprise.ready(function() {{
                    grecaptcha.enterprise.execute(
                        '{_RECAPTCHA_SITE_KEY}', 
                        {{action: 'search'}}
                    ).then(function(t) {{
                        clearTimeout(timer);
                        callback(t);
                    }}).catch(function(e) {{
                        clearTimeout(timer);
                        callback('ERROR: ' + e);
                    }});
                }});
            """)

            if not token or not isinstance(token, str) or token.startswith('ERROR') or token == 'TIMEOUT':
                logger.error("HDI: Token üretimi başarısız oldu. Dönen yanıt: %s", token)
                raise ScraperHTTPError(
                    f"reCAPTCHA Enterprise geçersiz token döndürdü veya hata oluştu: {token!r}"
                )

            logger.info(
                "HDI: reCAPTCHA Enterprise token başarıyla üretildi (uzunluk=%d, ön=%s...)",
                len(token), token[:20],
            )
            return token
        finally:
            try:
                driver.quit()
            except Exception:
                pass
            if 'display' in locals() and display:
                try:
                    display.stop()
                    logger.debug("HDI: PyVirtualDisplay kapatıldı.")
                except Exception:
                    pass


class HdiClient:
    """HDI Sigorta anlaşmalı kurum API istemcisi.

    İki endpoint kullanılır:
      - GET  /service/bupa/districts?provinceId={plate_code}
             → İl bazında ilçe listesini döner. provinceId = plaka kodu (1..81, başında 0 YOK).
      - POST /service/bupa/contracted-health-institutions
             → payload: {"productId": "373", "provinceId": "16", "districtId": "202", "institutionTypeId": "1"}

    reCAPTCHA:
        Her istekte geçerli bir reCAPTCHA Enterprise token `recaptcha-token` header'ına
        eklenir. Token HdiRecaptchaTokenManager tarafından Playwright headless Chromium
        ile üretilir ve 90s cache'lenir. Token süresi dolduğunda (veya 400 MALFORMED
        hatası alındığında) otomatik yenilenir.
    """

    DISTRICTS_URL = f"{_BASE_URL}/districts"
    INSTITUTIONS_URL = f"{_BASE_URL}/contracted-health-institutions"

    BLOCK_MAX_RETRIES = 2
    BLOCK_RETRY_BASE_DELAY = 6.0

    def __init__(
        self,
        session: requests.Session | None = None,
        token_manager: HdiRecaptchaTokenManager | None = None,
    ):
        self.session = session or self._build_session()
        self.token_manager = token_manager or HdiRecaptchaTokenManager()

    # ------------------------------------------------------------------ #
    # Session yönetimi                                                    #
    # ------------------------------------------------------------------ #

    def _build_session(self) -> requests.Session:
        """Chrome 150 tarayıcısını taklit eden session oluşturur."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers = requests.structures.CaseInsensitiveDict({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Origin": "https://www.hdisigorta.com.tr",
            "Referer": _REFERER_URL,
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "priority": "u=1, i",
        })
        return session

    def _get_headers_with_token(self) -> dict:
        """Güncel reCAPTCHA token'ını içeren ek header dict'i döner."""
        token = self.token_manager.get_token()
        return {"recaptcha-token": token}

    def _reset_session(self) -> None:
        """Anti-bot bloğu şüphesi sonrası session'ı tazeler."""
        logger.info("HDI session sıfırlanıyor...")
        self.session.close()
        self.session = self._build_session()

    @staticmethod
    def _is_recaptcha_error(response: requests.Response) -> bool:
        """Token MALFORMED/INVALID hatası — token yenilenmeli."""
        if response.status_code == 400:
            try:
                body = response.json()
                err = (body.get("error") or "").lower()
                return "recaptcha" in err or "token" in err
            except Exception:
                pass
        return False

    @staticmethod
    def _looks_blocked(response: requests.Response) -> bool:
        """JSON beklenirken HTML/boş içerik → bot bloğu şüphesi."""
        if response.status_code in (403, 429):
            return True
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type and response.status_code == 200:
            return bool(response.text.strip())
        return False

    # ------------------------------------------------------------------ #
    # Retry mekanizması                                                   #
    # ------------------------------------------------------------------ #

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        context_label: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> requests.Response:
        """GET veya POST atar; reCAPTCHA hatası, blok veya genel HTTP
        hatalarında backoff + token yenileme + session reset ile yeniden dener."""
        last_response: requests.Response | None = None

        for attempt in range(self.BLOCK_MAX_RETRIES + 1):
            extra_headers = self._get_headers_with_token()

            try:
                if method.upper() == "GET":
                    resp = self.session.get(
                        url, params=params, headers=extra_headers, timeout=25
                    )
                else:
                    resp = self.session.post(
                        url, json=json_body, headers=extra_headers, timeout=25
                    )
            except requests.RequestException as exc:
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"HDI API {method} başarısız ({context_label}): {exc}"
                    ) from exc
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "HDI API bağlantı hatası (%s, deneme=%d/%d): %s. %.1f s bekleniyor...",
                    context_label, attempt + 1, self.BLOCK_MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
                continue

            # reCAPTCHA token geçersiz → invalidate et, bir sonraki turda yenilenir
            if self._is_recaptcha_error(resp):
                logger.warning(
                    "HDI reCAPTCHA token geçersiz (%s, deneme=%d/%d). "
                    "Token yenileniyor...",
                    context_label, attempt + 1, self.BLOCK_MAX_RETRIES,
                )
                self.token_manager.invalidate()
                last_response = resp
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"HDI reCAPTCHA token sürekli geçersiz ({context_label}), "
                        f"tüm denemeler tükendi. "
                        f"body={resp.text[:300]!r}"
                    )
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                time.sleep(delay)
                continue

            retryable = self._looks_blocked(resp) or not resp.ok
            if retryable:
                last_response = resp
                last_detail = (
                    f"status={resp.status_code}, "
                    f"content_type={resp.headers.get('Content-Type')}, "
                    f"body={resp.text[:300]!r}"
                )
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"HDI API isteği başarısız ({context_label}), "
                        f"tüm denemeler ({self.BLOCK_MAX_RETRIES + 1}) tükendi. {last_detail}"
                    )
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "HDI API hata/blok şüphesi (%s, deneme=%d/%d, %s). "
                    "%.1f s bekleniyor ve session sıfırlanıyor...",
                    context_label, attempt + 1, self.BLOCK_MAX_RETRIES, last_detail, delay,
                )
                time.sleep(delay)
                self._reset_session()
                continue

            last_response = resp
            break

        return last_response  # type: ignore[return-value]

    @staticmethod
    def _parse_hdi_response(response: requests.Response, context_label: str) -> list[dict]:
        """HDI sarmalayıcı response'unu parse eder ve data listesini döner.

        Beklenen format:
          {"data": [...], "isSuccess": true, "statusCode": 200, "errorMessage": null}
        """
        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperParseError(
                f"HDI API geçersiz JSON döndürdü ({context_label}): {exc} "
                f"body_len={len(response.text)} body_preview={response.text[:200]!r}"
            ) from exc

        if not data.get("isSuccess", True):
            err_msg = data.get("errorMessage") or data.get("error") or "(mesaj yok)"
            logger.warning("HDI API başarısız yanıt (%s): %s", context_label, err_msg)
            return []

        records = data.get("data") or []
        if not isinstance(records, list):
            return []

        return records

    # ------------------------------------------------------------------ #
    # Public API metodları                                                #
    # ------------------------------------------------------------------ #

    def get_districts(self, *, province_id: str | int) -> list[dict]:
        """Belirli bir il için ilçe listesini çeker.

        Args:
            province_id: Plaka kodu (1..81, başında 0 YOK). Örn: 16 (Bursa).

        Returns:
            [{"id": "202", "name": "ADANA MERKEZ"}, ...]
        """
        context = f"districts/provinceId={province_id}"
        resp = self._request_with_retry(
            "GET",
            self.DISTRICTS_URL,
            context_label=context,
            params={"provinceId": str(province_id)},
        )
        return self._parse_hdi_response(resp, context)

    def get_institutions(
        self,
        *,
        product_id: str | int,
        province_id: str | int,
        district_id: str | int,
        institution_type_id: str | int,
    ) -> list[dict]:
        """Belirli bir il/ilçe/ürün/kurum tipi kombinasyonu için kurum listesini çeker.

        Args:
            product_id:          HDI ürün ID'si (örn. "373").
            province_id:         Plaka kodu (örn. "16" = Bursa). Başında 0 YOK.
            district_id:         HDI'nın ilçe ID'si (districts endpoint'inden).
            institution_type_id: HDI kurum tipi ID'si (1=Hastane, 2=Eczane, ...).

        Returns:
            [
              {
                "description": "Acıbadem Bursa Hastanesi",
                "address": "...",
                "phone": "2242704444",
                "typeDescription": "Hastane",
                "hcnwDetailDescription": "A1 Kurumları",
                "latitude": "40.212964",
                "longitude": "28.976643",
                ...
              }, ...
            ]
        """
        payload = {
            "productId": str(product_id),
            "provinceId": str(province_id),
            "districtId": str(district_id),
            "institutionTypeId": str(institution_type_id),
        }
        context = (
            f"institutions/product={product_id}/province={province_id}"
            f"/district={district_id}/type={institution_type_id}"
        )
        resp = self._request_with_retry(
            "POST",
            self.INSTITUTIONS_URL,
            context_label=context,
            json_body=payload,
        )
        return self._parse_hdi_response(resp, context)
