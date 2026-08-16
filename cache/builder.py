from typing import Any, cast

from fastapi_cache import default_key_builder, KeyBuilder
from sqlalchemy.ext.asyncio import AsyncSession

IGNORED_CACHE_KEYS = {"session", "db", "redis", "redis_session", "s3_client"}


def _cache_key_builder(func, namespace: str = "", *, request=None, response=None,
                       args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None, ) -> str:
    kwargs = kwargs.copy() if kwargs else {}
    for key in IGNORED_CACHE_KEYS:
        kwargs.pop(key, None)
    clean_args = tuple(arg for arg in args if not isinstance(arg, AsyncSession))

    return default_key_builder(
        func=func, namespace=namespace, request=request, response=response, args=clean_args, kwargs=kwargs)


cache_key_builder = cast(KeyBuilder, _cache_key_builder)
