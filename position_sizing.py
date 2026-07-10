"""Pure sizing math — kept separate from the IBKR client so it can be unit
tested without a live TWS/Gateway connection.

Every function below takes a `capital` figure rather than assuming "the whole
account" — callers pass in the *allocated* capital for one account/strategy
combination (see accounts.py: tactical_capital() / quant_capital()), not
necessarily the account's full net liquidation.
"""

import math

import config


def open_quantity(capital: float, weight: float, price: float) -> int:
    """Shares to buy for a new OPEN signal, sized off allocated capital."""
    if price <= 0 or weight <= 0 or capital <= 0:
        return 0
    allocation = capital * weight * config.WEIGHT_UNIT_PCT
    return math.floor(allocation / price)


def increase_quantity(capital: float, weight_from: float, weight_to: float, price: float) -> int:
    """Additional shares to buy for an INCREASE signal — sized off the weight
    delta (new target minus old), not the full new weight, since the original
    allocation is already held."""
    if price <= 0 or capital <= 0 or weight_to <= weight_from:
        return 0
    allocation = capital * (weight_to - weight_from) * config.WEIGHT_UNIT_PCT
    return math.floor(allocation / price)


def partial_close_quantity(current_shares: int, weight_from: float, weight_to: float) -> int:
    """Shares to sell for a PARTIAL_CLOSE signal, proportional to the weight drop."""
    if current_shares <= 0 or weight_from <= 0 or weight_to >= weight_from:
        return 0
    fraction = (weight_from - weight_to) / weight_from
    return round(current_shares * fraction)


def close_quantity(current_shares: int) -> int:
    """Shares to sell for a full CLOSE signal — the entire position."""
    return max(current_shares, 0)


def quant_target_shares(capital: float, price: float, level: str) -> int:
    """Target share count to hold in the Quant Portfolio's instrument for a
    given signal level. Bravos's own guidance is to take the *full* position
    associated with each signal, not scale in gradually — so this is an
    absolute target, not a delta. CASH means 0 (fully out); the caller is
    responsible for actually rebalancing (selling whatever's currently held
    if the instrument changed, e.g. QQQ -> TQQQ)."""
    if level == "CASH" or price <= 0 or capital <= 0:
        return 0
    return math.floor(capital / price)
