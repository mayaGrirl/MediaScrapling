"""Single worker loop for both capabilities."""

import logging

from app.capabilities.media import MediaCrawlerUnavailable, run_media
from app.capabilities.resolve import run_resolve
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
        if job.capability == "resolve":
            items = run_resolve(job)
            html = ""
        elif job.capability == "media":
            if not job.proxy:
                _log(ctx, job.id, "info", "代理池暂无可用代理，本次直连")
            items, html = run_media(job, ctx)
            items = [enrich_with_web(item, html) for item in items]
        else:
            item, html = run_web(job, ctx)
            items = [item]
            children = promote_known_links(html, job.url, ctx, job)
            for child in children:
                ctx.store.save_job(child)
                _log(ctx, job.id, "info", f"发现已知站点，已入队 {child.platform} {child.url}")
        current = ctx.store.get_job(job.id)
        if current is None or current.status == "cancelled":
            _log(ctx, job.id, "warning", "任务已停止，丢弃结果")
            return job
        for item in items:
            if html and job.capability != "media":
                item.raw = {**item.raw, "preview_html": html[:20000]}
            ctx.store.save_video(item)
        job.status = "done"
        job.error = ""
        _log(ctx, job.id, "info", f"完成 {len(items)}/{job.target_count} 条")
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


def _start_proxy_refresh(ctx: PlatformContext) -> None:
    import threading

    from app.platform.proxy_refresh import refresh

    def loop() -> None:
        while True:
            try:
                count = refresh(ctx.proxies)
                _log(ctx, "", "info", f"代理池更新，可用 {count} 个")
            except Exception:
                log.exception("proxy refresh failed")
            threading.Event().wait(300)

    threading.Thread(target=loop, name="proxy-refresh", daemon=True).start()


def _log(ctx: PlatformContext, job_id: str, level: str, message: str) -> None:
    getattr(log, level if level != "error" else "error")("%s %s", job_id, message)
    ctx.store.add_log(job_id, level, message)


def serve(ctx: PlatformContext, once: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ctx.store.create_tables()
    _start_proxy_refresh(ctx)
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
