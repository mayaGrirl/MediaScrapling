"""Resolve a concrete public video URL with yt-dlp. No separate queue or database."""

from app.platform.models import Job, VideoItem


def run_resolve(job: Job) -> list[VideoItem]:
    try:
        return _extract(job)
    except Exception:
        if not job.proxy:
            raise
        job.proxy = None
        return _extract(job)


def _extract(job: Job) -> list[VideoItem]:
    import yt_dlp

    options = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        "no_warnings": True,
    }
    if job.proxy:
        options["proxy"] = job.proxy
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(job.url, download=False)
    if info is None:
        raise RuntimeError("yt-dlp returned no info")
    entries = info.get("entries") or [info]
    items: list[VideoItem] = []
    for entry in entries:
        if not entry:
            continue
        video_url = entry.get("url") or ""
        if not video_url:
            formats = entry.get("formats") or []
            for fmt in reversed(formats):
                if fmt.get("vcodec") not in {None, "none"} and fmt.get("url"):
                    video_url = fmt["url"]
                    break
        items.append(
            VideoItem(
                job_id=job.id,
                platform=job.platform or "resolve",
                source_url=str(entry.get("webpage_url") or job.url),
                title=str(entry.get("title") or ""),
                video_url=str(video_url),
                cover_url=str(entry.get("thumbnail") or ""),
                raw={"extractor": entry.get("extractor"), "id": entry.get("id")},
            )
        )
        if len(items) >= max(1, job.target_count):
            break
    if not items:
        raise RuntimeError("yt-dlp found no video")
    return items
