"""Per-account configuration: which IBKR login an account lives under, how
much capital is allocated to the strategy, and how that capital splits
between the Tactical and Quant portfolios.

Loaded from a JSON file (accounts.json by default) rather than .env, since
this is a list of structured records, not flat scalars.
"""

import json
from dataclasses import dataclass

import config

VALID_CAPITAL_MODES = ("fixed", "percent")


@dataclass
class AccountConfig:
    account_id: str
    label: str
    gateway: str  # key into config.IBKR_GATEWAYS
    capital_mode: str  # "fixed" or "percent"
    capital_value: float  # dollars if fixed, 0-100 if percent
    tactical_split: float  # 0-100, percent of allocated capital
    quant_split: float  # 0-100, percent of allocated capital

    def __post_init__(self):
        if self.capital_mode not in VALID_CAPITAL_MODES:
            raise ValueError(
                f"Account {self.account_id}: capital_mode must be one of "
                f"{VALID_CAPITAL_MODES}, got {self.capital_mode!r}"
            )
        if self.gateway not in config.IBKR_GATEWAYS:
            raise ValueError(
                f"Account {self.account_id}: unknown gateway {self.gateway!r}, "
                f"expected one of {list(config.IBKR_GATEWAYS)}"
            )
        if self.tactical_split + self.quant_split > 100:
            raise ValueError(
                f"Account {self.account_id}: tactical_split + quant_split "
                f"({self.tactical_split} + {self.quant_split}) exceeds 100"
            )


def load_accounts(path: str = None) -> list[AccountConfig]:
    path = path or config.ACCOUNTS_CONFIG_PATH
    with open(path) as f:
        raw = json.load(f)
    accounts = [AccountConfig(**entry) for entry in raw]

    # execution.py keys per-account results by account_id — a duplicate would
    # silently overwrite an earlier account's outcome rather than erroring.
    seen = set()
    for a in accounts:
        if a.account_id in seen:
            raise ValueError(f"Duplicate account_id in accounts config: {a.account_id!r}")
        seen.add(a.account_id)

    return accounts


def allocated_capital(account: AccountConfig, net_liquidation: float) -> float:
    """Total capital this account devotes to the strategy (before the
    Tactical/Quant split)."""
    if account.capital_mode == "fixed":
        return account.capital_value
    return net_liquidation * account.capital_value / 100


def tactical_capital(account: AccountConfig, net_liquidation: float) -> float:
    return allocated_capital(account, net_liquidation) * account.tactical_split / 100


def quant_capital(account: AccountConfig, net_liquidation: float) -> float:
    return allocated_capital(account, net_liquidation) * account.quant_split / 100


def accounts_for_tactical(accounts: list[AccountConfig]) -> list[AccountConfig]:
    return [a for a in accounts if a.tactical_split > 0]


def accounts_for_quant(accounts: list[AccountConfig]) -> list[AccountConfig]:
    return [a for a in accounts if a.quant_split > 0]
