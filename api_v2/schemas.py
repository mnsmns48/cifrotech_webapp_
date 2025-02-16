from pydantic import BaseModel, Field


class Menu(BaseModel):
    code: int = Field(ge=0, le=1000)
    parent: int = Field(ge=0, le=1000)
    name: str
