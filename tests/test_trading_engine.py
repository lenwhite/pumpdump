from decimal import Decimal

import pytest

from mock_trading_platform.platform.order import LimitOrder
from mock_trading_platform.platform.trading_engine import TradingEngine


def test_default_engine():
    te = TradingEngine("FOOBAR")
    assert te


@pytest.fixture
def engine():
    return TradingEngine("FOOBAR")


@pytest.fixture
def engine_with_orders(engine: TradingEngine):
    for i in range(10):
        engine.add_limit_order(LimitOrder(size=100, side="buy", price=100 - i))

    for i in range(10):
        engine.add_limit_order(LimitOrder(size=100, side="sell", price=110 + i))

    return engine


def test_limit_orders(engine_with_orders: TradingEngine):
    engine = engine_with_orders

    ob = engine.order_book
    print(ob)

    assert len(ob.bids) == 10
    assert len(ob.asks) == 10

    for i in range(10):
        assert ob.bids[i].price == 100 - i
        assert ob.bids[i].quantity == 100

    for i in range(10):
        assert ob.asks[i].price == 110 + i
        assert ob.asks[i].quantity == 100


def test_crossing_order(engine_with_orders: TradingEngine):
    engine = engine_with_orders
    order = engine.add_limit_order(LimitOrder(size=200, side="buy", price="110.5"))

    ob = engine.order_book
    print(order)
    print(ob)
    assert len(ob.asks) == 9
    assert len(ob.bids) == 11
    assert ob.bids[0].price == Decimal("110.5")
    assert ob.bids[0].quantity == 100

    assert order.remaining == 100
    assert len(order.trades) == 1
    assert order.trades[0].price == 110
    assert order.trades[0].amount == 100
