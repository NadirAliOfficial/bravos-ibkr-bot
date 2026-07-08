import json

from telegram_bot import STATUS_LABELS, WELCOME_MESSAGE, approval_keyboard, format_signal_message

OPEN_SIGNAL = {
    "action": "OPEN",
    "ticker": "HROW",
    "title": "Initiating Long on Harrow Inc ($HROW) | Breakout",
    "price": 43.43,
    "weight": 3.0,
    "take_profits": json.dumps([50.0, 54.0, 60.0]),
    "stop_loss": 40.0,
}

PARTIAL_SIGNAL = {
    "action": "PARTIAL_CLOSE",
    "ticker": "EXEL",
    "title": "Booking Partial Profits in Exelixis, Inc ($EXEL) | Profit Booking",
    "price": 56.09,
    "weight_from": 6.0,
    "weight_to": 4.0,
}

CLOSE_SIGNAL = {
    "action": "CLOSE",
    "ticker": "LSCC",
    "title": "Closing Lattice Semiconductor Corporation ($LSCC) | Breakdown",
    "price": 140.0,
}

INCREASE_SIGNAL = {
    "action": "INCREASE",
    "ticker": "HROW",
    "title": "Increasing Exposure to Harrow Inc ($HROW) | Technical Strength",
    "price": 45.05,
    "weight_from": 3.0,
    "weight_to": 6.0,
}


def test_format_open_signal_includes_key_fields():
    text = format_signal_message(OPEN_SIGNAL)
    assert "HROW" in text
    assert "$43.43" in text
    assert "50.0, 54.0, 60.0" in text
    assert "$40.0" in text


def test_format_signal_message_escapes_html_special_chars():
    signal = dict(OPEN_SIGNAL, ticker="A&B", title="Trend <up> & strong")
    text = format_signal_message(signal)
    assert "A&amp;B" in text
    assert "&lt;up&gt;" in text


def test_format_partial_close_shows_weight_transition():
    text = format_signal_message(PARTIAL_SIGNAL)
    assert "6.0 → 4.0" in text


def test_format_increase_shows_weight_transition():
    text = format_signal_message(INCREASE_SIGNAL)
    assert "3.0 → 6.0" in text
    assert "$45.05" in text


def test_format_close_shows_price():
    text = format_signal_message(CLOSE_SIGNAL)
    assert "$140.0" in text


def test_approval_keyboard_callback_data():
    kb = approval_keyboard(42)
    buttons = kb.inline_keyboard[0]
    assert buttons[0].callback_data == "approve:42"
    assert buttons[1].callback_data == "reject:42"


def test_welcome_message_mentions_approve_reject():
    assert "Approve" in WELCOME_MESSAGE
    assert "Reject" in WELCOME_MESSAGE


def test_status_labels_cover_all_lifecycle_states():
    for state in ("pending", "sent", "approved", "rejected", "executed", "failed"):
        assert state in STATUS_LABELS
