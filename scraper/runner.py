import threading

from django.db import close_old_connections


def launch_job_async(job_id: int) -> threading.Thread:
    """Runs a ScrapeJob in a background thread so the admin request doesn't block.

    No Celery/Redis: each thread must close/reopen its own DB connections since it
    doesn't inherit Django's per-request connection lifecycle.
    """

    def _target():
        close_old_connections()
        try:
            from .models import ScrapeJob
            from .services import ScrapeJobRunner

            job = ScrapeJob.objects.get(pk=job_id)
            ScrapeJobRunner().run(job)
        finally:
            close_old_connections()

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    return thread
