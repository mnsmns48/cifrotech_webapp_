from pydantic import BaseModel


class GenerateDescriptionPayload(BaseModel):
    product_features_id: int
