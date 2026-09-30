from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.platform.actions import enqueue
from app.platform.context import PlatformContext

PAGE = Path(__file__).with_name("console.html")


class CrawlIn(BaseModel):
    url: str
    keyword: str = ""


class ProxyIn(BaseModel):
    proxy_url: str


def create_app() -> FastAPI:
    app = FastAPI(title="MediaScrapling")
    ctx = PlatformContext.open()
    ctx.store.create_tables()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(PAGE)

    @app.post("/api/jobs")
    def create_job(body: CrawlIn) -> dict:
        url = body.url.strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="url must start with http:// or https://")
        job = enqueue(ctx, url, body.keyword.strip())
        return job.model_dump()

    @app.get("/api/jobs")
    def list_jobs(limit: int = 50) -> list[dict]:
        return [job.model_dump() for job in ctx.store.list_jobs(limit)]

    @app.get("/api/proxies")
    def list_proxies() -> list[str]:
        return ctx.proxies.list()

    @app.post("/api/proxies")
    def add_proxy(body: ProxyIn) -> dict:
        ctx.proxies.add(body.proxy_url.strip())
        return {"proxies": ctx.proxies.list()}

    return app
