from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import ScrapeJob
from .runner import launch_job_async

STATUS_LABELS = {
    ScrapeJob.Status.PENDING: "warning",
    ScrapeJob.Status.RUNNING: "info",
    ScrapeJob.Status.SUCCESS: "success",
    ScrapeJob.Status.PARTIAL: "warning",
    ScrapeJob.Status.FAILED: "danger",
}


@admin.register(ScrapeJob)
class ScrapeJobAdmin(ModelAdmin):
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path("log-stream/", self.admin_site.admin_view(self.log_stream_view), name="scraper_log_stream"),
        ]
        return custom_urls + urls

    def log_stream_view(self, request):
        from django.shortcuts import render
        context = {
            **self.admin_site.each_context(request),
            "title": "Canlı Log Takibi (WebSocket Stream)",
        }
        return render(request, "admin/scraper/log_stream.html", context)

    list_display = (
        "id",

        "source_key",
        "company",
        "product_type",
        "city",
        "district",
        "status_badge",
        "pages_fetched",
        "result_count",
        "started_at",
        "finished_at",
    )
    list_filter = ("source_key", "status", "company", "product_type")
    readonly_fields = (
        "status",
        "triggered_by",
        "request_params",
        "pages_fetched",
        "created_count",
        "updated_count",
        "result_count",
        "error_message",
        "log",
        "log_file_path",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    )
    fields = (
        "source_key",
        "company",
        "product_type",
        "city",
        "district",
        "institution_type",
        "status",
        "triggered_by",
        "request_params",
        "pages_fetched",
        "created_count",
        "updated_count",
        "result_count",
        "error_message",
        "log",
        "log_file_path",
        "started_at",
        "finished_at",
    )
    actions = ["run_now"]

    @display(description="Durum", label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status

    @admin.action(description="Şimdi çalıştır (Run now)")
    def run_now(self, request, queryset):
        started = 0
        skipped = 0
        for job in queryset:
            if job.status == ScrapeJob.Status.RUNNING:
                skipped += 1
                continue
            job.triggered_by = request.user
            job.status = ScrapeJob.Status.PENDING
            job.error_message = ""
            job.log = ""
            job.pages_fetched = 0
            job.created_count = 0
            job.updated_count = 0
            job.result_count = 0
            job.save()
            launch_job_async(job.pk)
            started += 1

        if started:
            self.message_user(request, f"{started} scrape işi arka planda başlatıldı.")
        if skipped:
            self.message_user(request, f"{skipped} iş zaten çalışıyordu, atlandı.")
