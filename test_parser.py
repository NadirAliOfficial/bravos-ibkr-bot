from models import TradeAction
from parser import parse_trade

EXEL_BODY = """
07/02/2026
Save post
We are trimming our position in Exelixis Inc ($EXEL) at $56.09, and reducing our allocation from a weight of 6 to a weight of 4 as the stock continues to advance higher.

Following the strong move since our entry, we believe it is prudent to lock in a portion of the gains while maintaining the majority of the position.

At the same time, we are raising our stop from $41.25 to $47.00, moving it above our original entry price.

This position was entered on April 22, 2026, at $46.67, and we increased our exposure on May 06, 2026, at $46.78.
"""

LSCC_BODY = """
06/26/2026
Save post
already read
We are closing our position in Lattice Semiconductor Corporation ($LSCC) at $140, as the stock has triggered our predefined stop loss after breaking below the rising trendline support that had been guiding the uptrend.

This position was entered on April 08, 2026, at $104.9, we booked partial profits on April 20, 2026, at $118.51, and we booked further partial profits on April 24, 2026, at $124.7.
"""

GS_BODY = """
06/26/2026
Save post
We are booking partial profits in Goldman Sachs ($GS) at $1,036.6, and reducing the weight from 5 to 4, after the stock broke below the rising trendline support that had been guiding the advance over the past several weeks.

This position was entered on May 20, 2026, at $965.75.
"""

SOFI_BODY = """
07/01/2026
Save post
already read
We are initiating a trade in SoFi Technologies Inc ($SOFI) at $18.49, with a weight allocation of 5.

Our 3 take profit levels are $21.5, $22.5, and $25. We'll re-evaluate the position around $16.75.

Entry: $18.49
Take Profit (TP): $21.5, $22.5, and $25
Suggested Stop Loss (SL): $16.75
"""

NVDA_BODY = """
07/10/2026
Save Post
We are initiating a position in NVIDIA (NVDA) at $209.50 with a weight of 5, a stop at $190, and price targets of $250, $275, and $300.

We recently exited our previous position in NVIDIA after the stock broke below our shorter-term support level and violated the risk management parameters established when the trade was initiated. Since then, however, the stock

Entry: $209.50

Take Profit (TP): $250, $275, and $300

Suggested Stop Loss (SL): $190

Weight Allocation: 5

Traders can get exposure to $NVDA through Interactive Brokers
"""

ASML_BODY = """
07/02/2026
Save post
already read
We are closing our position in ASML Holding (ASML) at $1,775 as price has broken below a recent level of support and the shorter-term moving average that had acted as support throughout the most recent pullback.

This trade was entered on May 21, 2026, at $1,564.48, we booked partial profits on June 09, 2026, at $1,825.06, and we booked further partial profits on June 30, 2026, at $1,985.
"""

QUANT_MODERATE_BODY = """
06/30/2026
Save Post
The Tactical Signal Model is updating today from CASH to MODERATE

This model is separate from our discretionary service
The model tells us the broader market environment. Our Active Trade Ideas are managed separately, with their own entry points, position sizing, and stops.
"""

QUANT_AGGRESSIVE_BODY = """
05/19/2026
Save Post
The Tactical Signal Model is updating today from MODERATE to AGGRESSIVE.

This model is separate from our discretionary service
"""

HROW_INCREASE_BODY = """
07/07/2026
Save Post
Already Read
We are increasing our position in Harrow Inc (HROW) at $45.05, and increasing the weight from 3 to 6 as the stock continues to hold above its recent breakout level and confirms the strength of the setup.

Since breaking above resistance, Harrow has successfully held the breakout area as support, reinforcing the constructive technical picture that we highlighted when initiating the starter position.

This position was entered on July 06, 2026, at $43.43.
"""

INFO_BODY = """
07/03/2026
Save post
Markets continue to digest the latest inflation data with no clear directional bias emerging across major indices.
"""


def test_partial_close_exel():
    s = parse_trade(
        "Booking Partial Profits in Exelixis, Inc ($EXEL) | Profit Booking",
        "https://bravosresearch.com/news-feed/booking-partial-profits-in-exelixis-inc-exel-profit-booking/",
        EXEL_BODY,
    )
    assert s.action == TradeAction.PARTIAL_CLOSE
    assert s.ticker == "EXEL"
    assert s.price == 56.09
    assert s.weight_from == 6
    assert s.weight_to == 4


def test_close_lscc():
    s = parse_trade(
        "Closing Lattice Semiconductor Corporation ($LSCC) | Breakdown",
        "https://bravosresearch.com/news-feed/closing-lattice-semiconductor-corporation-lscc-breakdown/",
        LSCC_BODY,
    )
    assert s.action == TradeAction.CLOSE
    assert s.ticker == "LSCC"
    assert s.price == 140


def test_partial_close_gs():
    s = parse_trade(
        "Booking Partial Profits in Goldman Sachs ($GS) | Profit Booking",
        "https://bravosresearch.com/news-feed/booking-partial-profits-in-goldman-sachs-gs-profit-booking/",
        GS_BODY,
    )
    assert s.action == TradeAction.PARTIAL_CLOSE
    assert s.ticker == "GS"
    assert s.price == 1036.6
    assert s.weight_from == 5
    assert s.weight_to == 4


def test_open_sofi():
    s = parse_trade(
        "Initiating Long on SoFi Technologies Inc ($SOFI) | Breakout",
        "https://bravosresearch.com/news-feed/initiating-long-on-sofi-technologies-inc-sofi-breakout/",
        SOFI_BODY,
    )
    assert s.action == TradeAction.OPEN
    assert s.ticker == "SOFI"
    assert s.price == 18.49
    assert s.weight == 5
    assert s.take_profits == [21.5, 22.5, 25]
    assert s.stop_loss == 16.75


def test_open_nvda_weight_allocation_colon_format():
    """Regression test: this real alert uses 'Weight Allocation: 5' (colon
    footer format) instead of 'weight allocation of 5' — the original regex
    only matched the latter and silently returned weight=None."""
    s = parse_trade(
        "Initiating Long on Nvidia ($NVDA) | Breakout",
        "https://bravosresearch.com/news-feed/initiating-long-on-nvidia-nvda-breakout-2/",
        NVDA_BODY,
    )
    assert s.action == TradeAction.OPEN
    assert s.ticker == "NVDA"
    assert s.price == 209.50
    assert s.weight == 5
    assert s.take_profits == [250.0, 275.0, 300.0]
    assert s.stop_loss == 190.0


def test_close_asml():
    s = parse_trade(
        "Closing ASML Holdings ($ASML) | Breakdown",
        "https://bravosresearch.com/news-feed/closing-asml-holdings-asml-breakdown-2/",
        ASML_BODY,
    )
    assert s.action == TradeAction.CLOSE
    assert s.ticker == "ASML"
    assert s.price == 1775


def test_increase_hrow():
    s = parse_trade(
        "Increasing Exposure to Harrow Inc ($HROW) | Technical Strength",
        "https://bravosresearch.com/news-feed/increasing-exposure-to-harrow-inc-hrow-technical-strength/",
        HROW_INCREASE_BODY,
    )
    assert s.action == TradeAction.INCREASE
    assert s.ticker == "HROW"
    assert s.price == 45.05
    assert s.weight_from == 3
    assert s.weight_to == 6


def test_quant_moderate_signal():
    s = parse_trade(
        "Model Signal (Moderate)",
        "https://bravosresearch.com/model-signal/model-signal-moderate-5/",
        QUANT_MODERATE_BODY,
    )
    assert s.action == TradeAction.QUANT
    assert s.quant_level == "MODERATE"
    assert s.ticker == "QQQ"


def test_quant_aggressive_signal():
    s = parse_trade(
        "Model Signal (Aggressive)",
        "https://bravosresearch.com/model-signal/model-signal-aggressive-2/",
        QUANT_AGGRESSIVE_BODY,
    )
    assert s.action == TradeAction.QUANT
    assert s.quant_level == "AGGRESSIVE"
    assert s.ticker == "TQQQ"


def test_quant_cash_signal():
    s = parse_trade(
        "Model Signal (Cash)",
        "https://bravosresearch.com/model-signal/model-signal-cash-4/",
        "The Tactical Signal Model is updating today from MODERATE to CASH.",
    )
    assert s.action == TradeAction.QUANT
    assert s.quant_level == "CASH"
    assert s.ticker is None


def test_info_update_ignored():
    s = parse_trade(
        "Weekly Market Recap",
        "https://bravosresearch.com/news-feed/weekly-market-recap/",
        INFO_BODY,
    )
    assert s.action == TradeAction.INFO
    assert s.price is None
