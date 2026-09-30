from dataclasses import dataclass

from app.platform.config import Settings
from app.platform.proxy import ProxyPool
from app.platform.queue import JobQueue
from app.platform.session import SessionStore
from app.platform.store import Store


@dataclass
class PlatformContext:
    settings: Settings
    queue: JobQueue
    proxies: ProxyPool
    sessions: SessionStore
    store: Store

    @classmethod
    def open(cls, settings: Settings | None = None) -> "PlatformContext":
        settings = settings or Settings()
        return cls(
            settings=settings,
            queue=JobQueue(settings),
            proxies=ProxyPool(settings),
            sessions=SessionStore(settings),
            store=Store(settings),
        )
