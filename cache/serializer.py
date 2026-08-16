from __future__ import annotations

from typing import Any, Type, TypeVar, Optional

import json
from pydantic import BaseModel

T = TypeVar("T")


class CacheSerializer:
    @staticmethod
    def serialize(value: Any) -> str:
        if isinstance(value, BaseModel):
            return value.model_dump_json()

        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)

        return str(value)

    @staticmethod
    def deserialize(raw: Optional[str], model: Optional[Type[T]] = None) -> Optional[T]:
        if raw is None:
            return None

        if model is not None and issubclass(model, BaseModel):
            return model.model_validate_json(raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
