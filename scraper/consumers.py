import asyncio
import json
import os
from pathlib import Path
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from companies.models import InsuranceCompany


class LogStreamConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_task = None
        self.closed = False

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
                "companies": companies
            }))

        elif action == "list_files":
            company = data.get("company")
            files = await self._get_files_list(company)
            await self.send(text_data=json.dumps({
                "type": "files_list",
                "company": company,
                "files": files
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

            filepath = Path(settings.BASE_DIR) / "logs" / company / log_file
            if not filepath.exists():
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Dosya bulunamadı: {log_file}"
                }))
                return

            if self.stream_task:
                self.stream_task.cancel()

            self.stream_task = asyncio.create_task(self._stream_file_loop(filepath))

        elif action == "stop_stream":
            if self.stream_task:
                self.stream_task.cancel()
                self.stream_task = None
            await self.send(text_data=json.dumps({
                "type": "stream_stopped"
            }))

    async def _get_companies_list(self):
        def _fetch():
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
            return sorted(list(codes))

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

    async def _stream_file_loop(self, filepath: Path):
        try:
            await self.send(text_data=json.dumps({
                "type": "stream_started",
                "file": filepath.name
            }))

            def _read_initial():
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(), f.tell()

            def _read_chunk(pos):
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    data = f.read()
                    return data, f.tell()

            content, pos = await asyncio.to_thread(_read_initial)
            if content:
                await self.send(text_data=json.dumps({
                    "type": "log_chunk",
                    "content": content
                }))

            while not self.closed:
                await asyncio.sleep(0.5)
                new_data, new_pos = await asyncio.to_thread(_read_chunk, pos)
                if new_data:
                    pos = new_pos
                    await self.send(text_data=json.dumps({
                        "type": "log_chunk",
                        "content": new_data
                    }))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self.closed:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Okuma hatası: {e}"
                }))
