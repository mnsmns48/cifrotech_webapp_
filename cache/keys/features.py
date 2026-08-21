from cache.keys.base import build_key


def short_specs_key(feature_id: int) -> str:
    return build_key("short_specs", feature_id)


def feature_key(feature_id: int) -> str:
    return build_key("full_features", feature_id)
