from dataclasses import dataclass
from decimal import Decimal
from typing import Dict


@dataclass
class SymbolConfig:
    symbol: str
    price_tick: Decimal
    size_tick: Decimal
    min_size: Decimal


class config:
    symbol_configs: Dict[str, SymbolConfig] = {
        "FOOBAR": SymbolConfig(
            symbol="FOOBAR", price_tick=0.01, size_tick=0.01, min_size=0.01
        )
    }

    class UndefinedSymbolConfig(Exception):
        pass
