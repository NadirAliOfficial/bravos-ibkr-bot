"""Turns an approved signal into IBKR orders across every account configured
for that signal's strategy (Tactical or Quant).

Kept as plain synchronous functions (not async) so this can run in its own
thread via asyncio.to_thread() — ib_insync manages its own event loop, and
mixing that with python-telegram-bot's asyncio loop in the same thread is a
recipe for conflicts.
"""

import json
from collections import defaultdict

from accounts import AccountConfig, accounts_for_quant, accounts_for_tactical, load_accounts, quant_capital, tactical_capital
from ibkr_client import IBKRClient
from models import TradeAction
from position_sizing import (
    close_quantity,
    increase_quantity,
    open_quantity,
    partial_close_quantity,
    quant_target_shares,
)


class ExecutionError(Exception):
    pass


def _execute_tactical_for_account(
    client: IBKRClient, action: TradeAction, signal: dict, account: AccountConfig, net_liq: float
) -> list[int]:
    ticker = signal["ticker"]
    capital = tactical_capital(account, net_liq)

    if action == TradeAction.OPEN:
        take_profits = json.loads(signal["take_profits"] or "[]")
        if not take_profits or signal["stop_loss"] is None:
            raise ExecutionError("Missing take-profit or stop-loss for OPEN signal")

        qty = open_quantity(capital, signal["weight"] or 0, signal["price"] or 0)
        if qty <= 0:
            raise ExecutionError(
                f"Computed order size was 0 (capital={capital}, "
                f"weight={signal['weight']}, price={signal['price']})"
            )

        trades = client.place_open(
            ticker=ticker,
            quantity=qty,
            entry_price=signal["price"],
            take_profit=take_profits[0],
            stop_loss=signal["stop_loss"],
            account=account.account_id,
        )
        return [t.order.orderId for t in trades]

    if action == TradeAction.INCREASE:
        qty = increase_quantity(
            capital, signal["weight_from"] or 0, signal["weight_to"] or 0, signal["price"] or 0
        )
        if qty <= 0:
            raise ExecutionError(
                f"Computed order size was 0 (capital={capital}, "
                f"weight {signal['weight_from']}->{signal['weight_to']}, price={signal['price']})"
            )
        trade = client.place_buy(ticker, qty, account=account.account_id)
        return [trade.order.orderId]

    if action == TradeAction.PARTIAL_CLOSE:
        current = client.position_size(ticker, account=account.account_id)
        qty = partial_close_quantity(current, signal["weight_from"] or 0, signal["weight_to"] or 0)
        if qty <= 0:
            raise ExecutionError(f"No shares to sell (current position={current})")
        trade = client.place_sell(ticker, qty, account=account.account_id)
        return [trade.order.orderId]

    if action == TradeAction.CLOSE:
        current = client.position_size(ticker, account=account.account_id)
        qty = close_quantity(current)
        if qty <= 0:
            raise ExecutionError("No open position to close")
        trade = client.place_sell(ticker, qty, account=account.account_id)
        return [trade.order.orderId]

    raise ExecutionError(f"Don't know how to execute Tactical action {action}")


def _execute_quant_for_account(
    client: IBKRClient, signal: dict, account: AccountConfig, net_liq: float
) -> list[int]:
    level = signal["quant_level"]
    target_instrument = signal["ticker"]  # "QQQ" / "TQQQ" / None for CASH
    capital = quant_capital(account, net_liq)
    order_ids = []

    # Bravos's own guidance: take the full position for the new signal, not a
    # gradual scale-in. A Moderate -> Aggressive move means selling QQQ and
    # buying TQQQ, not holding both — clear out whichever instrument isn't
    # this signal's target.
    for other in ("QQQ", "TQQQ"):
        if other == target_instrument:
            continue
        held = client.position_size(other, account=account.account_id)
        if held > 0:
            trade = client.place_sell(other, held, account=account.account_id)
            order_ids.append(trade.order.orderId)

    if target_instrument:
        price = client.current_price(target_instrument)
        target_shares = quant_target_shares(capital, price, level)
        current = client.position_size(target_instrument, account=account.account_id)
        delta = target_shares - current
        if delta > 0:
            trade = client.place_buy(target_instrument, delta, account=account.account_id)
            order_ids.append(trade.order.orderId)
        elif delta < 0:
            trade = client.place_sell(target_instrument, -delta, account=account.account_id)
            order_ids.append(trade.order.orderId)

    if not order_ids:
        raise ExecutionError("No rebalancing needed — already at target position")

    return order_ids


def execute_signal_sync(signal: dict) -> dict[str, dict]:
    """Fans a signal out to every account configured for its strategy
    (Tactical or Quant). Returns one result per account:
        {"U1234567": {"status": "executed", "order_ids": [10, 11, 12]}}
        {"U2345678": {"status": "failed", "error": "..."}}
    Raises ExecutionError only when NO accounts are configured for this
    signal's strategy at all — that's a config problem, not a per-account one.
    """
    action = TradeAction(signal["action"])
    is_quant = action == TradeAction.QUANT

    if not is_quant and not signal["ticker"]:
        raise ExecutionError("Signal has no ticker")

    all_accounts = load_accounts()
    relevant = accounts_for_quant(all_accounts) if is_quant else accounts_for_tactical(all_accounts)
    if not relevant:
        strategy = "Quant" if is_quant else "Tactical"
        raise ExecutionError(f"No accounts configured for {strategy}")

    by_gateway: dict[str, list[AccountConfig]] = defaultdict(list)
    for acct in relevant:
        by_gateway[acct.gateway].append(acct)

    results: dict[str, dict] = {}
    for gateway_name, accts in by_gateway.items():
        with IBKRClient(gateway=gateway_name) as client:
            for acct in accts:
                net_liq = client.net_liquidation(acct.account_id)
                try:
                    if is_quant:
                        order_ids = _execute_quant_for_account(client, signal, acct, net_liq)
                    else:
                        order_ids = _execute_tactical_for_account(
                            client, action, signal, acct, net_liq
                        )
                    results[acct.account_id] = {"status": "executed", "order_ids": order_ids}
                except Exception as e:
                    results[acct.account_id] = {"status": "failed", "error": str(e)}

    return results
