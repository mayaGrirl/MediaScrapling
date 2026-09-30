from app.platform.context import PlatformContext
from app.platform.models import Job, classify


def enqueue(ctx: PlatformContext, url: str, keyword: str = "") -> Job:
    ctx.store.create_tables()
    capability, platform = classify(url)
    job = Job(url=url, keyword=keyword, capability=capability, platform=platform, cookie_key=platform)
    ctx.queue.push(job)
    ctx.store.save_job(job)
    return job
