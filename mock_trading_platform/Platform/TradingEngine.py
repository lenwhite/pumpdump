import threading
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Union

from sortedcontainers import SortedList

from mock_trading_platform.Config import config
from mock_trading_platform.Platform.Order import (
    InvalidSideException,
    LimitOrder,
    Order,
    PricedOrder,
    Side,
)
from mock_trading_platform.Platform.OrderBook import OrderBook, PriceLevel
from mock_trading_platform.Platform.Trade import Trade


class TradingEngineException(Exception):
    pass


class OrderTooSmall(TradingEngineException):
    pass


class InvalidPricePrecision(TradingEngineException):
    pass


class InvalidSizePrecision(TradingEngineException):
    pass


class OrderAlreadyCanceled(TradingEngineException):
    pass


class OrderAlreadyCompleted(TradingEngineException):
    pass


class OrderNotFound(TradingEngineException):
    pass


class Bids:
    def __init__(self, open_orders: Dict[str, PricedOrder]) -> None:
        self.open_orders = open_orders
        self.bids = SortedList(
            (-o.price, o.create_time, o.order_id) for o in open_orders.values()
        )

    def pop(self) -> PricedOrder:
        _, _create_time, order_id = self.bids.pop(0)
        return self.open_orders[order_id]

    @property
    def best(self) -> Optional[PricedOrder]:
        try:
            _, _create_time, order_id = self.bids[0]
            return self.open_orders[order_id]
        except IndexError:
            return None

    def insert(self, order: PricedOrder):
        self.bids.add((-order.price, order.create_time, order.order_id))
        self.open_orders[order.order_id] = order

    @property
    def book(self) -> List[PriceLevel]:
        # TODO: optimize if needed
        bid_book = defaultdict(Decimal)
        for _, _create_time, order_id in self.bids:
            order = self.open_orders[order_id]
            bid_book[order.price] += order.remaining

        return [
            PriceLevel(price=p, quantity=q)
            for p, q in sorted(tuple(bid_book.items()), reverse=True)
        ]

    def remove(self, order: PricedOrder):
        self.bids.remove((-order.price, order.create_time, order.order_id))


class Asks:
    def __init__(self, open_orders: Dict[str, PricedOrder]) -> None:
        self.open_orders = open_orders
        self.asks = SortedList(
            (o.price, o.create_time, o.order_id) for o in open_orders.values()
        )

    def pop(self) -> PricedOrder:
        _, _create_time, order_id = self.asks.pop(0)
        return self.open_orders[order_id]

    @property
    def best(self) -> Optional[PricedOrder]:
        try:
            _, _create_time, order_id = self.asks[0]
            return self.open_orders[order_id]
        except IndexError:
            return None

    def insert(self, order: PricedOrder):
        self.asks.add((order.price, order.create_time, order.order_id))
        self.open_orders[order.order_id] = order

    @property
    def book(self) -> List[PriceLevel]:
        # TODO: optimize if needed
        ask_book = defaultdict(Decimal)
        for _, _create_time, order_id in self.asks:
            order = self.open_orders[order_id]
            ask_book[order.price] += order.remaining

        return [
            PriceLevel(price=p, quantity=q) for p, q in sorted(tuple(ask_book.items()))
        ]

    def remove(self, order: PricedOrder):
        self.asks.remove((order.price, order.create_time, order.order_id))


class TradingEngine:
    def __init__(self, symbol) -> None:
        self.symbol = symbol

        self._open_orders: Dict[str, Order] = {}
        self._trades: List[Trade] = []
        self._completed_orders: Dict[str, Order] = {}

        self._bids = Bids(self._open_orders)
        self._asks = Asks(self._open_orders)

        self.lock = threading.Lock()

    @property
    def price_tick(self):
        try:
            return config.symbol_configs[self.symbol].price_tick
        except KeyError:
            raise config.UndefinedSymbolConfig

    @property
    def size_tick(self):
        try:
            return config.symbol_configs[self.symbol].size_tick
        except KeyError:
            raise config.UndefinedSymbolConfig

    @property
    def min_size(self):
        try:
            return config.symbol_configs[self.symbol].min_size
        except KeyError:
            raise config.UndefinedSymbolConfig

    @property
    def order_book(self):
        return OrderBook(symbol=self.symbol, bids=self._bids.book, asks=self._asks.book)

    def order(self, order_id):
        order = self._open_orders.get(order_id) or self._completed_orders.get(order_id)
        if not order:
            raise OrderNotFound

        return order

    def check_valid_order(self, order: Union[Order, PricedOrder]):
        if order.size < self.min_size:
            raise OrderTooSmall
        if order.size.quantize(self.size_tick) != order.size:
            raise InvalidSizePrecision
        if order.price.quantize(self.size_tick) != order.price:
            raise InvalidPricePrecision

    def add_limit_order(self, order: LimitOrder) -> LimitOrder:
        if order.side == Side.buy:
            match_against = self._asks
            insert_into = self._bids
        elif order.side == Side.sell:
            match_against = self._bids
            insert_into = self._asks
        else:
            raise InvalidSideException

        while True:
            best_match = match_against.best
            if best_match is None:
                insert_into.insert(order)
                return order
            trade = self._match_limit_order(order, best_match)
            if not trade:
                insert_into.insert(order)
                return order

            order.trades.append(trade)
            best_match.trades.append(trade)
            self._trades.append(trade)

            if best_match.completed:
                match_against.pop()
            if order.completed:
                return order

    def cancel_order(self, order_id) -> LimitOrder:
        try:
            order = self._open_orders.pop(order_id)
            order.canceled = datetime.utcnow()
            self._completed_orders[order_id] = order
        except KeyError:
            if order_id in self._completed_orders:
                order = self._completed_orders[order_id]
                if order.canceled:
                    raise OrderAlreadyCanceled
                else:
                    raise OrderAlreadyCompleted

            else:
                raise OrderNotFound

    def _match_limit_order(
        self, taker_order: PricedOrder, maker_order: PricedOrder
    ) -> Optional[Trade]:
        """match two limit orders"""
        if taker_order.side * taker_order.price < taker_order.side * maker_order.price:
            return None

        return Trade(
            amount=min(maker_order.remaining, taker_order.remaining),
            price=maker_order.price,
            timestamp=taker_order.create_time,
        )
