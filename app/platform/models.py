from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Capability = Literal["media", "web"]


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


def classify(url: str) -> tuple[Capability, str | None]:
    platform = platform_for_url(url)
    if platform:
        return "media", platform
    return "web", None
