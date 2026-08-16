from fastapi import Depends

from cache.backend import CacheBackend
from cache.serializer import CacheSerializer
from cache.manager import CacheManager
from config import redis_session


def get_cache_manager(redis=Depends(redis_session)) -> CacheManager:
    backend = CacheBackend(redis)
    serializer = CacheSerializer()
    return CacheManager(backend, serializer)
