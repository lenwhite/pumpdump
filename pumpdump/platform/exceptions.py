class PlatformException(Exception):
    pass


class InsufficientBalance(Exception):
    pass


class UnrecognizedSymbol(PlatformException):
    pass


class UnrecognizedOrderType(PlatformException):
    pass


class TradingEngineException(PlatformException):
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
