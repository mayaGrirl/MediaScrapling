import redis

from app.platform.config import Settings


def redis_client(settings: Settings) -> redis.Redis:
    # protocol=2 keeps older local Redis servers that reject HELLO.
    # socket_timeout must stay unset so BLPOP can wait without the client aborting first.
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        protocol=2,
        socket_timeout=None,
        socket_connect_timeout=5,
    )
