"""Turns an approved TradeSignal row into IBKR orders.

Kept as a plain synchronous function (not async) so it can run in its own
thread via asyncio.to_thread() — ib_insync manages its own event loop, and
mixing that with python-telegram-bot's asyncio loop in the same thread is a
recipe for conflicts.
"""

import json

from ibkr_client import IBKRClient
from models import TradeAction
from position_sizing import (
    close_quantity,
    increase_quantity,
    open_quantity,
    partial_close_quantity,
)


class ExecutionError(Exception):
    pass


def execute_signal_sync(signal: dict) -> list[int]:
    """Returns the list of IBKR order IDs placed. Raises ExecutionError on
    anything that should stop the trade (bad sizing, missing position, etc)."""
    action = TradeAction(signal["action"])
    ticker = signal["ticker"]
    if not ticker:
        raise ExecutionError("Signal has no ticker")

    with IBKRClient() as client:
        if action == TradeAction.OPEN:
            take_profits = json.loads(signal["take_profits"] or "[]")
            if not take_profits or signal["stop_loss"] is None:
                raise ExecutionError("Missing take-profit or stop-loss for OPEN signal")

            net_liq = client.net_liquidation()
            qty = open_quantity(net_liq, signal["weight"] or 0, signal["price"] or 0)
            if qty <= 0:
                raise ExecutionError(
                    f"Computed order size was 0 (net_liq={net_liq}, "
                    f"weight={signal['weight']}, price={signal['price']})"
                )

            trades = client.place_open(
                ticker=ticker,
                quantity=qty,
                entry_price=signal["price"],
                take_profit=take_profits[0],
                stop_loss=signal["stop_loss"],
            )
            return [t.order.orderId for t in trades]

        if action == TradeAction.INCREASE:
            net_liq = client.net_liquidation()
            qty = increase_quantity(
                net_liq, signal["weight_from"] or 0, signal["weight_to"] or 0, signal["price"] or 0
            )
            if qty <= 0:
                raise ExecutionError(
                    f"Computed order size was 0 (net_liq={net_liq}, "
                    f"weight {signal['weight_from']}->{signal['weight_to']}, price={signal['price']})"
                )
            trade = client.place_buy(ticker, qty)
            return [trade.order.orderId]

        if action == TradeAction.PARTIAL_CLOSE:
            current = client.position_size(ticker)
            qty = partial_close_quantity(
                current, signal["weight_from"] or 0, signal["weight_to"] or 0
            )
            if qty <= 0:
                raise ExecutionError(f"No shares to sell (current position={current})")
            trade = client.place_sell(ticker, qty)
            return [trade.order.orderId]

        if action == TradeAction.CLOSE:
            current = client.position_size(ticker)
            qty = close_quantity(current)
            if qty <= 0:
                raise ExecutionError("No open position to close")
            trade = client.place_sell(ticker, qty)
            return [trade.order.orderId]

        raise ExecutionError(f"Don't know how to execute action {action}")
