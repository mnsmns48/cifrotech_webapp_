from __future__ import annotations

from typing import Dict, Iterable, Optional

from redis.asyncio import Redis


class CacheBackend:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get(self, key: str) -> Optional[str]:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return raw

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        if ttl is not None and ttl > 0:
            await self._redis.set(key, value, ex=ttl)
        else:
            await self._redis.set(key, value)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(key))

    async def mget(self, keys: Iterable[str]) -> Dict[str, Optional[str]]:
        raw_values = await self._redis.mget(list(keys))
        result: Dict[str, Optional[str]] = {}
        for key, raw in zip(keys, raw_values):
            if raw is None:
                result[key] = None
            elif isinstance(raw, bytes):
                result[key] = raw.decode("utf-8")
            else:
                result[key] = raw
        return result

    async def mset(self, mapping: Dict[str, str], ttl: Optional[int] = None) -> None:
        if not mapping:
            return

        if ttl is None or ttl <= 0:
            await self._redis.mset(mapping)
            return

        pipe = self._redis.pipeline()
        for key, value in mapping.items():
            pipe.execute_command("SET", key, value, "EX", ttl)
        await pipe.execute()

    async def invalidate_prefix(self, prefix: str) -> None:
        cursor = 0
        pattern = f"{prefix}*"
        while True:
            cursor, keys = await self._redis.scan(cursor=cursor, match=pattern, count=1000)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break
