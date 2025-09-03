from datetime import datetime

from pydantic import BaseModel


class VSLScheme(BaseModel):
    id: int
    vendor_id: int
    title: str
    url: str
    dt_parsed: datetime | None = None
    profit_range_id: int | None = None

    @classmethod
    def cls_validate(cls, vendor, exclude_id=False):
        if exclude_id:
            return cls.model_validate(vendor.__dict__).model_dump(exclude={"id"})
        return cls.model_validate(vendor.__dict__).model_dump()

    model_config = {"from_attributes": True}
