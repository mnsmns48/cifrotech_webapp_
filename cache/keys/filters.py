from cache.keys.base import build_key


def model_filters_key(feature_ids: list[int]) -> str:
    sorted_ids = sorted(feature_ids)
    joined = ",".join(str(fid) for fid in sorted_ids)
    return build_key("model_filters", joined)
