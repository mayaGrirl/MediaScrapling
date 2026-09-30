"""Keep a small pool of working public proxies and drop the dead ones."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.request import ProxyHandler, Request, build_opener, urlopen

from app.platform.proxy import ProxyPool

log = logging.getLogger("platform.proxy")

POOL_SIZE = 20
CHECK_URL = "http://www.gstatic.com/generate_204"
SOURCES = (
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
)
_ADDRESS = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}")


def refresh(pool: ProxyPool) -> int:
    candidates = _collect()
    working = _check(candidates)
    pool.replace(working)
    log.info("proxy pool %s working from %s candidates", len(working), len(candidates))
    return len(working)


def _collect() -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for source in SOURCES:
        try:
            request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
            text = urlopen(request, timeout=20).read().decode("utf-8", "replace")
        except Exception as exc:
            log.info("proxy source failed %s %s", source, exc)
            continue
        for address in _ADDRESS.findall(text):
            proxy = "http://" + address
            if proxy not in seen:
                seen.add(proxy)
                found.append(proxy)
    return found


def _check(candidates: list[str]) -> list[str]:
    def alive(proxy: str) -> str | None:
        opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
        try:
            with opener.open(CHECK_URL, timeout=8) as response:
                if response.status in {200, 204}:
                    return proxy
        except Exception:
            return None
        return None

    working: list[str] = []
    checked = 0
    while working.__len__() < POOL_SIZE and checked < len(candidates) and checked < 400:
        chunk = candidates[checked : checked + 40]
        checked += len(chunk)
        with ThreadPoolExecutor(max_workers=20) as executor:
            for proxy in executor.map(alive, chunk):
                if proxy:
                    working.append(proxy)
    return working[:POOL_SIZE]
