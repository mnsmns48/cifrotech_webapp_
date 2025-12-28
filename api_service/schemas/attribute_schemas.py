from pydantic import BaseModel, field_validator


class AttributeBase(BaseModel):
    attribute_name: str
    alias: str | None

    @field_validator("attribute_name")
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Attribute name cannot be empty")
        return v

    @field_validator("alias")
    def validate_alias(cls, v):
        return v.strip() if v else v


class CreateAttribute(AttributeBase):
    key: int


class UpdateAttribute(AttributeBase):
    id: int
