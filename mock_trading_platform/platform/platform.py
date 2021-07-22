import threading
from collections import defaultdict
from typing import Dict, List, Mapping, Optional

from mock_trading_platform import PlatformConfig, SymbolConfig, default_config
from mock_trading_platform.platform.balance import AssetBalance, Balance, BalanceData
from mock_trading_platform.platform.order import Order, OrderType, PricedOrder, Side
from mock_trading_platform.platform.trade import Trade
from mock_trading_platform.platform.trading_engine import TradingEngine

from .exceptions import (
    InsufficientBalance,
    OrderNotFound,
    UnrecognizedOrderType,
    UnrecognizedSymbol,
)


class Platform:
    def __init__(self, config: Optional[PlatformConfig] = None) -> None:
        self.config = config or default_config
        self._account_balance: Mapping[str, Balance] = defaultdict(
            self._default_balance
        )
        self._account_balance.update(
            {
                user_id: BalanceData(
                    __root__={
                        asset: AssetBalance(available=start_balance)
                        for asset, start_balance in (balance.balances.items())
                    }
                )
                for user_id, balance in self.config.balance_config.items()
            }
        )
        # TODO: remove dependence on global config object
        self.trading_engine: Mapping[str, TradingEngine] = {
            symbol: TradingEngine(symbol) for symbol in self.config.symbol_configs
        }
        self.lock = threading.Lock()

    @property
    def symbol_configs(self) -> Dict[str, SymbolConfig]:
        return self.config.symbol_configs

    def _default_balance(self):
        return BalanceData(
            __root__={
                asset: AssetBalance(available=start_balance)
                for asset, start_balance in self.config.balance_config[
                    None
                ].balances.items()
            }
        )

    def balance(self, user_id: Optional[str]) -> Balance:
        if user_id is None:
            return Balance(balances=self._default_balance())

        return Balance(balances=self._account_balance[user_id], user_id=user_id)

    def _on_trade(self, order: Order, trade: Trade):
        if order.user_id is None:
            return

        base = self.config.symbol_configs[order.symbol].base
        quote = self.config.symbol_configs[order.symbol].quote

        if order.side == Side.buy:
            if base is not None:
                self._account_balance[order.user_id][base].available += trade.amount
            if quote is not None:
                if isinstance(order, PricedOrder):
                    self._account_balance[order.user_id][quote].reserved -= (
                        trade.amount * trade.price
                    )
                else:
                    self._account_balance[order.user_id][quote].available -= (
                        trade.amount * trade.price
                    )

        elif order.side == Side.sell:
            if base is not None:
                if isinstance(order, PricedOrder):
                    self._account_balance[order.user_id][base].reserved -= trade.amount
                else:
                    self._account_balance[order.user_id][base].available -= trade.amount
            if quote is not None:
                self._account_balance[order.user_id][quote].available += (
                    trade.amount * trade.price
                )

        # TODO: add other callbacks (for websocket?)

    def _reserve_asset(self, order: Order):
        if order.user_id is None:
            return

        if not isinstance(order, PricedOrder):
            return

        if order.side == Side.buy:
            reserve_amount = order.size * order.price
            asset = self.config.symbol_configs[order.symbol].quote
        elif order.side == Side.sell:
            reserve_amount = order.size
            asset = self.config.symbol_configs[order.symbol].base

        if asset is None:
            return

        if self._account_balance[order.user_id][asset].available < reserve_amount:
            raise InsufficientBalance(asset)

        self._account_balance[order.user_id][asset].available -= reserve_amount
        self._account_balance[order.user_id][asset].reserved += reserve_amount

    def add_order(self, order: Order) -> Order:
        with self.lock:
            self._reserve_asset(order)
            try:
                trading_engine = self.trading_engine[order.symbol]
            except KeyError:
                raise UnrecognizedSymbol

            if order.order_type == OrderType.limit_order:
                order_trades = trading_engine.add_limit_order(order)
            else:
                raise UnrecognizedOrderType

            for order, trade in order_trades:
                self._on_trade(order, trade)

            return Order

    def order_status(self, order_id: str, symbol: Optional[str] = None) -> Order:
        if symbol is None:
            symbols = tuple(self.trading_engine.keys())
        else:
            symbols = tuple(symbol)

        for symbol in symbols:
            try:
                return self.trading_engine[symbol].order_status(order_id)
            except OrderNotFound:
                pass
        else:
            raise OrderNotFound

    def cancel_order(self, order_id, symbol: Optional[str] = None) -> Order:
        if symbol is None:
            symbols = tuple(self.trading_engine.keys())
        else:
            symbols = tuple(symbol)

        for symbol in symbols:
            try:
                return self.trading_engine[symbol].cancel_order(order_id)
            except OrderNotFound:
                pass
        else:
            raise OrderNotFound

    def cancel_all_orders(
        self, symbol: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Order]:
        if symbol is None:
            symbols = tuple(self.trading_engine.keys())
        else:
            symbols = tuple(symbol)

        canceled = []
        for symbol in symbols:
            canceled.append(self.trading_engine[symbol].cancel_order(user_id))

        return canceled

    def order_book(self, symbol: str):
        try:
            return self.trading_engine[symbol].order_book
        except KeyError:
            raise UnrecognizedSymbol
