from app.platform.config import Settings
from app.platform.models import Job
from app.platform.redis_client import redis_client

QUEUE_KEY = "crawler:jobs"


class JobQueue:
    def __init__(self, settings: Settings):
        self._redis = redis_client(settings)

    def push(self, job: Job) -> None:
        self._redis.rpush(QUEUE_KEY, job.model_dump_json())

    def pop(self, timeout: int = 5) -> Job | None:
        item = self._redis.blpop(QUEUE_KEY, timeout=timeout)
        if not item:
            return None
        return Job.model_validate_json(item[1])

    def length(self) -> int:
        return int(self._redis.llen(QUEUE_KEY))
