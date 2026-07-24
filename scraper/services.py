"""ScrapeJobRunner dispatcher.

job.source_key değerine göre ilgili scraper plugin'ini registry'den alır ve çalıştırır.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.utils import timezone

from .sources.registry import get_scraper

if TYPE_CHECKING:
    from .models import ScrapeJob


class ScrapeJobRunner:
    """ScrapeJob'u doğru plugin ile çalıştıran ana çalıştırıcı (dispatcher)."""

    def run(self, job: "ScrapeJob") -> None:
        source_key = getattr(job, "source_key", "axa") or "axa"
        try:
            scraper_cls = get_scraper(source_key)
        except ValueError as exc:
            job.status = job.Status.FAILED
            job.error_message = str(exc)
            job.started_at = timezone.now()
            job.finished_at = timezone.now()
            job.append_log(f"HATA: {exc}")
            job.save()
            return

        # Başlangıç logunu ve dosya yolunu (logs/AXA/...) oluştur/kaydet
        job.pid = os.getpid()
        job.append_log(f"Arka plan işlemi başlatıldı. PID: {job.pid}")
        job.save()

        scraper = scraper_cls()
        scraper.run(job)

