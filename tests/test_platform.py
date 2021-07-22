import pytest

from mock_trading_platform.platform.order import LimitOrder
from mock_trading_platform.platform.platform import Platform


@pytest.fixture
def platform():
    return Platform()


def test_balance(platform: Platform):
    balance = platform.balance("0")
    assert balance.balances["FOO"].available == 1e12
    assert balance.balances["FOO"].reserved == 0
    assert balance.balances["BAR"].available == 1e12
    assert balance.balances["BAR"].reserved == 0
    assert balance.user_id == "0"


def test_balance_reserve(platform: Platform):
    balance = platform.balance("0")
    platform.add_order(
        LimitOrder(symbol="FOOBAR", size=200, side="sell", price="100", user_id="0")
    )
    balance = platform.balance("0")
    assert balance.balances["FOO"].available == 1e12 - 200
    assert balance.balances["FOO"].reserved == 200


def test_balance_trade(platform: Platform):
    balance = platform.balance("0")
    platform.add_order(LimitOrder(symbol="FOOBAR", size=200, side="buy", price="100"))
    platform.add_order(
        LimitOrder(symbol="FOOBAR", size=200, side="sell", price="100", user_id="0")
    )

    balance = platform.balance("0")
    assert balance.balances["FOO"].available == 1e12 - 200
    assert balance.balances["BAR"].available == 1e12 + 20000
