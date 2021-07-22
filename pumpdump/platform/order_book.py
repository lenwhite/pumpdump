from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel
from pydantic.fields import Field

from pumpdump.model_utils import static_check_init_args


@static_check_init_args
class PriceLevel(BaseModel):
    price: Decimal
    quantity: Decimal


@static_check_init_args
class OrderBook(BaseModel):
    symbol: str
    bids: List[PriceLevel]
    asks: List[PriceLevel]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
