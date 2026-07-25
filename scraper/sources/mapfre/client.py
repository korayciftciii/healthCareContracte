from __future__ import annotations

import logging
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.exceptions import ScraperHTTPError, ScraperParseError

logger = logging.getLogger(__name__)


class MapfreClient:
    """Mapfre Sigorta 'ComeRoundForms' API istemcisi.

    Endpoint: POST https://form.mapfre.com.tr/ComeRoundForms/biws/api/searchContractedInstitutions
    Payload şekli:
      {
          "cityId": "İstanbul",
          "districtId": "",
          "networkTypeCode": "65",
          "institutionType": "TIP MERKEZİ",
          "expertiseType": ""
      }

    Not: "cityId" alanına (ismine rağmen) il ADI gönderilir (örn. "İstanbul"),
    id değil. "districtId" ZORUNLU DEĞİLDİR — boş bırakılırsa AXA/Anadolu gibi
    o ilin TÜM ilçelerindeki kurumlar tek istekte döner; her kurumun ilçesi
    response'taki "ilceadi" alanından okunur. "networkTypeCode" ve
    "institutionType" ZORUNLUDUR. "expertiseType" bu entegrasyonda kullanılmaz,
    her zaman boş string gönderilir.

    Response şekli:
      {
        "RecordList": [
          {
            "kurum_tip": "HASTANE",
            "centerLocation": {"x_coord": "41.02454", "y_coord": "29.0839"},
            "address": "...", "text_info": "...",
            "recordname": "MEDICANA ÇAMLICA HOSPITALS",
            "network_tip_adi": "TSS KATILIMLI NETWORK",
            "recordcode": "01000075", "telephone": "02165226000",
            "ilceid": "34000025000", "ilid": "34", "network_tip_kodu": "107",
            "iladi": "İstanbul", "ilceadi": "Üsküdar",
            "email": "anlasmalikurumlar@medicana.com.tr"
          }, ...
        ]
      }

    Güvenlik notları:
        Diğer kaynaklarla (AXA/Allianz/Anadolu) aynı sağlam mantık: gerçek
        tarayıcı header seti, session priming (form sayfası GET), bloklanmaya
        karşı exponential backoff + jitter, beklenmeyen yanıt durumunda
        session sıfırlama. Mapfre önünde F5 BIG-IP TS çerezi (TS011821e6) ve
        FORMSESSIONID görülüyor; ikisi de session priming GET'i sırasında
        doğal olarak edinilir.
    """

    BASE_URL = "https://form.mapfre.com.tr/ComeRoundForms/biws/api/searchContractedInstitutions"
    PAGE_URL = "https://form.mapfre.com.tr/iletisim/formlar/"

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
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Origin": "https://form.mapfre.com.tr",
            "Referer": "https://form.mapfre.com.tr/iletisim/formlar/",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Connection": "keep-alive",
        })
        return session

    def _ensure_session_primed(self) -> None:
        """Form sayfasına bir GET atarak oturum çerezlerini (TS/FORMSESSIONID) edinir."""
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
            logger.warning("Mapfre sayfa GET başarısız (devam ediliyor): %s", exc)
        finally:
            self._session_primed = True

        time.sleep(random.uniform(1.5, 3.5))

    def _reset_session(self) -> None:
        logger.info("Mapfre session sıfırlanıyor (anti-bot bloğu şüphesi sonrası)...")
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

    def get_institutions(
        self,
        *,
        city_id: str,
        network_type_code: str,
        institution_type: str,
        district_id: str = "",
        expertise_type: str = "",
    ) -> list[dict]:
        """Mapfre API'sinden belirli bir il/network/kurum tipi için kurum listesini çeker.

        districtId ZORUNLU DEĞİLDİR — boş gönderilirse o ilin TÜM ilçelerindeki
        kurumlar döner; her kurumun kendi ilçesi response'taki "ilceadi"
        alanından okunur.
        """
        payload = {
            "cityId": city_id,
            "districtId": district_id,
            "networkTypeCode": str(network_type_code),
            "institutionType": institution_type,
            "expertiseType": expertise_type,
        }

        self._ensure_session_primed()

        response = self._post_with_retry(
            payload=payload,
            city_id=city_id,
            network_type_code=network_type_code,
            institution_type=institution_type,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperParseError(
                f"Mapfre API did not return valid JSON (city={city_id}, network={network_type_code}, "
                f"type={institution_type}): {exc} body_len={len(response.text)} "
                f"body_preview={response.text[:200]!r}"
            ) from exc

        content = data.get("RecordList") or []
        if not isinstance(content, list):
            return []

        return content

    def _post_with_retry(
        self,
        *,
        payload: dict,
        city_id: str,
        network_type_code: str,
        institution_type: str,
    ) -> requests.Response:
        """POST isteği atar; hem anti-bot bloğu hem de genel HTTP hatalarında
        (429, 500 vb.) backoff + session reset ile yeniden dener.

        BLOCK_MAX_RETRIES kadar yeniden denenir (toplam BLOCK_MAX_RETRIES + 1 deneme);
        tüm denemeler tükenirse ScraperHTTPError fırlatılır ve tarama bir sonraki
        il/network/kurum tipine geçer (job durmaz).
        """
        last_response: requests.Response | None = None

        for attempt in range(self.BLOCK_MAX_RETRIES + 1):
            try:
                resp = self.session.post(self.BASE_URL, json=payload, timeout=20)
            except requests.RequestException as exc:
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"Mapfre API POST failed (city={city_id}, network={network_type_code}, "
                        f"type={institution_type}): {exc}"
                    ) from exc
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Mapfre API isteği başarısız (city=%s, network=%s, type=%s, deneme=%d/%d): %s. "
                    "%.1f saniye bekleniyor...",
                    city_id, network_type_code, institution_type, attempt + 1, self.BLOCK_MAX_RETRIES, exc, delay,
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
                        f"Mapfre API isteği başarısız oldu (city={city_id}, network={network_type_code}, "
                        f"type={institution_type}), tüm denemeler ({self.BLOCK_MAX_RETRIES + 1}) tükendi. "
                        f"{last_error_detail}"
                    )

                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Mapfre API hata/blok şüphesi (city=%s, network=%s, type=%s, deneme=%d/%d, %s). "
                    "%.1f saniye bekleniyor ve session sıfırlanıyor...",
                    city_id, network_type_code, institution_type, attempt + 1, self.BLOCK_MAX_RETRIES,
                    last_error_detail, delay,
                )
                time.sleep(delay)
                self._reset_session()
                continue

            last_response = resp
            break

        return last_response  # type: ignore[return-value]
