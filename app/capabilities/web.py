"""Web capability: Scrapling parses HTML and can fetch a page inside the platform process."""

from scrapling.parser import Selector

from app.platform.context import PlatformContext
from app.platform.models import Job, VideoItem


def parse_html(html: str) -> dict[str, str]:
    page = Selector(html)
    title = _first(page, "title") or _meta(page, "og:title")
    video = _attr(page, "video", "src") or _attr(page, "source", "src") or _meta(page, "og:video")
    cover = _meta(page, "og:image")
    return {"title": title, "video_url": video, "cover_url": cover}


def links(html: str, base_url: str) -> list[str]:
    from urllib.parse import urljoin

    page = Selector(html)
    found: list[str] = []
    for node in page.css("a"):
        href = node.attrib.get("href") if hasattr(node, "attrib") else None
        if href is None and hasattr(node, "get"):
            href = node.get("href")
        if not href:
            continue
        found.append(urljoin(base_url, href))
    return found


def run_web(job: Job, ctx: PlatformContext) -> tuple[VideoItem, str]:
    """Fetch with Scrapling when a live page is required. Tests call parse_html directly."""
    from scrapling.fetchers import Fetcher

    proxy = job.proxy or ctx.proxies.acquire()
    cookie = ctx.sessions.get(job.cookie_key) if job.cookie_key else None
    kwargs: dict = {}
    if proxy:
        kwargs["proxy"] = proxy
    if cookie:
        kwargs["headers"] = {"Cookie": cookie}
    page = Fetcher.get(job.url, **kwargs)
    html = getattr(page, "html_content", None) or getattr(page, "body", "") or str(page)
    fields = parse_html(html if isinstance(html, str) else "")
    item = VideoItem(job_id=job.id, platform="web", source_url=job.url, raw={"proxy": proxy}, **fields)
    return item, html if isinstance(html, str) else ""


def _first(page, selector: str) -> str:
    nodes = page.css(selector)
    if not nodes:
        return ""
    node = nodes[0]
    text = getattr(node, "text", None)
    if text:
        return str(text).strip()
    if hasattr(node, "get"):
        return str(node.get() or "").strip()
    return str(node).strip()


def _attr(page, selector: str, name: str) -> str:
    nodes = page.css(selector)
    if not nodes:
        return ""
    node = nodes[0]
    attrib = getattr(node, "attrib", None) or {}
    if name in attrib:
        return str(attrib[name])
    if hasattr(node, "get"):
        value = node.get(name)
        return str(value or "")
    return ""


def _meta(page, prop: str) -> str:
    nodes = page.css(f'meta[property="{prop}"], meta[name="{prop}"]')
    if not nodes:
        return ""
    node = nodes[0]
    attrib = getattr(node, "attrib", None) or {}
    return str(attrib.get("content") or "")
