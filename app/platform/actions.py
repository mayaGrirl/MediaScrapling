from app.platform.context import PlatformContext
from app.platform.models import Job, classify


def enqueue(ctx: PlatformContext, url: str, keyword: str = "", cookie: str = "") -> Job:
    ctx.store.create_tables()
    capability, platform = classify(url)
    job = Job(url=url, keyword=keyword, capability=capability, platform=platform, cookie_key=platform)
    if cookie and platform:
        ctx.sessions.put(platform, cookie)
    ctx.store.save_job(job)
    ctx.queue.push(job)
    ctx.store.add_log(job.id, "info", f"已入队 {capability} {platform or '-'} {url}")
    return job
