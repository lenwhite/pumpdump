import random
import threading
import time
from decimal import Decimal
from typing import Any, Optional, Union

from pumpdump.platform.order import LimitOrder, Side
from pumpdump.platform.platform import Platform


class RandomWalk(threading.Thread):
    def __init__(
        self,
        platform: Platform,
        symbol: str,
        initial_price: Union[int, float, Decimal, str] = 100,
        volume: Union[int, float, Decimal, str] = 100,
        variance: Union[int, float, Decimal, str] = 1.01,
        run_interval: Union[int, float, Decimal, str] = 0.1,
        stop_flag: Optional[threading.Event] = None,
        seed: Any = None,
    ) -> None:
        super().__init__(name="random walk bot", daemon=True)

        self.platform = platform
        self.symbol = symbol
        self.initial_price = initial_price
        self.volume = volume
        self.variance = variance
        self.run_interval = run_interval

        self.stop_flag = stop_flag or threading.Event()
        self.random = random.Random()
        self.random.seed(seed)
        self.exception: Optional[Exception] = None

    def run(self):
        try:
            symbol_configs = self.platform.symbol_configs
            symbol_config = symbol_configs[self.symbol]
            while not self.stop_flag.is_set():
                ob = self.platform.order_book(self.symbol)
                side = self.random.choice((Side.buy, Side.sell))

                if side == Side.buy and ob.bids:
                    reference_price = float(ob.bids[0].price)
                elif side == Side.buy and ob.asks:
                    reference_price = float(ob.asks[0].price) / (self.variance ** 5)
                elif side == Side.sell and ob.asks:
                    reference_price = float(ob.asks[0].price)
                elif side == Side.sell and ob.bids:
                    reference_price = float(ob.bids[0].price) * (self.variance ** 5)
                else:
                    reference_price = self.initial_price

                size = self.random.weibullvariate(self.volume, 1)

                if side == Side.buy:
                    reference_price *= self.variance ** ((self.volume / size - 1) / 10)
                elif side == Side.sell:
                    reference_price *= self.variance ** ((size / self.volume - 1) / 10)

                size = Decimal(size).quantize(exp=symbol_config.size_tick)
                if size < symbol_config.min_size:
                    continue

                price = Decimal(
                    self.random.normalvariate(1, self.variance - 1) * reference_price
                ).quantize(exp=symbol_config.price_tick)

                order = LimitOrder(
                    symbol=self.symbol, size=size, side=side, price=price
                )
                print(order)
                self.platform.add_order(order)

                time.sleep(self.run_interval)
        except Exception as e:
            self.exception = e
            raise
