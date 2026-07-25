from __future__ import annotations

import logging
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.exceptions import ScraperHTTPError, ScraperParseError

logger = logging.getLogger(__name__)


class AllianzClient:
    """Allianz Sigorta 'oneweb-health-module' API istemcisi.

    Endpoint: POST https://digitall.allianz.com.tr/oneweb-health-module-backend/api/myHealth/search
    (Backend GET'i 405 Method Not Allowed ile reddediyor; parametreler query-string
    olarak kalıyor, sadece HTTP metodu POST.)
    Query params:
      {
          "serviceType": "CONTRACTEDHEALTH",
          "country": "TR",
          "city": "01",              # plaka kodu, 01..81
          "instutionType": 1,
          "networkType": 17,          # bkz. NETWORK_TYPE eşlemesi (companies seed'inde)
          "partitionType": "MDSG",    # MDSG=Modüler Sağlık(ÖSS), STSS=Tamamlayıcı Sağlık(TSS)
      }

    Not: "district" parametresi opsiyoneldir — verilmezse Allianz o ilin TÜM
    kurumlarını döner. search response'unda ilçe bilgisi hiç gelmediği için
    (sadece serbest metin "address" var), ilçeyi doğru şekilde kaydedebilmek
    amacıyla önce valueSetter API'sinden (valueType=DISTRICTS) o ile ait ilçe
    id/isim listesi çekilir, sonra her ilçe id'si search isteğine "district"
    parametresi olarak eklenerek kurumlar ilçe bazında toplanır (bkz. get_districts).

    Response şekli:
      {
        "timestamp": "...",
        "response": [
          {
            "instituteName": "...", "phone": "...", "fax": "...", "mail": "...",
            "address": "...", "latitude": "...", "longitude": "...",
            "instituteCode": 1122, "networkGroupId": 0, "hasActivity": 1,
            "institutePartitions": [{"code": "0", "explanation": "...", "detailExplanation": []}],
            "hasTssPaymentWarn": false, "tssInstitute": true, "advantageous": false
          }, ...
        ],
        "response_code": 0
      }

    Güvenlik notları:
        Allianz'ın dijital platformu da (Akamai/CDN benzeri) bot trafiğini
        engelleyebilir. Bu client:
        - Gerçek Chrome tarayıcısının header setini (Sec-*, Client Hints) ekler
        - İstek öncesi ana sayfaya bir GET ile session/cookie edinir
        - İstekler arası rastgele jitter uygular (banlanmayı önlemek için)
        - Beklenmeyen (HTML/boş) yanıt durumunda session'ı sıfırlayıp yeniden dener
    """

    BASE_URL = "https://digitall.allianz.com.tr/oneweb-health-module-backend/api/myHealth/search"
    VALUE_SETTER_URL = "https://digitall.allianz.com.tr/oneweb-health-module-backend/api/myHealth/valueSetter"
    PAGE_URL = "https://digitall.allianz.com.tr/"

    # Fixed/varsayılan API parametreleri (Allianz tarafında sabit gözüküyor)
    DEFAULT_SERVICE_TYPE = "CONTRACTEDHEALTH"
    DEFAULT_COUNTRY = "TR"
    DEFAULT_INSTITUTION_TYPE = 1

    # Blok/anti-bot tespiti sonrası maksimum yeniden deneme sayısı
    BLOCK_MAX_RETRIES = 2
    BLOCK_RETRY_BASE_DELAY = 5.0

    def __init__(self, session: requests.Session | None = None):
        self.session = session or self._build_session()
        self._session_primed = False

    def _build_session(self) -> requests.Session:
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
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://digitall.allianz.com.tr",
            "Referer": "https://digitall.allianz.com.tr/",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Sec-CH-UA": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Connection": "keep-alive",
        })
        return session

    def _ensure_session_primed(self) -> None:
        """Anasayfaya bir GET atarak oturum çerezlerini (varsa XSRF token vb.) edinir."""
        if self._session_primed:
            return
        try:
            resp = self.session.get(
                self.PAGE_URL,
                timeout=20,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Upgrade-Insecure-Requests": "1",
                },
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Allianz sayfa GET başarısız (devam ediliyor): %s", exc)
        finally:
            self._session_primed = True

        for cookie_name in ("XSRF-TOKEN", "xsrf-token"):
            token = self.session.cookies.get(cookie_name)
            if token:
                self.session.headers["X-XSRF-TOKEN"] = token
                break

        time.sleep(random.uniform(1.5, 3.5))

    def _reset_session(self) -> None:
        logger.info("Allianz session sıfırlanıyor (anti-bot bloğu şüphesi sonrası)...")
        self.session.close()
        self.session = self._build_session()
        self._session_primed = False
        self._ensure_session_primed()

    @staticmethod
    def _looks_blocked(response: requests.Response) -> bool:
        """JSON beklenirken HTML/boş içerik dönmesi anti-bot bloğuna işaret eder."""
        content_type = response.headers.get("Content-Type", "")
        if response.status_code in (403, 429):
            return True
        if "application/json" not in content_type and response.text.strip():
            return True
        return False

    def get_districts(self, *, city_plate_code: str) -> list[dict]:
        """Bir il için Allianz ilçe listesini döner (valueSetter API, valueType=DISTRICTS).

        Dönen her öğe: {"key": "0118" (ilçe id), "value": "TUFANBEYLİ" (ilçe adı), "keyX": "TR"}
        """
        city = str(city_plate_code).zfill(2)
        data = {
            "valueType": "DISTRICTS",
            "country": self.DEFAULT_COUNTRY,
            "city": city,
        }

        self._ensure_session_primed()

        response = self._post_form_with_retry(data=data, context=f"city={city}/valueType=DISTRICTS")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ScraperParseError(
                f"Allianz valueSetter API did not return valid JSON (city={city}): "
                f"{exc} body_len={len(response.text)} body_preview={response.text[:200]!r}"
            ) from exc

        content = payload.get("response") or []
        if not isinstance(content, list):
            return []
        return content

    def get_institutions(
        self,
        *,
        city_plate_code: str,
        partition_type: str,
        network_type: int | str,
        institution_type: int | None = None,
        district: str | None = None,
    ) -> list[dict]:
        """Allianz API'sinden belirli bir il/poliçe tipi/network için kurum listesini çeker.

        district parametresi verilirse (ilçe id, örn. "0118") istek o ilçeyle
        sınırlandırılır; verilmezse ilin TÜM kurumları döner (bkz. sınıf docstring).
        """
        params = {
            "serviceType": self.DEFAULT_SERVICE_TYPE,
            "country": self.DEFAULT_COUNTRY,
            "city": str(city_plate_code).zfill(2),
            "instutionType": institution_type if institution_type is not None else self.DEFAULT_INSTITUTION_TYPE,
            "networkType": network_type,
            "partitionType": partition_type,
        }
        if district:
            params["district"] = district

        self._ensure_session_primed()

        response = self._post_with_retry(params=params, city_plate_code=city_plate_code, network_type=network_type)

        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperParseError(
                f"Allianz API did not return valid JSON (city={city_plate_code}, networkType={network_type}): "
                f"{exc} body_len={len(response.text)} body_preview={response.text[:200]!r}"
            ) from exc

        if data.get("response_code") not in (0, None):
            logger.warning(
                "Allianz API response_code=%s (city=%s, networkType=%s)",
                data.get("response_code"), city_plate_code, network_type,
            )

        content = data.get("response") or []
        if not isinstance(content, list):
            return []

        return content

    def _post_with_retry(
        self,
        *,
        params: dict,
        city_plate_code: str,
        network_type,
    ) -> requests.Response:
        """POST isteği atar; hem anti-bot bloğu hem de genel HTTP hatalarında
        (405, 500 vb.) backoff + session reset ile yeniden dener.

        BLOCK_MAX_RETRIES kadar yeniden denenir (toplam BLOCK_MAX_RETRIES + 1 deneme);
        tüm denemeler tükenirse ScraperHTTPError fırlatılır ve tarama bir sonraki
        network/il'e geçer (job durmaz).
        """
        last_response: requests.Response | None = None
        last_error_detail = ""

        for attempt in range(self.BLOCK_MAX_RETRIES + 1):
            try:
                resp = self.session.post(self.BASE_URL, params=params, timeout=20)
            except requests.RequestException as exc:
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"Allianz API POST failed (city={city_plate_code}, networkType={network_type}): {exc}"
                    ) from exc
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Allianz API isteği başarısız (city=%s, networkType=%s, deneme=%d/%d): %s. "
                    "%.1f saniye bekleniyor...",
                    city_plate_code, network_type, attempt + 1, self.BLOCK_MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
                continue

            retryable = self._looks_blocked(resp) or not resp.ok
            if retryable:
                last_response = resp
                last_error_detail = (
                    f"status={resp.status_code}, content_type={resp.headers.get('Content-Type')}, "
                    f"body={resp.text[:300]!r}"
                )
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"Allianz API isteği başarısız oldu (city={city_plate_code}, networkType={network_type}), "
                        f"tüm denemeler ({self.BLOCK_MAX_RETRIES + 1}) tükendi. {last_error_detail}"
                    )

                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Allianz API hata/blok şüphesi (city=%s, networkType=%s, deneme=%d/%d, %s). "
                    "%.1f saniye bekleniyor ve session sıfırlanıyor...",
                    city_plate_code, network_type, attempt + 1, self.BLOCK_MAX_RETRIES, last_error_detail, delay,
                )
                time.sleep(delay)
                self._reset_session()
                continue

            last_response = resp
            break

        return last_response  # type: ignore[return-value]

    def _post_form_with_retry(self, *, data: dict, context: str) -> requests.Response:
        """valueSetter gibi form-urlencoded endpoint'ler için _post_with_retry ile aynı
        blok/backoff mantığını uygular."""
        last_response: requests.Response | None = None
        last_error_detail = ""
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

        for attempt in range(self.BLOCK_MAX_RETRIES + 1):
            try:
                resp = self.session.post(self.VALUE_SETTER_URL, data=data, headers=headers, timeout=20)
            except requests.RequestException as exc:
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(f"Allianz valueSetter API POST failed ({context}): {exc}") from exc
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Allianz valueSetter isteği başarısız (%s, deneme=%d/%d): %s. %.1f saniye bekleniyor...",
                    context, attempt + 1, self.BLOCK_MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
                continue

            retryable = self._looks_blocked(resp) or not resp.ok
            if retryable:
                last_response = resp
                last_error_detail = (
                    f"status={resp.status_code}, content_type={resp.headers.get('Content-Type')}, "
                    f"body={resp.text[:300]!r}"
                )
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"Allianz valueSetter isteği başarısız oldu ({context}), "
                        f"tüm denemeler ({self.BLOCK_MAX_RETRIES + 1}) tükendi. {last_error_detail}"
                    )

                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Allianz valueSetter hata/blok şüphesi (%s, deneme=%d/%d, %s). "
                    "%.1f saniye bekleniyor ve session sıfırlanıyor...",
                    context, attempt + 1, self.BLOCK_MAX_RETRIES, last_error_detail, delay,
                )
                time.sleep(delay)
                self._reset_session()
                continue

            last_response = resp
            break

        return last_response  # type: ignore[return-value]
