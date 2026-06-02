from pydantic import BaseModel


class GenerateDescriptionPayload(BaseModel):
    product_features_map: dict[int, dict | None]


class SpecsParamScheme(BaseModel):
    category: str
    param: str
