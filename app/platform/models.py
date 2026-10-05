from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Capability = Literal["media", "web", "resolve", "reach"]


class Job(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    url: str
    keyword: str = ""
    capability: Capability = "web"
    platform: str | None = None
    status: str = "pending"
    error: str = ""
    proxy: str | None = None
    cookie_key: str | None = None
    target_count: int = 1


class VideoItem(BaseModel):
    job_id: str
    platform: str
    source_url: str
    title: str = ""
    video_url: str = ""
    cover_url: str = ""
    raw: dict = Field(default_factory=dict)


HOST_PLATFORM: dict[str, str] = {
    "xiaohongshu.com": "xhs",
    "www.xiaohongshu.com": "xhs",
    "douyin.com": "dy",
    "www.douyin.com": "dy",
    "v.douyin.com": "dy",
    "kuaishou.com": "ks",
    "www.kuaishou.com": "ks",
    "bilibili.com": "bili",
    "www.bilibili.com": "bili",
    "b23.tv": "bili",
    "weibo.com": "wb",
    "www.weibo.com": "wb",
    "m.weibo.cn": "wb",
    "tieba.baidu.com": "tieba",
    "zhihu.com": "zhihu",
    "www.zhihu.com": "zhihu",
}


def platform_for_url(url: str) -> str | None:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    if host in HOST_PLATFORM:
        return HOST_PLATFORM[host]
    for suffix, name in HOST_PLATFORM.items():
        if host.endswith("." + suffix) or host == suffix:
            return name
    return None


RESOLVE_HOSTS: dict[str, str] = {
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "m.youtube.com": "youtube",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
    "vm.tiktok.com": "tiktok",
    "vimeo.com": "vimeo",
    "www.vimeo.com": "vimeo",
    "twitter.com": "twitter",
    "www.twitter.com": "twitter",
    "x.com": "twitter",
}


def _host(url: str) -> str:
    from urllib.parse import urlparse

    return (urlparse(url).hostname or "").lower()


def _path(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path.lower().rstrip("/")


def classify(url: str) -> tuple[Capability, str | None]:
    host = _host(url)
    for suffix, name in RESOLVE_HOSTS.items():
        if host == suffix or host.endswith("." + suffix):
            return "resolve", name
    if host in {"v2ex.com", "www.v2ex.com"} or host.endswith(".v2ex.com"):
        return "reach", "v2ex"
    if host in {"xueqiu.com", "www.xueqiu.com"}:
        return "reach", "xueqiu"
    if host in {"github.com", "www.github.com"}:
        return "reach", "github"
    path = _path(url)
    if path.endswith(("/feed", "/rss", ".rss", ".xml", ".atom", "/atom")):
        return "reach", "rss"
    platform = platform_for_url(url)
    if platform in {"dy", "bili", "ks"} and "/video/" in url:
        return "resolve", platform
    if platform:
        return "media", platform
    return "web", None
