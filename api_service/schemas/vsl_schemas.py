from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from api_service.schemas.product_schemas import BrandModel


class VSLSchemeBase(BaseModel):
    vendor_id: int
    title: str
    url: str
    dt_parsed: datetime | None = None


class VSLScheme(VSLSchemeBase):
    id: int

    @classmethod
    def cls_validate(cls, vendor, exclude_id=False):
        if exclude_id:
            return cls.model_validate(vendor.__dict__).model_dump(exclude={"id"})
        return cls.model_validate(vendor.__dict__).model_dump()

    model_config = {"from_attributes": True}


class VSLSchemeWithBrands(VSLScheme):
    brands: Optional[list[BrandModel]] = None


class VSLSchemeWithBrandsCreate(VSLSchemeBase):
    brands: Optional[list[BrandModel]] = None
