"""Launch MediaCrawler with CDP turned off so it starts its own browser."""

import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    home = Path(sys.argv[1]).resolve()
    if not (home / "main.py").exists():
        raise SystemExit(f"MediaCrawler main.py not found at {home}")
    os.chdir(home)
    sys.path.insert(0, str(home))
    sys.argv = [str(home / "main.py"), *sys.argv[2:]]
    import config

    config.ENABLE_CDP_MODE = False
    _use_installed_chrome()
    _relax_page_navigation()
    _skip_forced_login()
    runpy.run_path(str(home / "main.py"), run_name="__main__")


def _use_installed_chrome() -> None:
    """Playwright's bundled Chromium is flagged and Douyin returns an empty feed."""
    from playwright.async_api import BrowserType

    original_launch = BrowserType.launch
    original_persistent = BrowserType.launch_persistent_context

    async def launch(self, *args, **kwargs):
        kwargs.setdefault("channel", "chrome")
        proxy = os.environ.get("MEDIASCRAPLING_PROXY")
        if proxy:
            kwargs.setdefault("proxy", {"server": proxy})
        return await original_launch(self, *args, **kwargs)

    async def persistent(self, *args, **kwargs):
        kwargs.setdefault("channel", "chrome")
        return await original_persistent(self, *args, **kwargs)

    BrowserType.launch = launch
    BrowserType.launch_persistent_context = persistent


def _relax_page_navigation() -> None:
    """Douyin keeps the connection open, so waiting for the full load event times out."""
    from playwright.async_api import Page

    original = Page.goto

    async def goto(self, url, *args, **kwargs):
        kwargs["wait_until"] = "commit"
        kwargs["timeout"] = 60000
        try:
            await original(self, url, *args, **kwargs)
        except Exception as exc:
            if "Timeout" not in type(exc).__name__ and "Timeout" not in str(exc):
                raise
        await self.wait_for_timeout(3000)
        return None

    Page.goto = goto


def _skip_forced_login() -> None:
    """Public Douyin pages do not need a logged-in account. Keep the browser cookies and continue."""
    from media_platform.douyin.client import DouYinClient

    async def pong(self, browser_context):
        await self.update_cookies(browser_context)
        return True

    DouYinClient.pong = pong
    _open_public_feed()
    _fill_from_page_when_search_empty()


def _open_public_feed() -> None:
    from media_platform.douyin.core import DouYinCrawler

    original_init = DouYinCrawler.__init__

    def init(self):
        original_init(self)
        self.index_url = "https://www.douyin.com/jingxuan"

    DouYinCrawler.__init__ = init


def _fill_from_page_when_search_empty() -> None:
    """Search API often returns nothing without a login. The public feed still lists videos."""
    from media_platform.douyin.core import DouYinCrawler
    from store import douyin as douyin_store

    original = DouYinCrawler.search

    async def search(self):
        await original(self)
        from pathlib import Path

        save_root = Path(getattr(__import__("config"), "SAVE_DATA_PATH", "") or ".")
        if any(save_root.rglob("*contents*.json")):
            return
        import os
        import re

        limit = max(1, int(os.environ.get("MEDIASCRAPLING_LIMIT", "1")))
        pattern = re.compile(
            r'awemeId\\":\\"(\d{15,})\\".*?desc\\":\\"(.*?)\\".*?cover\\":\\"((?:https:(?:\\u0026|\\/|[^"\\])+))'
        )
        found: dict[str, tuple[str, str]] = {}
        stale = 0
        while len(found) < limit and stale < 3:
            html = await self.context_page.content()
            before = len(found)
            for match in pattern.finditer(html):
                aweme_id, title, cover = match.group(1), match.group(2), match.group(3)
                cover = cover.replace("\\u0026", "&").replace("\\/", "/")
                found.setdefault(aweme_id, (title, cover))
                if len(found) >= limit:
                    break
            if len(found) == before:
                stale += 1
            else:
                stale = 0
            if len(found) >= limit or stale >= 3:
                break
            await self.context_page.mouse.wheel(0, 2800)
            await self.context_page.wait_for_timeout(2000)
        for aweme_id, (title, cover) in list(found.items())[:limit]:
            await douyin_store.update_douyin_aweme(
                aweme_item={
                    "aweme_id": aweme_id,
                    "desc": title,
                    "author": {"nickname": ""},
                    "statistics": {},
                    "video": {"cover": {"url_list": [cover]}},
                }
            )

    DouYinCrawler.search = search


if __name__ == "__main__":
    main()
