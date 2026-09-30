from app.platform.config import Settings
from app.platform.redis_client import redis_client

PROXY_KEY = "crawler:proxies"


class ProxyPool:
    def __init__(self, settings: Settings):
        self._redis = redis_client(settings)

    def add(self, proxy_url: str) -> None:
        self._redis.sadd(PROXY_KEY, proxy_url)

    def acquire(self) -> str | None:
        proxy = self._redis.srandmember(PROXY_KEY)
        return proxy or None

    def list(self) -> list[str]:
        return sorted(self._redis.smembers(PROXY_KEY))

    def replace(self, proxy_urls: list[str]) -> None:
        pipe = self._redis.pipeline()
        pipe.delete(PROXY_KEY)
        if proxy_urls:
            pipe.sadd(PROXY_KEY, *proxy_urls)
        pipe.execute()
