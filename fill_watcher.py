"""Keeps a persistent IBKR connection open and notifies Telegram whenever an
order actually fills — separate from execution.py, which only confirms an
order was submitted, not when (or whether) it fills.
"""

import logging
from html import escape

import httpx
from ib_insync import IB

import config
from store import SignalStore

log = logging.getLogger("fill-watcher")

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"


def format_fill_message(trade, fill) -> str:
    side = "Bought" if fill.execution.side == "BOT" else "Sold"
    symbol = escape(trade.contract.symbol)
    return (
        f"<b>Order Filled</b>\n\n"
        f"{side} {fill.execution.shares} <b>{symbol}</b> @ ${fill.execution.price}\n"
        f"Order ID: {trade.order.orderId}"
    )


def send_telegram_message(text: str):
    for chat_id in config.TELEGRAM_CHAT_IDS:
        httpx.post(
            TELEGRAM_API,
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        ).raise_for_status()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ib = IB()
    ib.connect(config.IBKR_HOST, config.IBKR_PORT, clientId=config.IBKR_WATCHER_CLIENT_ID)
    store = SignalStore()

    def on_fill(trade, fill):
        signal = store.find_by_order_id(trade.order.orderId)
        signal_note = f" (signal #{signal['id']})" if signal else ""
        log.info(
            "Fill: order %s %s %s @ %s%s",
            trade.order.orderId,
            fill.execution.side,
            trade.contract.symbol,
            fill.execution.price,
            signal_note,
        )
        try:
            send_telegram_message(format_fill_message(trade, fill))
        except Exception:
            log.exception("Failed to send fill notification for order %s", trade.order.orderId)

    ib.execDetailsEvent += on_fill
    log.info("Watching for IBKR order fills...")
    ib.run()


if __name__ == "__main__":
    main()
