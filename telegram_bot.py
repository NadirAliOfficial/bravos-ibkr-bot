"""Sends pending trade signals to Telegram for manual approve/reject, then
executes approved ones through IBKR."""

import asyncio
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
from execution import ExecutionError, execute_signal_sync
from store import SignalStore

log = logging.getLogger("telegram-bot")

ACTION_LABELS = {
    "OPEN": "\U0001F7E2 OPEN",
    "PARTIAL_CLOSE": "\U0001F7E1 PARTIAL CLOSE",
    "CLOSE": "\U0001F534 CLOSE",
}

STATUS_LABELS = {
    "pending": "⏳ pending",
    "sent": "\U0001F4E9 awaiting your decision",
    "approved": "✅ approved",
    "rejected": "❌ rejected",
    "executed": "✅ executed",
    "failed": "⚠️ failed",
}

WELCOME_MESSAGE = (
    "\U0001F44B Welcome to the IBKR Bravos Bot!\n\n"
    "This bot watches your Bravos Research subscription for new trade alerts "
    "(new positions, partial profit bookings, and closes) and sends each one "
    "here for you to review.\n\n"
    "Tap ✅ Approve to place the trade in your Interactive Brokers account, "
    "or ❌ Reject to skip it. Nothing is ever traded without your approval.\n\n"
    "Use /status anytime to see recent signal activity."
)


def format_signal_message(signal: dict) -> str:
    action = signal["action"]
    lines = [f"{ACTION_LABELS.get(action, action)} — {signal['ticker']}", signal["title"], ""]

    if action == "OPEN":
        tps = json.loads(signal["take_profits"] or "[]")
        lines += [
            f"Entry: ${signal['price']}",
            f"Weight: {signal['weight']}",
            f"Take profit(s): {tps}",
            f"Stop loss: ${signal['stop_loss']}",
        ]
    elif action == "PARTIAL_CLOSE":
        lines += [
            f"Price: ${signal['price']}",
            f"Weight: {signal['weight_from']} → {signal['weight_to']}",
        ]
    elif action == "CLOSE":
        lines += [f"Price: ${signal['price']}"]

    return "\n".join(lines)


def approval_keyboard(signal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{signal_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{signal_id}"),
            ]
        ]
    )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store = SignalStore()
    try:
        rows = store.recent_signals(limit=5)
    finally:
        store.close()

    if not rows:
        await update.message.reply_text("No trade signals yet.")
        return

    lines = ["Recent signals:", ""]
    for row in rows:
        label = ACTION_LABELS.get(row["action"], row["action"])
        status = STATUS_LABELS.get(row["status"], row["status"])
        lines.append(f"{label} {row['ticker']} — {status}")
    await update.message.reply_text("\n".join(lines))


async def send_pending_signals(context: ContextTypes.DEFAULT_TYPE):
    store = SignalStore()
    try:
        for signal in store.pending_trade_signals():
            message = await context.bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=format_signal_message(signal),
                reply_markup=approval_keyboard(signal["id"]),
            )
            store.mark_sent(signal["id"], message.message_id)
            log.info("Sent signal %s to Telegram for approval", signal["id"])
    finally:
        store.close()


async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    decision, signal_id_str = query.data.split(":")
    signal_id = int(signal_id_str)

    store = SignalStore()
    try:
        signal = store.get(signal_id)
        if signal is None or signal["status"] != "sent":
            await query.edit_message_text(query.message.text + "\n\n(already handled)")
            return

        if decision == "reject":
            store.mark_rejected(signal_id)
            await query.edit_message_text(query.message.text + "\n\n❌ Rejected")
            return

        try:
            order_ids = await asyncio.to_thread(execute_signal_sync, signal)
        except ExecutionError as e:
            store.mark_failed(signal_id, str(e))
            await query.edit_message_text(query.message.text + f"\n\n⚠️ Failed: {e}")
            return
        except Exception as e:
            store.mark_failed(signal_id, str(e))
            await query.edit_message_text(
                query.message.text + f"\n\n⚠️ IBKR error: {e}"
            )
            log.exception("Unexpected error executing signal %s", signal_id)
            return

        store.mark_executed(signal_id, order_ids)
        await query.edit_message_text(
            query.message.text + f"\n\n✅ Executed (orders {order_ids})"
        )
    finally:
        store.close()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CallbackQueryHandler(handle_decision))
    app.job_queue.run_repeating(
        send_pending_signals, interval=config.APPROVAL_POLL_INTERVAL_SECONDS, first=0
    )
    app.run_polling()


if __name__ == "__main__":
    main()
