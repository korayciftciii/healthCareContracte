from __future__ import annotations

import logging
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.exceptions import ScraperHTTPError, ScraperParseError

logger = logging.getLogger(__name__)

# F5 ASM / BIG-IP WAF'ının döndürdüğü blok sayfasını tespit etmek için
_WAF_BLOCK_MARKERS = (
    "Request Rejected",
    "Your support ID is",
    "The requested URL was rejected",
)


class AxaClient:
    """AXA Sigorta kurumsal sitesi / API istemcisi.

    Endpoint: POST https://www.axasigorta.com.tr/api/axa/contracted/GetHealthServices
    Payload şekli:
      {
          "PolicyType": "TAMAMLAYICI SİGORTA",
          "ServiceName": "",
          "ServiceTypeName": "",
          "CityName": "BURSA",
          "DistrictName": "",
          "ServiceId": "17"
      }

    WAF Notları:
        AXA'nın önündeki F5 BIG-IP ASM, datacenter IP'lerinden gelen veya
        eksik browser fingerprint'i olan istekleri reddeder. Bu client:
        - Gerçek Chrome tarayıcısının gönderdiği tam Sec-* header setini ekler
        - WAF blok sayfası geldiğinde session'ı sıfırlayıp yeniden dener
        - İstekler arası random jitter ile burst davranışını önler
    """

    BASE_URL = "https://www.axasigorta.com.tr/api/axa/contracted/GetHealthServices"
    PAGE_URL = "https://www.axasigorta.com.tr/anlasmali-saglik-kurumlari"

    # WAF blok sonrası maksimum yeniden deneme sayısı
    WAF_MAX_RETRIES = 2
    # Yeniden denemeler arası bekleme süresi (saniye) — exponential backoff
    WAF_RETRY_BASE_DELAY = 5.0

    def __init__(self, session: requests.Session | None = None):
        self.session = session or self._build_session()
        self._session_primed = False

    def _build_session(self) -> requests.Session:
        """Gerçek Chrome tarayıcısını taklit eden bir requests.Session oluşturur.

        F5 ASM'nin bot tespiti şu header'ların varlığını/yokluğunu kontrol eder:
        - Sec-CH-UA, Sec-CH-UA-Mobile, Sec-CH-UA-Platform (Client Hints)
        - Sec-Fetch-Site, Sec-Fetch-Mode, Sec-Fetch-Dest (Fetch Metadata)
        - Accept-Language (her gerçek tarayıcıda bulunur)
        """
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        # Header sırası önemli: Chrome'un gerçek sırasını takip ediyoruz
        session.headers = requests.structures.CaseInsensitiveDict({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Origin": "https://www.axasigorta.com.tr",
            "Referer": "https://www.axasigorta.com.tr/anlasmali-saglik-kurumlari",
            "X-Requested-With": "XMLHttpRequest",
            # Fetch Metadata — tarayıcı her cross-origin isteğe ekler
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            # Client Hints — Chrome 89+ tüm isteklere ekler
            "Sec-CH-UA": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            # Bağlantı yönetimi
            "Connection": "keep-alive",
        })
        return session

    def _ensure_session_primed(self) -> None:
        """AXA'nın WAF/session koruması için önce sayfa GET isteği yapılır.

        Amaç:
        1. Oturum çerezi (XSRF-TOKEN vb.) almak
        2. WAF'a gerçek bir tarayıcı davranışını taklit ettirmek (sayfa ziyareti → API)
        """
        if self._session_primed:
            return
        try:
            # Sayfa GET'i: tarayıcı gibi davranmak için Accept header'ı geçici değiştir
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
            logger.warning("AXA sayfa GET başarısız (devam ediliyor): %s", exc)
        finally:
            self._session_primed = True

        # XSRF token varsa POST isteklerine ekle
        xsrf_token = self.session.cookies.get("XSRF-TOKEN")
        if xsrf_token:
            self.session.headers["X-XSRF-TOKEN"] = xsrf_token

        # Sayfa ziyareti ile API isteği arasına gerçekçi bir gecikme ekle
        time.sleep(random.uniform(1.5, 3.5))

    def _reset_session(self) -> None:
        """WAF bloğu sonrası session'ı tamamen sıfırlar.

        Aynı session (ve cookie) ile tekrar deneme yapmak WAF'ta aynı
        blok kuralını tetikleyebilir; taze session + yeni GET daha güvenli.
        """
        logger.info("AXA session sıfırlanıyor (WAF bloğu sonrası)...")
        self.session.close()
        self.session = self._build_session()
        self._session_primed = False
        self._ensure_session_primed()

    @staticmethod
    def _is_waf_block(response: requests.Response) -> bool:
        """F5 BIG-IP ASM blok sayfasını tespit eder."""
        if response.status_code in (403, 200) and "text/html" in response.headers.get("Content-Type", ""):
            body_snippet = response.text[:500]
            return any(marker in body_snippet for marker in _WAF_BLOCK_MARKERS)
        return False

    def get_institutions(
        self,
        *,
        policy_type: str,
        service_id: str,
        city_name: str,
        district_name: str = "",
        service_type_name: str = "",
    ) -> list[dict]:
        """AXA API'sinden belirli bir il/poliçe/servis ID için kurum listesini çeker.

        Returns list of dicts:
        [
          {
            "ID": "7a67dfb5-de99-4d83-bb5f-c418542c40c3",
            "KurumAdi": "ACIBADEM BURSA HASTANESİ",
            "Tip": "HASTANE",
            "AnlasmaTipi": "TAMAMLAYICI SİGORTA",
            "Sehir": "BURSA",
            "Ilce": "NİLÜFER",
            "Adres": "FSM BULV. SÜMER SOK. NO: 1 NİLÜFER BURSA",
            "Tel": "(224)270 44 44",
            "TamamlayiciUrunAnlasmaDurumu": "SADECE KARDİYOLOJİ...",
            "GmapEnlem": "40.213",
            "GmapBoylam": "28.9758",
            "Kurumkodu": "208119"
          },
          ...
        ]
        """
        payload = {
            "PolicyType": policy_type,
            "ServiceName": "",
            "ServiceTypeName": service_type_name,
            "CityName": city_name.upper(),
            "DistrictName": district_name.upper() if district_name else "",
            "ServiceId": str(service_id),
        }

        self._ensure_session_primed()

        response = self._post_with_waf_retry(payload=payload, city_name=city_name, service_id=service_id)

        if not response.ok:
            raise ScraperHTTPError(
                f"AXA API returned HTTP {response.status_code} ({city_name}, ServiceId={service_id}): {response.text[:300]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperParseError(
                f"AXA API did not return valid JSON ({city_name}, ServiceId={service_id}): {exc} "
                f"body_len={len(response.text)} body_preview={response.text[:200]!r}"
            ) from exc

        # AXA Response wrapper parsing:
        # { "result": { "restResponse": { "success": true, "content": [...] } } }
        result = data.get("result") or {}
        rest_resp = result.get("restResponse") or {}
        if not rest_resp.get("success", True):
            # API returned logical error
            return []

        content = rest_resp.get("content") or []
        if not isinstance(content, list):
            return []

        return content

    def _post_with_waf_retry(
        self,
        *,
        payload: dict,
        city_name: str,
        service_id: str,
    ) -> requests.Response:
        """WAF blok tespiti ile POST isteği atar; blok varsa session sıfırlayıp yeniden dener.

        Strateji:
        - İlk denemede normal POST gönderilir.
        - Yanıt WAF blok sayfasıysa (HTML + 'Request Rejected' içeriği):
            1. Session tamamen sıfırlanır (yeni cookie + yeni GET)
            2. Exponential backoff + jitter ile beklenir
            3. WAF_MAX_RETRIES kadar yeniden denenir
        - Tüm denemeler tükenirse ScraperHTTPError fırlatılır.
        """
        last_response: requests.Response | None = None

        for attempt in range(self.WAF_MAX_RETRIES + 1):
            try:
                resp = self.session.post(self.BASE_URL, json=payload, timeout=20)
            except requests.RequestException as exc:
                raise ScraperHTTPError(
                    f"AXA API POST failed ({city_name}, ServiceId={service_id}): {exc}"
                ) from exc

            if self._is_waf_block(resp):
                support_id = ""
                try:
                    # F5'in döndürdüğü destek ID'sini loglamak için parse et
                    import re
                    match = re.search(r"support ID is:\s*(\d+)", resp.text)
                    if match:
                        support_id = match.group(1)
                except Exception:
                    pass

                if attempt >= self.WAF_MAX_RETRIES:
                    raise ScraperHTTPError(
                        f"AXA API WAF tarafından engellendi ({city_name}, ServiceId={service_id}), "
                        f"tüm denemeler tükendi (support_id={support_id}). "
                        f"VM IP'si datacenter havuzunda olabilir; proxy gerekebilir."
                    )

                delay = self.WAF_RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(1.0, 3.0)
                logger.warning(
                    "WAF bloğu tespit edildi (%s/ServiceId=%s, support_id=%s, deneme=%d/%d). "
                    "%.1f saniye bekleniyor ve session sıfırlanıyor...",
                    city_name, service_id, support_id,
                    attempt + 1, self.WAF_MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                self._reset_session()
                continue

            last_response = resp
            break

        return last_response  # type: ignore[return-value]
