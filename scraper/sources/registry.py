"""Scraper plugin registry.

Şirket bazlı scraper'lar @register decorator'ı ile bu registry'e kaydedilir.
ScrapeJobRunner, job.source_key değerini kullanarak doğru scraper'ı seçer.

Yeni bir şirket eklemek için:
    1. scraper/sources/<company>/ dizini oluştur
    2. scraper.py içinde BaseScraper'ı implement et
    3. @register("<company_code>") decorator'ını ekle
    4. Bu modülün altındaki import listesine ekle
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseScraper

SCRAPER_REGISTRY: dict[str, type["BaseScraper"]] = {}


def register(source_key: str):
    """Scraper sınıfını registry'e kaydeder.

    Kullanım:
        @register("axa")
        class AxaScraper(BaseScraper):
            source_key = "axa"
    """
    def decorator(cls):
        cls.source_key = source_key
        SCRAPER_REGISTRY[source_key] = cls
        return cls
    return decorator


def get_scraper(source_key: str) -> type["BaseScraper"]:
    """source_key için kayıtlı scraper sınıfını döner.

    Kayıtlı değilse ValueError fırlatır.
    """
    if source_key not in SCRAPER_REGISTRY:
        available = ", ".join(sorted(SCRAPER_REGISTRY.keys())) or "(none)"
        raise ValueError(
            f"'{source_key}' için kayıtlı scraper bulunamadı. "
            f"Mevcut: {available}"
        )
    return SCRAPER_REGISTRY[source_key]


# ------------------------------------------------------------------ #
# Kayıtlı scraper'ları import et — bu satırlar yeni şirket ekledikçe #
# genişletilir.                                                       #
# ------------------------------------------------------------------ #
from .axa import scraper as _axa_scraper  # noqa: E402, F401
