import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import ScraperHTTPError, ScraperNotConfigured, ScraperParseError


def _as_list(value):
    """The upstream API is a PHP/Laravel backend: json_encode() serializes a PHP
    array as a JSON *object* (not a list) whenever its integer keys aren't a
    contiguous 0..n sequence (e.g. one item got filtered out server-side,
    leaving a gap). Observed in practice on /search-hospital with limit=50.
    Normalize both shapes to a plain list."""
    if isinstance(value, dict):
        return [value[k] for k in sorted(value.keys(), key=lambda k: int(k))]
    return value


class TamamlayiciSaglikClient:
    """Thin HTTP client for tamamlayicisaglik.com's internal-api endpoints.

    Confirmed by direct testing (no cookies/CSRF token required for these GET
    endpoints, plain requests work): cities, districts, hospital-types,
    company-list-results, search-hospital, networks.
    """

    def __init__(self, session: requests.Session | None = None):
        self.config = settings.SCRAPER_CONFIG
        self.base_url = self.config["BASE_URL"].rstrip("/")
        self.session = session or self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
            }
        )
        session.headers.update(self.config.get("REQUEST_HEADERS") or {})
        return session

    def _request(self, path: str, params) -> dict:
        """params may be a dict or a list of (key, value) tuples (needed for
        repeated array-style query params like companyIds[])."""
        if not path:
            raise ScraperNotConfigured("Scraper endpoint path is not configured (empty).")

        url = f"{self.base_url}{path}"
        if isinstance(params, dict):
            clean_params = {k: v for k, v in params.items() if v is not None}
        else:
            clean_params = [(k, v) for k, v in params if v is not None]

        try:
            response = self.session.get(
                url,
                params=clean_params,
                timeout=self.config["REQUEST_TIMEOUT_SECONDS"],
            )
        except requests.RequestException as exc:
            raise ScraperHTTPError(f"GET {url} failed: {exc}") from exc

        if not response.ok:
            raise ScraperHTTPError(
                f"GET {url} returned HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ScraperParseError(f"GET {url} did not return valid JSON: {exc}") from exc

    def _get_with_array_param(self, path: str, array_param_name: str, values: list[int], extra_params: dict) -> dict:
        params = list(extra_params.items()) + [(array_param_name, v) for v in values]
        return self._request(path, params)

    # --- reference/lookup endpoints (all wrapped as {"data": [...]}) ---

    def get_cities(self) -> list[dict]:
        """Returns [{"id": 34, "name": "İstanbul"}, ...] for all 81 provinces.
        Confirmed: id matches the official Turkish plate code (plaka kodu)."""
        return _as_list(self._request(self.config["CITY_LIST_PATH"], {})["data"])

    def get_districts(self, *, city_id: int) -> list[dict]:
        """Returns [{"id": 420, "name": "Adalar"}, ...] for the given city."""
        return _as_list(
            self._request(self.config["DISTRICT_LIST_PATH"], {"cityId": city_id})["data"]
        )

    def get_hospital_types(self) -> list[dict]:
        """Returns [{"id": 1, "name": "Hastane", "defaultItem": true}, ...]."""
        return _as_list(self._request(self.config["HOSPITAL_TYPES_PATH"], {})["data"])

    def get_networks(self, *, company_ids: list[int], product_type_id: int) -> dict:
        """Returns {"success": true, "data": {"<Company Display Name>": {"networks": [...]}}}."""
        path = self.config["NETWORKS_PATH"]
        return self._get_with_array_param(
            path, "companyIds[]", company_ids, {"productTypeId": product_type_id}
        )

    # --- company list (cross-sell widget; also usable to sync InsuranceCompany) ---

    def get_companies(
        self,
        *,
        city_id: int | None = None,
        product_type_id: int | None = None,
        except_company_id: int | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        path = self.config["COMPANY_LIST_PATH"]
        return self._request(
            path,
            {
                "page": page,
                "limit": limit,
                "cityId": city_id,
                "productTypeId": product_type_id,
                "exceptCompanyId": except_company_id,
            },
        )

    # --- the actual "anlaşmalı kurum" search (this is what ScrapeJobRunner uses) ---

    def get_institutions(
        self,
        *,
        company_external_id: int,
        city_id: int,
        district_id: int | None = None,
        product_type_id: int,
        query: str = "",
        page: int = 1,
        limit: int | None = None,
    ) -> dict:
        """Hits /internal-api/search-hospital. Response shape is FLAT:
        {"data": [...], "current_page": 1, "per_page": 5, "total": 189, "last_page": 38}
        — NOT nested like company-list-results. "data" is normalized to always
        be a list here (see _as_list — the upstream PHP backend sometimes
        serializes it as a gap-keyed JSON object instead).

        Each item: {id, name, highlighted_name, hospital_type: {id, name},
        network_ids: [...], district_name (string, not id), company_count,
        has_tss_payment_warn}. No address/phone/coordinates are provided by
        this endpoint.

        districtId is passed opportunistically (observed param naming pattern,
        not confirmed to filter server-side) — callers should still filter
        client-side on district_name if precise district scoping matters.
        """
        path = self.config["INSTITUTION_LIST_PATH"]
        params = {
            "query": query,
            "page": page,
            "limit": limit or self.config["DEFAULT_PAGE_SIZE"],
            "cityId": city_id,
            "districtId": district_id,
            "productTypeId": product_type_id,
        }
        payload = self._get_with_array_param(path, "companyIds[]", [company_external_id], params)
        payload["data"] = _as_list(payload.get("data", []))
        return payload
