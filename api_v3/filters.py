import json
import hashlib
from typing import Any, Dict


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, list):
        normalized = [_normalize_value(v) for v in value]
        return sorted(normalized)

    if isinstance(value, dict):
        return {
            key: _normalize_value(value[key])
            for key in sorted(value.keys())
            if value[key] is not None
        }

    if isinstance(value, str) and value.isdigit():
        return int(value)

    return value


def normalize_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {
        key: value
        for key, value in filters.items()
        if value not in (None, "", [], {})
    }

    normalized = {
        key: _normalize_value(value)
        for key, value in cleaned.items()
    }

    return normalized


def generate_filters_hash(filters: Dict[str, Any]) -> str:
    normalized = normalize_filters(filters)
    json_str = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(json_str.encode("utf-8")).hexdigest()
