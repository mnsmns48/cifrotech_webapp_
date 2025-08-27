from typing import List

from pydantic import BaseModel


class RewardRangeLineSchema(BaseModel):
    line_from: int
    line_to: int
    is_percent: bool
    reward: int

    class Config:
        from_attributes = True


class RewardRangeSchema(BaseModel):
    title: str


class RewardRangeResponseSchema(BaseModel):
    id: int
    title: str
    ranges: List[RewardRangeLineSchema]


class RewardRangeAddLineSchema(BaseModel):
    range_id: int
    line_from: int
    line_to: int
    is_percent: bool
    reward: int

    class Config:
        from_attributes = True
