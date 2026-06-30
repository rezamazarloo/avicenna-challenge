from functools import lru_cache

from django.conf import settings
from redis import Redis


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis.from_url(settings.NOTIFICATION_REDIS_URL, decode_responses=True)
