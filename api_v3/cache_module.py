from cache.settings import cache_ttl


def cache_key(feature_id: int) -> str:
    return f"product_features:{feature_id}"


async def get_cached_features(cache, feature_id: int):
    return await cache.get(cache_key(feature_id))


async def set_cached_features(cache, feature_id: int, full_specs, pros_cons):
    await cache.set(
        cache_key(feature_id),
        {
            "full_specs": full_specs.model_dump() if full_specs else None,
            "pros_cons": pros_cons,
        },
        ttl=cache_ttl.medium,
    )
