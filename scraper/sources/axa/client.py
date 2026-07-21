from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.exceptions import ScraperHTTPError, ScraperParseError


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
    """

    BASE_URL = "https://www.axasigorta.com.tr/api/axa/contracted/GetHealthServices"
    PAGE_URL = "https://www.axasigorta.com.tr/anlasmali-saglik-kurumlari"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or self._build_session()
        self._session_primed = False

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Origin": "https://www.axasigorta.com.tr",
            "Referer": "https://www.axasigorta.com.tr/anlasmali-saglik-kurumlari",
            "X-Requested-With": "XMLHttpRequest",
        })
        return session

    def _ensure_session_primed(self) -> None:
        """AXA'nın WAF/session koruması, sayfa hiç ziyaret edilmeden yapılan POST
        isteklerini 200 + boş body ile sessizce reddediyor. Cookie'leri (ör.
        XSRF-TOKEN) almak için önce sayfayı bir kez GET ediyoruz."""
        if self._session_primed:
            return
        try:
            self.session.get(self.PAGE_URL, timeout=15)
        except requests.RequestException:
            pass
        finally:
            self._session_primed = True

        xsrf_token = self.session.cookies.get("XSRF-TOKEN")
        if xsrf_token:
            self.session.headers["X-XSRF-TOKEN"] = xsrf_token

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

        try:
            response = self.session.post(self.BASE_URL, json=payload, timeout=15)
        except requests.RequestException as exc:
            raise ScraperHTTPError(f"AXA API POST failed ({city_name}, ServiceId={service_id}): {exc}") from exc

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
