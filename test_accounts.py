import json

import pytest

from accounts import (
    AccountConfig,
    accounts_for_quant,
    accounts_for_tactical,
    allocated_capital,
    load_accounts,
    quant_capital,
    tactical_capital,
)


def test_fixed_allocation_ignores_net_liquidation():
    acct = AccountConfig("U1", "Test", "primary", "fixed", 10_000, 50, 50)
    assert allocated_capital(acct, net_liquidation=999_999) == 10_000


def test_percent_allocation_scales_with_net_liquidation():
    acct = AccountConfig("U1", "Test", "primary", "percent", 80, 50, 50)
    assert allocated_capital(acct, net_liquidation=10_000) == 8_000
    assert allocated_capital(acct, net_liquidation=20_000) == 16_000


def test_tactical_and_quant_capital_split_allocated_capital():
    acct = AccountConfig("U1", "Test", "primary", "fixed", 10_000, 80, 20)
    assert tactical_capital(acct, net_liquidation=0) == 8_000
    assert quant_capital(acct, net_liquidation=0) == 2_000


def test_invalid_capital_mode_rejected():
    with pytest.raises(ValueError):
        AccountConfig("U1", "Test", "primary", "bogus", 100, 50, 50)


def test_unknown_gateway_rejected():
    with pytest.raises(ValueError):
        AccountConfig("U1", "Test", "not-a-real-gateway", "fixed", 100, 50, 50)


def test_split_over_100_rejected():
    with pytest.raises(ValueError):
        AccountConfig("U1", "Test", "primary", "fixed", 100, 70, 40)


def test_accounts_for_tactical_and_quant_filter_zero_splits():
    accounts = [
        AccountConfig("U1", "Tactical only", "primary", "fixed", 100, 100, 0),
        AccountConfig("U2", "Quant only", "primary", "fixed", 100, 0, 100),
        AccountConfig("U3", "Both", "primary", "fixed", 100, 50, 50),
    ]
    tactical = {a.account_id for a in accounts_for_tactical(accounts)}
    quant = {a.account_id for a in accounts_for_quant(accounts)}
    assert tactical == {"U1", "U3"}
    assert quant == {"U2", "U3"}


def test_load_accounts_from_file(tmp_path):
    data = [
        {
            "account_id": "U1",
            "label": "Test",
            "gateway": "primary",
            "capital_mode": "fixed",
            "capital_value": 5000,
            "tactical_split": 100,
            "quant_split": 0,
        }
    ]
    path = tmp_path / "accounts.json"
    path.write_text(json.dumps(data))
    accounts = load_accounts(str(path))
    assert len(accounts) == 1
    assert accounts[0].account_id == "U1"
    assert accounts[0].capital_value == 5000


def test_load_accounts_rejects_duplicate_account_id(tmp_path):
    entry = {
        "account_id": "U1",
        "label": "Test",
        "gateway": "primary",
        "capital_mode": "fixed",
        "capital_value": 5000,
        "tactical_split": 100,
        "quant_split": 0,
    }
    path = tmp_path / "accounts.json"
    path.write_text(json.dumps([entry, dict(entry, label="Duplicate")]))
    with pytest.raises(ValueError):
        load_accounts(str(path))
