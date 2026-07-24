import asyncio
import json
from pathlib import Path
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from companies.models import InsuranceCompany

# Büyük log dosyalarında tüm dosyayı tek seferde okumak (overflow / donma riski)
# yerine sadece dosyanın son kısmını okuyoruz; kullanıcı yukarı kaydırdıkça
# önceki bölümler "load_more" ile parça parça çekilir.
TAIL_INITIAL_BYTES = 200_000  # ~ilk açılışta okunacak son kısım
LOAD_MORE_CHUNK_BYTES = 150_000  # her "load_more" isteğinde geriye doğru okunacak parça


class LogStreamConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_task = None
        self.closed = False
        self.current_filepath: Path | None = None
        # Şu an ekranda görünen aralığın dosya içindeki sınırları (byte offset)
        self.earliest_loaded_pos = 0
        self.tail_pos = 0
        self.loading_more = False

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.is_staff:
            await self.close(code=4003)
            return
        await self.accept()

    async def disconnect(self, close_code):
        self.closed = True
        if self.stream_task:
            self.stream_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")

        if action == "list_companies":
            companies = await self._get_companies_list()
            await self.send(text_data=json.dumps({
                "type": "companies_list",
                "companies": companies,
            }))

        elif action == "list_files":
            company = data.get("company")
            files = await self._get_files_list(company)
            await self.send(text_data=json.dumps({
                "type": "files_list",
                "company": company,
                "files": files,
            }))

        elif action == "start_stream":
            company = data.get("company")
            log_file = data.get("log_file")
            if not company or not log_file:
                return

            # Güvenlik kontrolü (path traversal engelleme)
            if ".." in company or "/" in company or "\\" in company:
                return
            if ".." in log_file or "/" in log_file or "\\" in log_file:
                return

            filepath = (Path(settings.BASE_DIR) / "logs" / company / log_file).resolve()
            logs_root = (Path(settings.BASE_DIR) / "logs").resolve()
            if logs_root not in filepath.parents or not filepath.exists():
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Dosya bulunamadı: {log_file}",
                }))
                return

            if self.stream_task:
                self.stream_task.cancel()

            self.stream_task = asyncio.create_task(self._stream_file_loop(filepath))

        elif action == "load_more":
            if self.loading_more or not self.current_filepath:
                return
            self.loading_more = True
            try:
                await self._load_more_chunk()
            finally:
                self.loading_more = False

        elif action == "stop_stream":
            if self.stream_task:
                self.stream_task.cancel()
                self.stream_task = None
            await self.send(text_data=json.dumps({
                "type": "stream_stopped",
            }))

    async def _get_companies_list(self):
        def _fetch():
            from .models import ScrapeJob

            # Hem DB'deki şirket kodlarını hem de logs klasörü altındaki mevcut klasörleri birleştir
            codes = set()
            try:
                for c in InsuranceCompany.objects.values_list("code", flat=True):
                    if c:
                        codes.add(c.upper())
            except Exception:
                pass

            logs_dir = Path(settings.BASE_DIR) / "logs"
            if logs_dir.exists():
                for d in logs_dir.iterdir():
                    if d.is_dir():
                        codes.add(d.name.upper())

            if not codes:
                codes.add("AXA")

            # Her şirket için çalışan (RUNNING) bir job var mı bak — varsa PID + log dosyasını ekle
            running_by_company = {}
            try:
                running_jobs = ScrapeJob.objects.filter(
                    status=ScrapeJob.Status.RUNNING,
                ).select_related("company").order_by("-started_at")
                for job in running_jobs:
                    code = (job.company.code.upper() if job.company_id else job.source_key.upper())
                    if code in running_by_company:
                        continue  # aynı şirket için en yeni RUNNING job'ı al
                    log_file = Path(job.log_file_path).name if job.log_file_path else ""
                    running_by_company[code] = {
                        "job_id": job.pk,
                        "pid": job.pid,
                        "source_key": job.source_key,
                        "log_file": log_file,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                    }
            except Exception:
                pass

            result = []
            for code in sorted(codes):
                result.append({
                    "code": code,
                    "running": running_by_company.get(code),
                })
            return result

        return await asyncio.to_thread(_fetch)

    async def _get_files_list(self, company: str):
        if not company or ".." in company or "/" in company or "\\" in company:
            return []

        def _fetch():
            log_dir = Path(settings.BASE_DIR) / "logs" / company
            if not log_dir.exists() or not log_dir.is_dir():
                return []
            result = []
            for f in log_dir.glob("*.log"):
                if f.is_file():
                    stat = f.stat()
                    result.append({
                        "filename": f.name,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    })
            result.sort(key=lambda x: x["mtime"], reverse=True)
            return result

        return await asyncio.to_thread(_fetch)

    @staticmethod
    def _align_to_line_start(filepath: Path, pos: int) -> int:
        """pos'tan itibaren bir sonraki satır başlangıcına hizalar (satırın ortasından
        başlamayı önlemek için). pos=0 ise zaten hizalıdır."""
        if pos <= 0:
            return 0
        with open(filepath, "rb") as f:
            f.seek(pos)
            f.readline()  # yarım kalan satırı atla
            return f.tell()

    async def _stream_file_loop(self, filepath: Path):
        try:
            self.current_filepath = filepath
            file_size = filepath.stat().st_size
            start_pos = max(0, file_size - TAIL_INITIAL_BYTES)

            def _read_tail(start):
                aligned = self._align_to_line_start(filepath, start)
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(aligned)
                    data = f.read()
                    return data, aligned, f.tell()

            content, earliest_pos, tail_pos = await asyncio.to_thread(_read_tail, start_pos)
            self.earliest_loaded_pos = earliest_pos
            self.tail_pos = tail_pos

            await self.send(text_data=json.dumps({
                "type": "stream_started",
                "file": filepath.name,
                "has_more": self.earliest_loaded_pos > 0,
            }))

            if content:
                await self.send(text_data=json.dumps({
                    "type": "log_chunk",
                    "content": content,
                }))

            while not self.closed:
                await asyncio.sleep(0.5)

                def _read_new(pos):
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos)
                        data = f.read()
                        return data, f.tell()

                new_data, new_pos = await asyncio.to_thread(_read_new, self.tail_pos)
                if new_data:
                    self.tail_pos = new_pos
                    await self.send(text_data=json.dumps({
                        "type": "log_chunk",
                        "content": new_data,
                    }))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self.closed:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Okuma hatası: {e}",
                }))

    async def _load_more_chunk(self):
        """Kullanıcı terminalde yukarı kaydırdığında, o an yüklü olan en eski
        pozisyondan geriye doğru bir parça daha okuyup başa ekler (prepend)."""
        filepath = self.current_filepath
        if not filepath or self.earliest_loaded_pos <= 0:
            await self.send(text_data=json.dumps({
                "type": "log_chunk_prepend",
                "content": "",
                "has_more": False,
            }))
            return

        def _read_prev():
            new_start = max(0, self.earliest_loaded_pos - LOAD_MORE_CHUNK_BYTES)
            aligned = self._align_to_line_start(filepath, new_start)
            # Hizalama, hedeflenen aralığın içine denk gelmezse (satır çok uzunsa)
            # en azından bir öncekinden ileri gitmemesini garanti et.
            if aligned >= self.earliest_loaded_pos and new_start > 0:
                aligned = new_start
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(aligned)
                data = f.read(self.earliest_loaded_pos - aligned)
                return data, aligned

        content, new_earliest_pos = await asyncio.to_thread(_read_prev)
        self.earliest_loaded_pos = new_earliest_pos

        await self.send(text_data=json.dumps({
            "type": "log_chunk_prepend",
            "content": content,
            "has_more": self.earliest_loaded_pos > 0,
        }))
