from pydantic import BaseModel


class VendorSchema(BaseModel):
    id: int
    name: str
    source: str | None = None
    telegram_id: str | None = None
    login: str | None = None
    password: str | None = None
    function: str | None = None

    @classmethod
    def cls_validate(cls, vendor, exclude_id=False):
        if exclude_id:
            return cls.model_validate(vendor.__dict__).model_dump(exclude={"id"})
        return cls.model_validate(vendor.__dict__).model_dump()
