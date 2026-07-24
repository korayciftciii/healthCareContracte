from __future__ import annotations

import logging
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.exceptions import ScraperHTTPError, ScraperParseError

logger = logging.getLogger(__name__)


class AnadoluClient:
    """Anadolu Sigorta 'atlas' API istemcisi.

    Endpoint: POST https://sm.anadolusigorta.com.tr/atlas/api/find-institutions/network-institutions
    Payload şekli:
      {
          "cityName": "İSTANBUL",
          "countyName": "KADIKÖY",
          "networkCodes": ["BT_A","BT_B","BT_C","TSS_A","TSS_B",
                            "TSS_Tamamlayıcı_Eko","TSS_Tamamlayıcı", "<seçilen network kodu>"],
          "mensup": false,
          "includepharmacies": false
      }

    Not: "networkCodes" dizisi, Anadolu'nun formundaki tüm network buton kodlarının
    sabit bir ön eki (ürün tipine göre TSS ya da ÖSS seti) + en sonda seçilen networkün
    kodu şeklinde kurgulanır. Bu client sadece "Anlaşmalı Sağlık Kurumu" sorgulama tipini
    hedefler (Tüp Bebek / Robotik Cerrahi gibi diğer sorgulama tipleri için dizide ekstra
    bir "marker" elemanı gönderilir; biz bunu hiç göndermiyoruz). Kurum tipi filtresi de
    (dizinin en sonuna eklenen sayısal id) kasıtlı olarak GÖNDERİLMİYOR — kurum tipi bizim
    formumuzda opsiyonel, response'taki "type" alanından kendimiz eşliyoruz.

    "countyName" (ilçe) ZORUNLU DEĞİLDİR — boş bırakılırsa AXA gibi o ilin TÜM
    ilçelerindeki kurumlar tek istekte döner. Her kurumun ilçesi response'taki
    "countyName" alanından okunur.

    Response şekli:
      {
        "data": [
          {
            "skrs": "534663001", "organizationName": "...", "type": "Teşhis Tanı Merkezi",
            "cityName": "İSTANBUL", "countyName": "KADIKÖY", "address": "...",
            "phone": "...", "parallel": "40.97...", "meridian": "29.05...",
            "networkCode": "AHN", "networkCodes": ["AHN", "E", "S"], ...
          }, ...
        ]
      }

    Güvenlik notları:
        Diğer kaynaklarla (AXA/Allianz) aynı sağlam mantık: gerçek tarayıcı header seti,
        session priming (anasayfa GET), bloklanmaya karşı exponential backoff + jitter,
        beklenmeyen yanıt durumunda session sıfırlama.
    """

    BASE_URL = "https://sm.anadolusigorta.com.tr/atlas/api/find-institutions/network-institutions"
    PAGE_URL = "https://saglik.anadolusigorta.com.tr/"

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
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://saglik.anadolusigorta.com.tr",
            "Referer": "https://saglik.anadolusigorta.com.tr/",
            "X_CHANNEL_ID": "WEB",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Sec-CH-UA": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Connection": "keep-alive",
        })
        return session

    def _ensure_session_primed(self) -> None:
        """Anasayfaya bir GET atarak oturum çerezlerini edinir."""
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
            logger.warning("Anadolu sayfa GET başarısız (devam ediliyor): %s", exc)
        finally:
            self._session_primed = True

        for cookie_name in ("XSRF-TOKEN", "xsrf-token"):
            token = self.session.cookies.get(cookie_name)
            if token:
                self.session.headers["X-XSRF-TOKEN"] = token
                break

        time.sleep(random.uniform(1.5, 3.5))

    def _reset_session(self) -> None:
        logger.info("Anadolu session sıfırlanıyor (anti-bot bloğu şüphesi sonrası)...")
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
        city_name: str,
        county_name: str = "",
        network_codes: list[str],
        include_pharmacies: bool = False,
    ) -> list[dict]:
        """Anadolu API'sinden belirli bir il/network için kurum listesini çeker.

        countyName ZORUNLU DEĞİLDİR — boş gönderilirse o ilin TÜM ilçelerindeki
        kurumlar döner; her kurumun kendi ilçesi response'taki "countyName"
        alanından okunur.
        """
        payload = {
            "cityName": city_name.upper(),
            "countyName": county_name.upper() if county_name else "",
            "networkCodes": network_codes,
            "mensup": False,
            "includepharmacies": include_pharmacies,
        }

        self._ensure_session_primed()

        response = self._post_with_retry(payload=payload, city_name=city_name, county_name=county_name)

        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperParseError(
                f"Anadolu API did not return valid JSON (city={city_name}, county={county_name}): "
                f"{exc} body_len={len(response.text)} body_preview={response.text[:200]!r}"
            ) from exc

        content = data.get("data") or []
        if not isinstance(content, list):
            return []

        return content

    def _post_with_retry(
        self,
        *,
        payload: dict,
        city_name: str,
        county_name: str,
    ) -> requests.Response:
        """POST isteği atar; hem anti-bot bloğu hem de genel HTTP hatalarında
        (429, 500 vb.) backoff + session reset ile yeniden dener.

        BLOCK_MAX_RETRIES kadar yeniden denenir (toplam BLOCK_MAX_RETRIES + 1 deneme);
        tüm denemeler tükenirse ScraperHTTPError fırlatılır ve tarama bir sonraki
        ilçe/network'e geçer (job durmaz).
        """
        last_response: requests.Response | None = None

        for attempt in range(self.BLOCK_MAX_RETRIES + 1):
            try:
                resp = self.session.post(self.BASE_URL, json=payload, timeout=20)
            except requests.RequestException as exc:
                if attempt >= self.BLOCK_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"Anadolu API POST failed (city={city_name}, county={county_name}): {exc}"
                    ) from exc
                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Anadolu API isteği başarısız (city=%s, county=%s, deneme=%d/%d): %s. "
                    "%.1f saniye bekleniyor...",
                    city_name, county_name, attempt + 1, self.BLOCK_MAX_RETRIES, exc, delay,
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
                        f"Anadolu API isteği başarısız oldu (city={city_name}, county={county_name}), "
                        f"tüm denemeler ({self.BLOCK_MAX_RETRIES + 1}) tükendi. {last_error_detail}"
                    )

                delay = self.BLOCK_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "Anadolu API hata/blok şüphesi (city=%s, county=%s, deneme=%d/%d, %s). "
                    "%.1f saniye bekleniyor ve session sıfırlanıyor...",
                    city_name, county_name, attempt + 1, self.BLOCK_MAX_RETRIES, last_error_detail, delay,
                )
                time.sleep(delay)
                self._reset_session()
                continue

            last_response = resp
            break

        return last_response  # type: ignore[return-value]
