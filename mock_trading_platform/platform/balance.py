from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterator, MutableMapping

from pydantic import BaseModel
from pydantic.fields import Field

from mock_trading_platform.model_utils import static_check_init_args, uuid_hex


@static_check_init_args
class AssetBalance(BaseModel):
    available: Decimal
    reserved: Decimal = Decimal(0)

    @property
    def total(self):
        return self.available + self.reserved


class BalanceData(MutableMapping, BaseModel):
    __root__: Dict[str, AssetBalance]

    def __getitem__(self, k: str) -> AssetBalance:
        try:
            return self.__root__.__getitem__(k)
        except KeyError:
            return AssetBalance(Decimal(0))

    def __setitem__(self, k: str, v: AssetBalance) -> None:
        return self.__root__.__setitem__(k, v)

    def __delitem__(self, v: str) -> None:
        return self.__root__.__delitem__(v)

    def __iter__(self) -> Iterator[AssetBalance]:
        return self.__root__.__iter__()

    def __len__(self) -> int:
        return self.__root__.__len__()


@static_check_init_args
class Balance(BaseModel):
    balances: BalanceData
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = Field(default_factory=uuid_hex)
