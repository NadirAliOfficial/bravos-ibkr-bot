"""Places IBKR orders for approved trade signals.

Known IBKR gotchas this respects:
- reqMarketDataType(1) so prices are live, not 15-min delayed
- eTradeOnly=False / firmQuoteOnly=False on every order, or paper accounts
  silently reject them
- account is set explicitly per order — required since the client has
  multiple IBKR accounts and orders otherwise route to the wrong one
"""

import asyncio

from ib_insync import IB, LimitOrder, MarketOrder, Stock, StopOrder

import config


def _apply_common_fields(order, account: str):
    order.eTradeOnly = False
    order.firmQuoteOnly = False
    if account:
        order.account = account


class IBKRClient:
    def __init__(self):
        self.ib = IB()

    def connect(self):
        # ib_insync needs an asyncio event loop in the calling thread. When this
        # runs via asyncio.to_thread() (as it does from the Telegram bot), the
        # worker thread has none by default — asyncio.get_event_loop() raises
        # rather than creating one, since Python 3.10+.
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        self.ib.connect(config.IBKR_HOST, config.IBKR_PORT, clientId=config.IBKR_CLIENT_ID)
        self.ib.reqMarketDataType(1)

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    def _qualified_stock(self, ticker: str) -> Stock:
        contract = Stock(ticker, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        return contract

    def net_liquidation(self, account: str = "") -> float:
        account = account or config.IBKR_ACCOUNT
        for v in self.ib.accountValues(account):
            if v.tag == "NetLiquidation" and v.currency == "USD":
                return float(v.value)
        return 0.0

    def position_size(self, ticker: str, account: str = "") -> int:
        account = account or config.IBKR_ACCOUNT
        for p in self.ib.positions(account):
            if p.contract.symbol == ticker:
                return int(p.position)
        return 0

    def place_open(
        self,
        ticker: str,
        quantity: int,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        account: str = "",
    ):
        """Bracket order: limit buy + one take-profit leg + one stop-loss leg.

        IBKR's native bracket only supports a single TP/SL pair per parent —
        when Bravos gives several take-profit levels, the nearest one is used
        here. A true multi-leg scale-out across all TP levels is a possible
        future enhancement, not required for this phase.
        """
        account = account or config.IBKR_ACCOUNT
        contract = self._qualified_stock(ticker)

        parent = LimitOrder("BUY", quantity, entry_price)
        parent.orderId = self.ib.client.getReqId()
        parent.transmit = False
        _apply_common_fields(parent, account)

        take_profit_order = LimitOrder("SELL", quantity, take_profit)
        take_profit_order.orderId = self.ib.client.getReqId()
        take_profit_order.parentId = parent.orderId
        take_profit_order.transmit = False
        _apply_common_fields(take_profit_order, account)

        stop_loss_order = StopOrder("SELL", quantity, stop_loss)
        stop_loss_order.orderId = self.ib.client.getReqId()
        stop_loss_order.parentId = parent.orderId
        stop_loss_order.transmit = True
        _apply_common_fields(stop_loss_order, account)

        return [
            self.ib.placeOrder(contract, parent),
            self.ib.placeOrder(contract, take_profit_order),
            self.ib.placeOrder(contract, stop_loss_order),
        ]

    def place_sell(self, ticker: str, quantity: int, account: str = ""):
        """Plain market sell — used for PARTIAL_CLOSE and CLOSE signals."""
        account = account or config.IBKR_ACCOUNT
        contract = self._qualified_stock(ticker)
        order = MarketOrder("SELL", quantity)
        _apply_common_fields(order, account)
        return self.ib.placeOrder(contract, order)
