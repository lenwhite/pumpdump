import time

import pytest

from mock_trading_platform.actor.random_walk import RandomWalk
from mock_trading_platform.platform.platform import Platform


@pytest.fixture
def platform():
    return Platform()


@pytest.fixture
def random_walk(platform: Platform):
    return RandomWalk(platform, "FOOBAR", run_interval=0.01)


def test_random_walk_run(random_walk: RandomWalk, platform: Platform):
    random_walk.start()
    time.sleep(0.5)
    random_walk.stop_flag.set()

    ob = platform.order_book("FOOBAR")
    assert not random_walk.exception
    
    assert ob.bids
    assert ob.asks
