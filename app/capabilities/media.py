"""Platform capability: one MediaCrawler invocation per job, driven by the platform."""

import json
import subprocess
import sys
from pathlib import Path

from app.platform.context import PlatformContext
from app.platform.models import Job, VideoItem


class MediaCrawlerUnavailable(RuntimeError):
    pass


def command(home: Path, job: Job, save_dir: Path, cookie: str = "") -> list[str]:
    home = Path(home).resolve()
    save_dir = Path(save_dir).resolve()
    python = home / (".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python")
    executable = str(python if python.exists() else Path(sys.executable))
    mode, target = _mode(job)
    args = [
        executable,
        str(Path(__file__).with_name("run_mediacrawler.py")),
        str(home),
        "--platform",
        job.platform or "",
        "--type",
        mode,
        "--lt",
        "cookie" if cookie else "qrcode",
        "--save_data_option",
        "json",
        "--save_data_path",
        str(save_dir),
        "--get_comment",
        "false",
        "--get_sub_comment",
        "false",
        "--crawler_max_notes_count",
        str(max(1, job.target_count)),
        "--headless",
        "false",
    ]
    if mode == "detail":
        args.extend(["--specified_id", target])
    else:
        args.extend(["--keywords", target])
    if cookie:
        args.extend(["--cookies", cookie])
    return args


def run_media(job: Job, ctx: PlatformContext) -> tuple[list[VideoItem], str]:
    home = Path(ctx.settings.mediacrawler_home)
    if not (home / "main.py").exists():
        raise MediaCrawlerUnavailable(
            f"MediaCrawler not found at {home}. Clone https://github.com/NanmiCoder/MediaCrawler there."
        )
    save_dir = Path("data") / "media_jobs" / job.id
    save_dir.mkdir(parents=True, exist_ok=True)
    cookie = ""
    if job.cookie_key:
        cookie = ctx.sessions.get(job.cookie_key) or ""
    log_path = save_dir / "mediacrawler.log"
    completed = None
    log_text = ""
    for _attempt in range(2):
        with log_path.open("w", encoding="utf-8") as handle:
            completed = subprocess.run(
                command(home, job, save_dir, cookie),
                cwd=home,
                env=_base_env(job),
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=ctx.settings.media_timeout_seconds,
                check=False,
            )
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        if completed.returncode == 0 or "Execution context was destroyed" not in log_text:
            break
    if completed is None or completed.returncode != 0:
        raise RuntimeError(_explain(log_text) or f"MediaCrawler exited {completed.returncode}")
    payloads = _read_results(save_dir)[: max(1, job.target_count)]
    if not payloads:
        raise RuntimeError(_explain(log_text) or "MediaCrawler finished without a content file.")
    html = str(payloads[0].get("html") or "")
    items = [
        VideoItem(
            job_id=job.id,
            platform=job.platform or "media",
            source_url=str(payload.get("aweme_url") or payload.get("url") or job.url),
            title=str(payload.get("title") or payload.get("desc") or ""),
            video_url=str(payload.get("video_download_url") or payload.get("video_url") or ""),
            cover_url=str(payload.get("cover_url") or ""),
            raw=payload,
        )
        for payload in payloads
    ]
    return items, html


def _mode(job: Job) -> tuple[str, str]:
    url = job.url or ""
    if "/video/" in url or "/note/" in url:
        return "detail", url
    keyword = (job.keyword or "").strip()
    if keyword:
        return "search", keyword
    return "search", "抖音"


def _base_env(job: Job) -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["MEDIASCRAPLING_LIMIT"] = str(max(1, job.target_count))
    if job.proxy:
        env["MEDIASCRAPLING_PROXY"] = job.proxy
    return env


def _read_results(save_dir: Path) -> list[dict]:
    files = sorted(save_dir.rglob("*contents*.json"), key=lambda path: path.stat().st_mtime)
    if not files:
        return []
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _explain(text: str) -> str:
    if "关键词搜索页没有视频" in text:
        return "按关键词打开了搜索页，但页面上没有视频。这次没有改用推荐流，所以结果里不会混入无关视频。"
    if "qrcode not found" in text or "login dialog box does not pop up" in text:
        return "抖音没有出现登录二维码，这次没有抓到视频。请在弹出的浏览器里手动登录，或在新建任务时填入已登录的 Cookie 后再入队。"
    if "Executable doesn't exist" in text:
        return "浏览器组件还没安装完成。请稍后重新入队。"
    return _tail(text)


def _tail(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]
