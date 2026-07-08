from types import SimpleNamespace

from fill_watcher import format_fill_message


def _make_trade_fill(symbol="AAPL", order_id=42, side="BOT", shares=100, price=200.5):
    trade = SimpleNamespace(
        contract=SimpleNamespace(symbol=symbol),
        order=SimpleNamespace(orderId=order_id),
    )
    fill = SimpleNamespace(execution=SimpleNamespace(side=side, shares=shares, price=price))
    return trade, fill


def test_format_fill_message_buy():
    trade, fill = _make_trade_fill(side="BOT", shares=100, price=200.5)
    text = format_fill_message(trade, fill)
    assert "Bought 100" in text
    assert "AAPL" in text
    assert "$200.5" in text
    assert "42" in text


def test_format_fill_message_sell():
    trade, fill = _make_trade_fill(side="SLD", shares=50, price=56.09)
    text = format_fill_message(trade, fill)
    assert "Sold 50" in text
    assert "$56.09" in text


def test_format_fill_message_escapes_symbol():
    trade, fill = _make_trade_fill(symbol="A&B")
    text = format_fill_message(trade, fill)
    assert "A&amp;B" in text
