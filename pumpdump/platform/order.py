import enum
from datetime import datetime
from decimal import Decimal
from typing import DefaultDict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, validator

from pumpdump.model_utils import static_check_init_args, uuid_hex
from pumpdump.platform.trade import Trade


class InvalidSideException(Exception):
    pass


N = TypeVar("N", int, float, Decimal)


class Side(str, enum.Enum):
    buy = "buy"
    sell = "sell"

    def __eq__(self, x: object) -> bool:
        if super().__eq__(x):
            return True
        x = str(x).lower()
        if x in ("buy", "long", "b", "1"):
            return self == Side.buy
        if x in ("sell", "short", "s", "-1"):
            return self == Side.sell
        return NotImplemented

    def __mul__(self, x: Generic[N]) -> N:
        if self == Side.buy:
            return x
        return -x


class OrderType(str, enum.Enum):
    limit_order = "limit_order"


@static_check_init_args
class Order(BaseModel):
    symbol: str
    size: Decimal
    side: Side
    order_type: OrderType
    canceled: Optional[datetime] = None
    trades: List[Trade] = []
    order_id: str = Field(default_factory=uuid_hex)
    fees: dict = DefaultDict(default_factory=Decimal)
    create_time: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    order_tag: Optional[str] = None

    @property
    def dealt(self) -> Decimal:
        return sum(t.amount for t in self.trades)

    @property
    def remaining(self) -> Decimal:
        return self.size - self.dealt

    @property
    def completed(self):
        return self.dealt == self.size

    @validator("size")
    def size_must_gte_zero(cls, v):
        if v <= 0:
            raise ValueError("must be greater than zero")
        return v


@static_check_init_args
class PricedOrder(Order):
    price: Decimal = Field()

    @validator("price")
    def price_must_gte_zero(cls, v):
        if v <= 0:
            raise ValueError("must be greater than zero")
        return v


@static_check_init_args
class LimitOrder(PricedOrder):
    order_type = OrderType.limit_order
