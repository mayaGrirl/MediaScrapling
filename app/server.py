from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.platform.actions import enqueue
from app.platform.context import PlatformContext

PAGE = Path(__file__).with_name("console.html")
LOGS = Path(__file__).with_name("logs.html")


class CrawlIn(BaseModel):
    url: str
    keyword: str = ""
    cookie: str = ""


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

    @app.get("/api/logs")
    def list_logs(limit: int = 200) -> list[dict]:
        return ctx.store.list_logs(limit)

    @app.post("/api/jobs")
    def create_job(body: CrawlIn) -> dict:
        url = body.url.strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="url must start with http:// or https://")
        job = enqueue(ctx, url, body.keyword.strip(), body.cookie.strip())
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

    @app.get("/api/videos")
    def list_videos(limit: int = 50) -> list[dict]:
        return [item.model_dump() for item in ctx.store.list_videos(limit)]

    @app.delete("/api/videos/{video_id}")
    def delete_video(video_id: int) -> dict:
        ctx.store.delete_video(video_id)
        return {"id": video_id, "status": "deleted"}

    return app
