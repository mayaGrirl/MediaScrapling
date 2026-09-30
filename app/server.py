from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.platform.actions import enqueue
from app.platform.context import PlatformContext

PAGE = Path(__file__).with_name("console.html")
LOGS = Path(__file__).with_name("logs.html")


class CrawlIn(BaseModel):
    url: str
    keyword: str = ""
    cookie: str = ""
    limit: int = 10


def create_app() -> FastAPI:
    app = FastAPI(title="MediaScrapling")
    ctx = PlatformContext.open()
    ctx.store.create_tables()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(PAGE)

    @app.get("/logs")
    def logs_page() -> FileResponse:
        return FileResponse(LOGS)

    @app.delete("/api/logs")
    def clear_logs() -> dict:
        ctx.store.clear_logs()
        return {"status": "cleared"}

    @app.get("/api/logs")
    def list_logs(limit: int = 200) -> list[dict]:
        return ctx.store.list_logs(limit)

    @app.post("/api/jobs")
    def create_job(body: CrawlIn) -> dict:
        url = body.url.strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="url must start with http:// or https://")
        job = enqueue(ctx, url, body.keyword.strip(), body.cookie.strip(), body.limit)
        return job.model_dump()

    @app.get("/api/jobs")
    def list_jobs(limit: int = 50) -> list[dict]:
        return [job.model_dump() for job in ctx.store.list_jobs(limit)]

    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str) -> dict:
        ctx.queue.remove(job_id)
        job = ctx.store.get_job(job_id)
        if job is not None and job.status == "running":
            job.status = "cancelled"
            job.error = "已在页面停止"
            ctx.store.save_job(job)
            return job.model_dump()
        ctx.store.delete_job(job_id)
        return {"id": job_id, "status": "deleted"}

    @app.get("/api/media")
    def media_proxy(url: str) -> Response:
        host = urlparse(url).hostname or ""
        if host != "douyinpic.com" and not host.endswith(".douyinpic.com"):
            raise HTTPException(status_code=400, detail="unsupported media host")
        request = Request(url, headers={"Referer": "https://www.douyin.com/", "User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=20) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "image/jpeg")
        return Response(content=body, media_type=content_type.split(";")[0])

    @app.get("/api/proxies")
    def list_proxies() -> dict:
        proxies = ctx.proxies.list()
        return {"count": len(proxies)}

    @app.get("/api/videos")
    def list_videos(limit: int = 50) -> list[dict]:
        return [item.model_dump() for item in ctx.store.list_videos(limit)]

    @app.delete("/api/videos/{video_id}")
    def delete_video(video_id: int) -> dict:
        ctx.store.delete_video(video_id)
        return {"id": video_id, "status": "deleted"}

    return app
