import redis

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
        try:
            item = self._redis.blpop(QUEUE_KEY, timeout=timeout)
        except redis.TimeoutError:
            return None
        if not item:
            return None
        return Job.model_validate_json(item[1])

    def remove(self, job_id: str) -> None:
        for raw in self._redis.lrange(QUEUE_KEY, 0, -1):
            try:
                job = Job.model_validate_json(raw)
            except ValueError:
                continue
            if job.id == job_id:
                self._redis.lrem(QUEUE_KEY, 0, raw)

    def length(self) -> int:
        return int(self._redis.llen(QUEUE_KEY))
