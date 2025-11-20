from pydantic import BaseModel


class ServiceImageResponse(BaseModel):
    id: int
    var: str
    value: str
    image: str


class ServiceImageCreate(BaseModel):
    var: str
    value: str


class ServiceImageUpdate(BaseModel):
    var: str | None = None
    value: str | None = None
