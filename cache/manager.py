from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Type, TypeVar

from pydantic import BaseModel

from .backend import CacheBackend
from .serializer import CacheSerializer

T = TypeVar("T", bound=BaseModel)


class CacheManager:
    def __init__(self, backend: CacheBackend, serializer: CacheSerializer):
        self._backend = backend
        self._serializer = serializer

    async def get(self, key: str, *, model: Optional[Type[T]] = None) -> Optional[Any]:
        raw = await self._backend.get(key)
        return self._serializer.deserialize(raw, model=model)

    async def set(self, key: str, value: Any, *, ttl: Optional[int] = None) -> None:
        raw = self._serializer.serialize(value)
        await self._backend.set(key, raw, ttl=ttl)

    async def delete(self, key: str) -> None:
        await self._backend.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._backend.exists(key)

    async def mget(
            self,
            keys: Iterable[str],
            *,
            model: Optional[Type[T]] = None,
    ) -> Dict[str, Optional[Any]]:
        raw_map = await self._backend.mget(list(keys))
        result: Dict[str, Optional[Any]] = {}
        for key, raw in raw_map.items():
            result[key] = self._serializer.deserialize(raw, model=model)
        return result

    async def mset(
            self,
            mapping: Dict[str, Any],
            *,
            ttl: Optional[int] = None,
    ) -> None:
        if not mapping:
            return

        raw_mapping: Dict[str, str] = {}
        for key, value in mapping.items():
            raw_mapping[key] = self._serializer.serialize(value)

        await self._backend.mset(raw_mapping, ttl=ttl)

    async def invalidate(self, prefix: str) -> None:
        await self._backend.invalidate_prefix(prefix)
