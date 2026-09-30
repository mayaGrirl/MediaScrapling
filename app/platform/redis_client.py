import redis

from app.platform.config import Settings


def redis_client(settings: Settings) -> redis.Redis:
    # protocol=2 keeps older local Redis servers that reject HELLO.
    return redis.Redis.from_url(settings.redis_url, decode_responses=True, protocol=2)
