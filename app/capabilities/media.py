"""Platform capability: one MediaCrawler invocation per job, driven by the platform."""

import json
import subprocess
import sys
from pathlib import Path

from app.platform.context import PlatformContext
from app.platform.models import Job, VideoItem


class MediaCrawlerUnavailable(RuntimeError):
    pass


def command(home: Path, job: Job) -> list[str]:
    python = home / (".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python")
    executable = str(python if python.exists() else Path(sys.executable))
    args = [
        executable,
        "main.py",
        "--platform",
        job.platform or "",
        "--type",
        "detail" if job.url else "search",
        "--lt",
        "qrcode",
    ]
    return args


def run_media(job: Job, ctx: PlatformContext) -> tuple[VideoItem, str]:
    home = Path(ctx.settings.mediacrawler_home)
    if not (home / "main.py").exists():
        raise MediaCrawlerUnavailable(
            f"MediaCrawler not found at {home}. Clone https://github.com/NanmiCoder/MediaCrawler there."
        )
    proxy = job.proxy or ctx.proxies.acquire()
    cookie = ctx.sessions.get(job.cookie_key or (job.platform or "")) if job.platform or job.cookie_key else None
    env = dict(**_base_env())
    if proxy:
        env["CRAWLER_PROXY"] = proxy
    if cookie:
        env["CRAWLER_COOKIE"] = cookie
    env["CRAWLER_KEYWORD"] = job.keyword or job.url
    env["CRAWLER_URL"] = job.url
    completed = subprocess.run(
        command(home, job),
        cwd=home,
        env=env,
        capture_output=True,
        text=True,
        timeout=ctx.settings.media_timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"MediaCrawler exited {completed.returncode}")
    payload = _read_result(home, completed.stdout)
    html = str(payload.get("html") or "")
    item = VideoItem(
        job_id=job.id,
        platform=job.platform or "media",
        source_url=str(payload.get("url") or job.url),
        title=str(payload.get("title") or ""),
        video_url=str(payload.get("video_url") or ""),
        cover_url=str(payload.get("cover_url") or ""),
        raw=payload,
    )
    return item, html


def _base_env() -> dict[str, str]:
    import os

    return dict(os.environ)


def _read_result(home: Path, stdout: str) -> dict:
    marker = home / "data" / "platform_result.json"
    if marker.exists():
        return json.loads(marker.read_text(encoding="utf-8"))
    text = stdout.strip()
    if text.startswith("{"):
        return json.loads(text.splitlines()[-1])
    return {"stdout": text}
