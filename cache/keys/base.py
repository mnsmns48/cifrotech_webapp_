from typing import Any

PROJECT_PREFIX = "c_webapp"
CACHE_VERSION = "v3"


def build_key(domain: str, *parts: Any) -> str:
    clean_parts = [str(p) for p in parts if p is not None]
    return f"{PROJECT_PREFIX}:{CACHE_VERSION}:{domain}:" + ":".join(clean_parts)
