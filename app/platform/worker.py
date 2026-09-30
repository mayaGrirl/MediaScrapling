"""Single worker loop for both capabilities."""

import logging

from app.capabilities.media import MediaCrawlerUnavailable, run_media
from app.capabilities.web import run_web
from app.cooperate import enrich_with_web, promote_known_links
from app.platform.context import PlatformContext
from app.platform.models import Job

log = logging.getLogger("platform")


def execute(job: Job, ctx: PlatformContext) -> Job:
    job.proxy = job.proxy or ctx.proxies.acquire()
    if job.capability == "media" and job.platform and not job.cookie_key:
        job.cookie_key = job.platform
    job.status = "running"
    ctx.store.save_job(job)
    try:
        if job.capability == "media":
            item, html = run_media(job, ctx)
            item = enrich_with_web(item, html)
        else:
            item, html = run_web(job, ctx)
            promote_known_links(html, job.url, ctx, job)
        ctx.store.save_video(item)
        job.status = "done"
        job.error = ""
    except MediaCrawlerUnavailable as exc:
        job.status = "failed"
        job.error = str(exc)
        log.warning("%s", exc)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        log.exception("job %s failed", job.id)
    ctx.store.save_job(job)
    return job


def serve(ctx: PlatformContext, once: bool = False) -> None:
    ctx.store.create_tables()
    while True:
        job = ctx.queue.pop(timeout=2 if once else 5)
        if job is None:
            if once:
                return
            continue
        execute(job, ctx)
        if once:
            return
