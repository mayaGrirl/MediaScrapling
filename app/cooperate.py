"""How the two capabilities hand work to each other inside one platform."""

from app.capabilities.web import links, parse_html
from app.platform.context import PlatformContext
from app.platform.models import Job, VideoItem, classify


def enrich_with_web(item: VideoItem, html: str) -> VideoItem:
    """Platform crawl returned HTML; Scrapling fills empty title, video, and cover."""
    if not html:
        return item
    fields = parse_html(html)
    data = item.model_dump()
    for key in ("title", "video_url", "cover_url"):
        if not data.get(key) and fields.get(key):
            data[key] = fields[key]
    data["raw"] = {**item.raw, "parsed_by": "scrapling"}
    return VideoItem(**data)


def promote_known_links(html: str, base_url: str, ctx: PlatformContext, parent: Job) -> list[Job]:
    """Web crawl found a known platform URL; enqueue a media job on the same queue."""
    created: list[Job] = []
    for url in links(html, base_url):
        capability, platform = classify(url)
        if capability != "media":
            continue
        job = Job(
            url=url,
            capability="media",
            platform=platform,
            proxy=parent.proxy,
            cookie_key=platform,
        )
        ctx.queue.push(job)
        created.append(job)
    return created
