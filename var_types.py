from dataclasses import dataclass
from enum import Enum


@dataclass
class VarTypes:
    UserIdType = int


var_types = VarTypes()


class PriceDiffStatus(str, Enum):
    only_parsing = "only_parsing"
    only_hub = "only_hub"
    equal = "equal"
    hub_higher = "hub_higher"
    parsing_higher = "parsing_higher"
