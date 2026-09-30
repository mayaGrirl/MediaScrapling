from app.capabilities.media import command
from app.cooperate import enrich_with_web, promote_known_links
from app.platform.models import Job, VideoItem, classify
from pathlib import Path


HTML = """
<html><head>
<title>Demo</title>
<meta property="og:image" content="https://cdn.example/cover.jpg"/>
</head><body>
<video src="https://cdn.example/a.mp4"></video>
<a href="https://www.bilibili.com/video/BV1xx">bili</a>
<a href="https://example.com/other">other</a>
</body></html>
"""


def test_classify_known_and_unknown():
    capability, platform = classify("https://example.com/watch")
    assert capability == "web"
    assert platform is None
    capability, platform = classify("https://www.youtube.com/watch?v=abc")
    assert capability == "resolve"
    assert platform == "youtube"
    capability, platform = classify("https://www.bilibili.com/video/BV1")
    assert capability == "resolve"
    assert platform == "bili"
    capability, platform = classify("https://www.douyin.com/")
    assert capability == "media"
    assert platform == "dy"


def test_media_command_shape():
    job = Job(url="https://www.douyin.com/video/1", capability="media", platform="dy")
    args = command(Path("third_party/MediaCrawler"), job, Path("data/media_jobs/demo"))
    assert "run_mediacrawler.py" in args[1]
    assert args[args.index("--platform") + 1] == "dy"
    assert args[args.index("--type") + 1] == "detail"
    assert args[args.index("--specified_id") + 1] == job.url

    home = Job(url="https://www.douyin.com/", capability="media", platform="dy", keyword="")
    args = command(Path("third_party/MediaCrawler"), home, Path("data/media_jobs/demo"))
    assert args[args.index("--type") + 1] == "search"
    assert args[args.index("--keywords") + 1] == "抖音"


def test_html_enrich_uses_parser():
    item = VideoItem(job_id="j1", platform="bili", source_url="https://www.bilibili.com/video/BV1")
    enriched = enrich_with_web(item, HTML)
    assert enriched.title == "Demo"
    assert enriched.video_url == "https://cdn.example/a.mp4"
    assert enriched.cover_url == "https://cdn.example/cover.jpg"
    assert enriched.raw["parsed_by"] == "scrapling"


class _Queue:
    def __init__(self):
        self.jobs = []

    def push(self, job):
        self.jobs.append(job)


class _Ctx:
    def __init__(self):
        self.queue = _Queue()


def test_known_link_becomes_media_job():
    parent = Job(url="https://example.com", capability="web")
    created = promote_known_links(HTML, parent.url, _Ctx(), parent)
    assert len(created) == 1
    assert created[0].capability == "resolve"
    assert created[0].platform == "bili"
    assert created[0].url.startswith("https://www.bilibili.com/")
