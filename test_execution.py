import json
from types import SimpleNamespace

import pytest

from accounts import AccountConfig
from execution import ExecutionError, _execute_quant_for_account, _execute_tactical_for_account
from models import TradeAction


class FakeTrade:
    def __init__(self, order_id):
        self.order = SimpleNamespace(orderId=order_id)


class FakeClient:
    def __init__(self, positions=None, prices=None):
        self.positions = positions or {}  # {(ticker, account): shares}
        self.prices = prices or {}  # {ticker: price}
        self.calls = []
        self._next_order_id = 1

    def _order_id(self):
        oid = self._next_order_id
        self._next_order_id += 1
        return oid

    def position_size(self, ticker, account=""):
        return self.positions.get((ticker, account), 0)

    def current_price(self, ticker):
        return self.prices.get(ticker, 0)

    def place_open(self, ticker, quantity, entry_price, take_profit, stop_loss, account=""):
        self.calls.append(("open", ticker, quantity, account))
        return [FakeTrade(self._order_id()) for _ in range(3)]

    def place_buy(self, ticker, quantity, account=""):
        self.calls.append(("buy", ticker, quantity, account))
        return FakeTrade(self._order_id())

    def place_sell(self, ticker, quantity, account=""):
        self.calls.append(("sell", ticker, quantity, account))
        return FakeTrade(self._order_id())


ACCOUNT = AccountConfig("U1", "Test (Tactical)", "primary", "fixed", 10_000, 100, 0)
QUANT_ACCOUNT = AccountConfig("U1", "Test (Quant)", "primary", "fixed", 10_000, 0, 100)


def test_tactical_open_places_bracket_sized_off_capital():
    client = FakeClient()
    signal = {
        "ticker": "AAPL",
        "price": 200.0,
        "weight": 1.0,
        "take_profits": json.dumps([210.0]),
        "stop_loss": 190.0,
    }
    order_ids = _execute_tactical_for_account(client, TradeAction.OPEN, signal, ACCOUNT, net_liq=0)
    assert len(order_ids) == 3
    assert client.calls[0][0] == "open"
    assert client.calls[0][3] == "U1"


def test_tactical_open_missing_sl_raises():
    client = FakeClient()
    signal = {"ticker": "AAPL", "price": 200.0, "weight": 1.0, "take_profits": "[]", "stop_loss": None}
    with pytest.raises(ExecutionError):
        _execute_tactical_for_account(client, TradeAction.OPEN, signal, ACCOUNT, net_liq=0)


def test_tactical_increase_buys_delta():
    client = FakeClient()
    signal = {"ticker": "HROW", "price": 45.05, "weight_from": 3.0, "weight_to": 6.0}
    order_ids = _execute_tactical_for_account(
        client, TradeAction.INCREASE, signal, ACCOUNT, net_liq=0
    )
    assert len(order_ids) == 1
    assert client.calls[0] == ("buy", "HROW", client.calls[0][2], "U1")


def test_tactical_partial_close_sells_fraction():
    client = FakeClient(positions={("EXEL", "U1"): 300})
    signal = {"ticker": "EXEL", "weight_from": 6.0, "weight_to": 4.0}
    _execute_tactical_for_account(client, TradeAction.PARTIAL_CLOSE, signal, ACCOUNT, net_liq=0)
    assert client.calls[0] == ("sell", "EXEL", 100, "U1")


def test_tactical_close_sells_everything():
    client = FakeClient(positions={("LSCC", "U1"): 150})
    signal = {"ticker": "LSCC"}
    _execute_tactical_for_account(client, TradeAction.CLOSE, signal, ACCOUNT, net_liq=0)
    assert client.calls[0] == ("sell", "LSCC", 150, "U1")


def test_tactical_close_no_position_raises():
    client = FakeClient()
    signal = {"ticker": "LSCC"}
    with pytest.raises(ExecutionError):
        _execute_tactical_for_account(client, TradeAction.CLOSE, signal, ACCOUNT, net_liq=0)


def test_quant_cash_to_moderate_buys_qqq():
    client = FakeClient(prices={"QQQ": 500.0})
    signal = {"quant_level": "MODERATE", "ticker": "QQQ"}
    _execute_quant_for_account(client, signal, QUANT_ACCOUNT, net_liq=0)
    assert client.calls == [("buy", "QQQ", 20, "U1")]  # $10,000 / $500 = 20


def test_quant_moderate_to_aggressive_switches_qqq_to_tqqq():
    client = FakeClient(positions={("QQQ", "U1"): 20}, prices={"TQQQ": 80.0})
    signal = {"quant_level": "AGGRESSIVE", "ticker": "TQQQ"}
    _execute_quant_for_account(client, signal, QUANT_ACCOUNT, net_liq=0)
    assert ("sell", "QQQ", 20, "U1") in client.calls
    assert ("buy", "TQQQ", 125, "U1") in client.calls  # $10,000 / $80 = 125


def test_quant_to_cash_sells_everything():
    client = FakeClient(positions={("QQQ", "U1"): 0, ("TQQQ", "U1"): 125})
    signal = {"quant_level": "CASH", "ticker": None}
    _execute_quant_for_account(client, signal, QUANT_ACCOUNT, net_liq=0)
    assert client.calls == [("sell", "TQQQ", 125, "U1")]


def test_quant_no_change_needed_raises():
    client = FakeClient(positions={("QQQ", "U1"): 20}, prices={"QQQ": 500.0})
    signal = {"quant_level": "MODERATE", "ticker": "QQQ"}
    with pytest.raises(ExecutionError):
        _execute_quant_for_account(client, signal, QUANT_ACCOUNT, net_liq=0)
