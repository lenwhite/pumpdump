import math

import pytest

from pumpdump import utils
from pumpdump.platform.platform import Platform


def test_constant_product_quote():
    res = utils._constant_product_quote(10, 100, 1000)

    assert math.isclose((100 + 10) * (1000 - res), 100 * 1000)


@pytest.fixture
def platform():
    return Platform()


def test_populate_order_book(platform: Platform):
    utils.generate_constant_product_book("FOOBAR", platform, fee=0)
    ob = platform.order_book("FOOBAR")
    assert ob
    assert len(ob.bids) == 30
    assert len(ob.asks) == 30
