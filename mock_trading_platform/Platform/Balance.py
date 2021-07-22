from datetime import datetime
from decimal import Decimal
from typing import Dict

from pydantic import BaseModel
from pydantic.fields import Field

from mock_trading_platform.Platform.model_utils import static_check_init_args, uuid_hex


@static_check_init_args
class AssetBalance(BaseModel):
    available: Decimal
    reserved: Decimal

    @property
    def total(self):
        return self.available + self.reserved


class BalanceData(BaseModel):
    __root__: Dict[str, AssetBalance]

@static_check_init_args
class Balance(BaseModel):
    balances: BalanceData
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = Field(default_factory=uuid_hex)
