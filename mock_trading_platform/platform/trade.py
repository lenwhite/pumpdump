from datetime import datetime
from decimal import Decimal

from pydantic.fields import Field
from pydantic.main import BaseModel

from mock_trading_platform.platform.model_utils import static_check_init_args, uuid_hex


@static_check_init_args
class Trade(BaseModel):
    price: Decimal
    amount: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow())
    trade_id: str = Field(default_factory=uuid_hex)
