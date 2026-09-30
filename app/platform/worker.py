"""Single worker loop for both capabilities."""

import logging

from app.capabilities.media import MediaCrawlerUnavailable, run_media
from app.capabilities.web import run_web
from app.cooperate import enrich_with_web, promote_known_links
from app.platform.context import PlatformContext
from app.platform.models import Job

log = logging.getLogger("platform")


def execute(job: Job, ctx: PlatformContext) -> Job:
    current = ctx.store.get_job(job.id)
    if current is not None and current.status == "cancelled":
        return job
    job.proxy = job.proxy or ctx.proxies.acquire()
    if job.capability == "media" and job.platform and not job.cookie_key:
        job.cookie_key = job.platform
    job.status = "running"
    ctx.store.save_job(job)
    _log(ctx, job.id, "info", f"开始 {job.capability} {job.platform or '-'} {job.url}")
    try:
        if job.capability == "media":
            item, html = run_media(job, ctx)
            item = enrich_with_web(item, html)
        else:
            item, html = run_web(job, ctx)
            children = promote_known_links(html, job.url, ctx, job)
            for child in children:
                ctx.store.save_job(child)
                _log(ctx, job.id, "info", f"发现已知站点，已入队 {child.platform} {child.url}")
        if html:
            item.raw = {**item.raw, "preview_html": html[:20000]}
        current = ctx.store.get_job(job.id)
        if current is None or current.status == "cancelled":
            _log(ctx, job.id, "warning", "任务已停止，丢弃结果")
            return job
        ctx.store.save_video(item)
        job.status = "done"
        job.error = ""
        _log(ctx, job.id, "info", f"完成 title={item.title or '-'} video={item.video_url or '-'} cover={item.cover_url or '-'}")
    except MediaCrawlerUnavailable as exc:
        job.status = "failed"
        job.error = str(exc)
        _log(ctx, job.id, "error", str(exc))
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        _log(ctx, job.id, "error", str(exc))
        log.exception("job %s failed", job.id)
    ctx.store.save_job(job)
    return job


def _log(ctx: PlatformContext, job_id: str, level: str, message: str) -> None:
    getattr(log, level if level != "error" else "error")("%s %s", job_id, message)
    ctx.store.add_log(job_id, level, message)


def serve(ctx: PlatformContext, once: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ctx.store.create_tables()
    _log(ctx, "", "info", "采集进程已启动")
    for job in ctx.store.list_jobs(200):
        if job.status == "running":
            job.status = "pending"
            job.error = ""
            ctx.store.save_job(job)
        if job.status != "pending":
            continue
        ctx.queue.remove(job.id)
        ctx.queue.push(job)
        _log(ctx, job.id, "info", f"继续排队 {job.capability} {job.platform or '-'} {job.url}")
    while True:
        try:
            job = ctx.queue.pop(timeout=2 if once else 5)
        except Exception:
            log.exception("queue pop failed")
            if once:
                return
            continue
        if job is None:
            if once:
                return
            continue
        execute(job, ctx)
        if once:
            return
