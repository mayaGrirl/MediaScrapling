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
    _relax_page_navigation()
    runpy.run_path(str(home / "main.py"), run_name="__main__")


def _relax_page_navigation() -> None:
    """Douyin keeps the connection open, so waiting for the full load event times out."""
    from playwright.async_api import Page

    original = Page.goto

    async def goto(self, url, *args, **kwargs):
        kwargs["wait_until"] = "commit"
        kwargs["timeout"] = 60000
        try:
            return await original(self, url, *args, **kwargs)
        except Exception as exc:
            if "Timeout" not in type(exc).__name__ and "Timeout" not in str(exc):
                raise
            return None

    Page.goto = goto


if __name__ == "__main__":
    main()
