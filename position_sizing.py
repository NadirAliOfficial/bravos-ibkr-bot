"""Pure sizing math — kept separate from the IBKR client so it can be unit
tested without a live TWS/Gateway connection.
"""

import math

import config


def open_quantity(net_liquidation: float, weight: float, price: float) -> int:
    """Shares to buy for a new OPEN signal, sized off account equity."""
    if price <= 0 or weight <= 0 or net_liquidation <= 0:
        return 0
    allocation = net_liquidation * weight * config.WEIGHT_UNIT_PCT
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
