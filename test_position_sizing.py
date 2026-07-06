import config
from position_sizing import close_quantity, open_quantity, partial_close_quantity


def test_open_quantity_basic(monkeypatch):
    monkeypatch.setattr(config, "WEIGHT_UNIT_PCT", 0.02)
    # $100,000 account, weight 5 -> 10% allocation = $10,000, price $50 -> 200 shares
    assert open_quantity(net_liquidation=100_000, weight=5, price=50) == 200


def test_open_quantity_floors_fractional_shares(monkeypatch):
    monkeypatch.setattr(config, "WEIGHT_UNIT_PCT", 0.02)
    # $10,000 * 0.02 * 3 = $600 allocation / $43.43 = 13.8.. -> 13 shares
    assert open_quantity(net_liquidation=10_000, weight=3, price=43.43) == 13


def test_open_quantity_zero_on_bad_input():
    assert open_quantity(0, 5, 50) == 0
    assert open_quantity(100_000, 0, 50) == 0
    assert open_quantity(100_000, 5, 0) == 0


def test_partial_close_quantity_matches_weight_ratio():
    # weight 6 -> 4 means sell 1/3 of the position
    assert partial_close_quantity(current_shares=300, weight_from=6, weight_to=4) == 100


def test_partial_close_quantity_gs_example():
    # weight 5 -> 4 means sell 1/5 of the position
    assert partial_close_quantity(current_shares=100, weight_from=5, weight_to=4) == 20


def test_partial_close_quantity_invalid_returns_zero():
    assert partial_close_quantity(0, 5, 4) == 0
    assert partial_close_quantity(100, 0, 4) == 0
    assert partial_close_quantity(100, 4, 5) == 0  # weight increased, not a partial close


def test_close_quantity_returns_full_position():
    assert close_quantity(150) == 150
    assert close_quantity(0) == 0
