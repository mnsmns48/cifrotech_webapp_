from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, conint, confloat

from models import Vendor, VendorSearchLine


@dataclass
class SourceContext:
    vendor: Vendor
    vsl: VendorSearchLine


class ParsingRequest(BaseModel):
    progress: str
    vsl_id: int
    sync_features: bool


class ParsingLinesIn(BaseModel):
    origin: conint(ge=0)
    title: str
    link: Optional[str] = None
    shipment: Optional[str] = None
    warranty: Optional[str] = None
    input_price: Optional[confloat(ge=0)] = None
    output_price: Optional[confloat(ge=0)] = None
    pics: Optional[List[str]] = None
    preview: Optional[str] = None
    optional: Optional[str] = None
    features_title: Optional[list] = None
    profit_range_id: Optional[int] = None

    model_config = {"from_attributes": True, "extra": "ignore"}


class ParsingResultOut(BaseModel):
    dt_parsed: Optional[datetime] = None
    profit_range_id: Optional[int] = None
    is_ok: bool
    duration: Optional[float] = None
    parsing_result: List[ParsingLinesIn]

    model_config = {"from_attributes": True}


class ParsingToDiffData(BaseModel):
    origin: int
    title: str
    url: Optional[str]
    warranty: Optional[str]
    optional: Optional[str]
    shipment: Optional[str]
    parsing_line_title: str
    parsing_input_price: Optional[float]
    parsing_output_price: Optional[float]
    dt_parsed: datetime
    profit_range_id: Optional[int]
