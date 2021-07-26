from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field

from .model_utils import static_check_init_args


@static_check_init_args
class SymbolConfig(BaseModel):
    symbol: str
    price_tick: Decimal
    size_tick: Decimal
    min_size: Decimal
    base: Optional[str] = Field(
        default=None, description="base currency/asset of the symbol"
    )
    quote: Optional[str] = Field(
        default=None, description="quote currency/asset of the symbol"
    )


@static_check_init_args
class InitialBalance(BaseModel):
    user_id: Optional[str]
    balances: Dict[str, Decimal] = Field(default_factory=dict)


def default_symbol_config() -> Dict[str, SymbolConfig]:
    return {
        "FOOBAR": SymbolConfig(
            symbol="FOOBAR",
            price_tick=0.01,
            size_tick=0.01,
            min_size=0.01,
            base="FOO",
            quote="BAR",
        )
    }


def default_balance_config() -> Dict[Optional[str], InitialBalance]:
    return {
        None: InitialBalance(
            user_id=None,
            balances={
                "FOO": 1e12,
                "BAR": 1e12,
                "USD": 1e12,
                "BAZQUX": 1e12,
            },
        )
    }


@static_check_init_args
class PlatformConfig(BaseModel):
    symbol_configs: Dict[str, SymbolConfig] = Field(
        default_factory=default_symbol_config
    )

    balance_config: Dict[Optional[str], InitialBalance] = Field(
        default_factory=default_balance_config
    )

    class UndefinedSymbolConfig(Exception):
        pass


default_config = PlatformConfig()
