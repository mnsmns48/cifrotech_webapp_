from typing import List

from pydantic import BaseModel


class RewardRangeLineSchema(BaseModel):
    line_from: int
    line_to: int
    is_percent: bool
    reward: int

    model_config = {"from_attributes": True}


class RewardRangeSchema(BaseModel):
    title: str


class RewardRangeAddLineSchema(BaseModel):
    range_id: int
    line_from: int
    line_to: int
    is_percent: bool
    reward: int

    model_config = {"from_attributes": True}


class RewardRangeBaseSchema(BaseModel):
    id: int
    title: str
    model_config = {"from_attributes": True}


class RewardRangeResponseSchema(RewardRangeBaseSchema):
    ranges: List[RewardRangeLineSchema]
