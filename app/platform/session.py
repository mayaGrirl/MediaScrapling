from app.platform.config import Settings
from app.platform.redis_client import redis_client


class SessionStore:
    """Cookies shared by both capabilities. Keyed by platform name or host."""

    def __init__(self, settings: Settings):
        self._redis = redis_client(settings)

    def put(self, key: str, cookie: str) -> None:
        self._redis.set(self._name(key), cookie)

    def get(self, key: str) -> str | None:
        return self._redis.get(self._name(key))

    @staticmethod
    def _name(key: str) -> str:
        return f"crawler:session:{key}"
