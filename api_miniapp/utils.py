import json
from functools import wraps

from fastapi_cache import FastAPICache


def cache_with_duration(expire):
    def extract_ids(args, kwargs):
        ids = kwargs.get("ids")
        if ids is None:
            ids = next((a for a in args if isinstance(a, (list, tuple))), None)
        return ids

    def normalize_ids(ids):
        try:
            return ",".join(map(str, sorted(map(int, ids))))
        except (TypeError, ValueError):
            return ",".join(map(str, ids))

    def deserialize(raw):
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return raw

    def serialize(result_obj, expire, cache_key, cache_backend):
        try:
            cached_copy = dict(result_obj)
            cached_copy["duration_ms"] = 0
            serialized = json.dumps(cached_copy).encode("utf-8")
            return cache_backend.set(cache_key, serialized, expire)
        except (TypeError, ValueError):
            return None

    def to_dict(result):
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if hasattr(result, "dict"):
            return result.dict()
        return None

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ids = extract_ids(args, kwargs)
            if ids is None:
                return await func(*args, **kwargs)

            ids_sorted = normalize_ids(ids)
            cache_key = f"{func.__module__}:{func.__name__}:{ids_sorted}"
            cache_backend = FastAPICache.get_backend()

            raw = await cache_backend.get(cache_key)
            if raw is not None:
                return deserialize(raw)

            result = await func(*args, **kwargs)
            result_obj = to_dict(result)
            if result_obj is None:
                return result

            await serialize(result_obj, expire, cache_key, cache_backend)
            return result

        return wrapper

    return decorator
