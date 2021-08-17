import random
from decimal import Decimal

from pumpdump.platform.order import LimitOrder
from pumpdump.platform.platform import Platform


# TODO: change to actor
def _constant_product_quote(
    source_asset_amount: float,
    source_asset_reserve: float,
    dest_asset_reserve: float,
) -> float:
    k = source_asset_reserve * dest_asset_reserve
    return dest_asset_reserve - k / (source_asset_reserve + source_asset_amount)


def generate_constant_product_book(
    symbol: str,
    platform: Platform,
    *,
    starting_price: Decimal = None,
    base_reserve: Decimal = None,
    quote_reserve: Decimal = None,
    levels: int = 30,
    fee: Decimal = Decimal("0.001"),
) -> None:
    if (
        starting_price is not None
        and base_reserve is not None
        and quote_reserve is not None
    ):
        raise ValueError("cannot specify all starting_price base_reserve quote_reserve")

    if base_reserve is None:
        base_reserve = random.random() * (10 ** random.uniform(4, 10))

    if quote_reserve is None and starting_price is None:
        quote_reserve = random.random() * (10 ** random.uniform(4, 10))

    approx_level_size_scaling = 100 ** (1 / 30)

    if base_reserve < quote_reserve:
        order_size = 1
    else:
        order_size = base_reserve / quote_reserve

    fee = float(fee)

    for _ in range(levels):
        quote_amount = _constant_product_quote(order_size, base_reserve, quote_reserve)
        buy_price = quote_amount / order_size * (1 + fee)
        platform.add_order(
            LimitOrder(
                symbol=symbol,
                size=order_size,
                side="buy",
                price=buy_price,
            )
        )

        quote_order_size = order_size * quote_reserve / base_reserve
        base_amount = _constant_product_quote(
            quote_order_size, quote_reserve, base_reserve
        )
        sell_price = quote_order_size / base_amount * (1 - fee)

        platform.add_order(
            LimitOrder(
                symbol=symbol,
                size=base_amount,
                side="sell",
                price=sell_price,
            )
        )

        order_size *= approx_level_size_scaling
