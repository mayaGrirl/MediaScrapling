"""Agent Reach channels that already expose a public read API."""

from urllib.request import Request, urlopen

from app.platform.models import Job, VideoItem


def run_reach(job: Job) -> list[VideoItem]:
    platform = job.platform or ""
    limit = max(1, job.target_count)
    if platform == "v2ex":
        from agent_reach.channels.v2ex import V2EXChannel

        channel = V2EXChannel()
        keyword = job.keyword.strip()
        rows = channel.get_node_topics(keyword, limit=limit) if keyword else channel.get_hot_topics(limit=limit)
        return _rows(job, rows, "title", "url")
    if platform == "xueqiu":
        from agent_reach.channels.xueqiu import XueqiuChannel

        rows = XueqiuChannel().get_hot_posts(limit=limit)
        return _rows(job, rows, "title", "url")
    if platform == "github":
        return [_github(job)]
    if platform == "rss":
        return _rss(job, limit)
    raise RuntimeError("这个 Agent Reach 渠道需要登录或单独的上游命令，当前入口只接了免登录的 V2EX、雪球、GitHub 和 RSS。")


def _rows(job: Job, rows: list, title_key: str, url_key: str) -> list[VideoItem]:
    items = []
    for row in rows:
        if not isinstance(row, dict) or row.get("error"):
            continue
        title = str(row.get(title_key) or row.get("text") or "")
        items.append(_item(job, title, str(row.get(url_key) or job.url), _plain(row)))
    if not items:
        raise RuntimeError("Agent Reach 没有返回内容")
    return items


def _plain(row: dict) -> dict:
    kept = {}
    for key, value in row.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            kept[key] = value[:500] if isinstance(value, str) else value
    return kept


def _item(job: Job, title: str, url: str, raw: dict) -> VideoItem:
    return VideoItem(
        job_id=job.id,
        platform=job.platform or "reach",
        source_url=str(url or job.url),
        title=str(title or ""),
        raw={"via": "agent-reach", **raw},
    )


def _github(job: Job) -> VideoItem:
    from urllib.parse import urlparse

    parts = [part for part in urlparse(job.url).path.split("/") if part]
    if len(parts) < 2:
        raise RuntimeError("GitHub 地址需要是 https://github.com/用户/仓库")
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    api = f"https://api.github.com/repos/{parts[0]}/{repo}"
    request = Request(api, headers={"User-Agent": "MediaScrapling", "Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=20) as response:
        import json

        data = json.loads(response.read().decode("utf-8"))
    return _item(job, data.get("full_name") or "", data.get("html_url") or job.url, {"description": data.get("description") or ""})


def _rss(job: Job, limit: int) -> list[VideoItem]:
    import feedparser

    feed = feedparser.parse(job.url)
    entries = feed.entries[:limit]
    if not entries:
        raise RuntimeError("RSS 源没有条目")
    return [
        _item(job, entry.get("title", ""), entry.get("link", job.url), {"summary": str(entry.get("summary") or "")[:500]})
        for entry in entries
    ]
