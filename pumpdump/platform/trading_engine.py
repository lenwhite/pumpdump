import threading
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

from sortedcontainers import SortedList

from pumpdump import PlatformConfig, default_config

from .exceptions import (
    InvalidPricePrecision,
    InvalidSizePrecision,
    OrderAlreadyCanceled,
    OrderAlreadyCompleted,
    OrderNotFound,
    OrderTooSmall,
)
from .order import InvalidSideException, LimitOrder, Order, PricedOrder, Side
from .order_book import OrderBook, PriceLevel
from .trade import Trade


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
    def __init__(self, symbol, config: Optional[PlatformConfig] = None) -> None:
        self.config = config or default_config
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
            return self.config.symbol_configs[self.symbol].price_tick
        except KeyError:
            raise self.config.UndefinedSymbolConfig

    @property
    def size_tick(self):
        try:
            return self.config.symbol_configs[self.symbol].size_tick
        except KeyError:
            raise self.config.UndefinedSymbolConfig

    @property
    def min_size(self):
        try:
            return self.config.symbol_configs[self.symbol].min_size
        except KeyError:
            raise self.config.UndefinedSymbolConfig

    @property
    def order_book(self):
        return OrderBook(symbol=self.symbol, bids=self._bids.book, asks=self._asks.book)

    def order_status(self, order_id):
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

    def add_limit_order(self, order: LimitOrder) -> List[Tuple[Order, Trade]]:
        if order.side == Side.buy:
            match_against = self._asks
            insert_into = self._bids
        elif order.side == Side.sell:
            match_against = self._bids
            insert_into = self._asks
        else:
            raise InvalidSideException

        order_trades: List[Tuple[Order, Trade]] = []

        while True:
            best_match = match_against.best
            if best_match is None:
                insert_into.insert(order)
                return order_trades
            trade = self._match_limit_order(order, best_match)
            if not trade:
                insert_into.insert(order)
                return order_trades

            order.trades.append(trade)
            best_match.trades.append(trade)
            self._trades.append(trade)
            order_trades.append((order, trade))
            order_trades.append((best_match, trade))

            if best_match.completed:
                match_against.pop()
            if order.completed:
                return order_trades

    def cancel_order(self, order_id: str) -> Order:
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

    def cancel_all(self, user_id: Optional[str] = None) -> List[Order]:
        return [
            self.cancel_order(order_id)
            for order_id, order in tuple(self._open_orders.items())
            if order.user_id == user_id
        ]

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
