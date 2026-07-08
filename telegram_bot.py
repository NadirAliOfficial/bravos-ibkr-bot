"""Sends pending trade signals to Telegram for manual approve/reject, then
executes approved ones through IBKR."""

import asyncio
import json
import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
from execution import ExecutionError, execute_signal_sync
from store import SignalStore

log = logging.getLogger("telegram-bot")

ACTION_LABELS = {
    "OPEN": "\U0001F7E2 OPEN",
    "INCREASE": "\U0001F7E2 INCREASE",
    "PARTIAL_CLOSE": "\U0001F7E1 PARTIAL CLOSE",
    "CLOSE": "\U0001F534 CLOSE",
}

STATUS_LABELS = {
    "pending": "Pending",
    "sent": "Awaiting decision",
    "approved": "Approved",
    "rejected": "Rejected",
    "executed": "Executed",
    "failed": "Failed",
}

WELCOME_MESSAGE = (
    "<b>IBKR Bravos Bot</b>\n\n"
    "This bot watches your Bravos Research subscription for new trade alerts "
    "(new positions, partial profit bookings, and closes) and sends each one "
    "here for review.\n\n"
    "Approve places the trade in your Interactive Brokers account. Reject "
    "skips it. Nothing is ever traded without your approval.\n\n"
    "Use /status to see recent signal activity."
)


def format_signal_message(signal: dict) -> str:
    action = signal["action"]
    ticker = escape(signal["ticker"] or "")
    title = escape(signal["title"] or "")
    lines = [f"{ACTION_LABELS.get(action, action)}  <b>{ticker}</b>", f"<i>{title}</i>", ""]

    if action == "OPEN":
        tps = json.loads(signal["take_profits"] or "[]")
        tps_str = ", ".join(str(v) for v in tps) if tps else "—"
        lines += [
            f"<b>Entry:</b> ${signal['price']}",
            f"<b>Weight:</b> {signal['weight']}",
            f"<b>Take profit(s):</b> {tps_str}",
            f"<b>Stop loss:</b> ${signal['stop_loss']}",
        ]
    elif action in ("PARTIAL_CLOSE", "INCREASE"):
        lines += [
            f"<b>Price:</b> ${signal['price']}",
            f"<b>Weight:</b> {signal['weight_from']} → {signal['weight_to']}",
        ]
    elif action == "CLOSE":
        lines += [f"<b>Price:</b> ${signal['price']}"]

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
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode=ParseMode.HTML)


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store = SignalStore()
    try:
        rows = store.recent_signals(limit=5)
    finally:
        store.close()

    if not rows:
        await update.message.reply_text("No trade signals yet.")
        return

    lines = ["<b>Recent signals</b>", ""]
    for row in rows:
        label = ACTION_LABELS.get(row["action"], row["action"])
        status = STATUS_LABELS.get(row["status"], row["status"])
        lines.append(f"{label}  <b>{escape(row['ticker'] or '')}</b> — {status}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def send_pending_signals(context: ContextTypes.DEFAULT_TYPE):
    store = SignalStore()
    try:
        for signal in store.pending_trade_signals():
            text = format_signal_message(signal)
            keyboard = approval_keyboard(signal["id"])
            sent = []
            for chat_id in config.TELEGRAM_CHAT_IDS:
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
                sent.append([chat_id, message.message_id])
            store.mark_sent(signal["id"], sent)
            log.info("Sent signal %s to %d Telegram recipient(s)", signal["id"], len(sent))
    finally:
        store.close()


async def _sync_outcome(context: ContextTypes.DEFAULT_TYPE, signal: dict, text: str):
    """Removes the Approve/Reject buttons and posts the outcome in every chat
    this signal was sent to, so all recipients see the same result and nobody
    approves twice from a stale copy of the alert."""
    for chat_id, message_id in json.loads(signal["telegram_messages"] or "[]"):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=None
            )
        except Exception:
            log.exception(
                "Failed to clear buttons for signal %s in chat %s", signal["id"], chat_id
            )
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception:
            log.exception(
                "Failed to send outcome for signal %s to chat %s", signal["id"], chat_id
            )


async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    decision, signal_id_str = query.data.split(":")
    signal_id = int(signal_id_str)

    store = SignalStore()
    try:
        signal = store.get(signal_id)
        if signal is None or signal["status"] != "sent":
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                "<b>Status:</b> Already handled", parse_mode=ParseMode.HTML
            )
            return

        if decision == "reject":
            store.mark_rejected(signal_id)
            await _sync_outcome(context, signal, "<b>Status:</b> Rejected")
            return

        try:
            order_ids = await asyncio.to_thread(execute_signal_sync, signal)
        except ExecutionError as e:
            store.mark_failed(signal_id, str(e))
            await _sync_outcome(context, signal, f"<b>Status:</b> Failed\n<i>{escape(str(e))}</i>")
            return
        except Exception as e:
            store.mark_failed(signal_id, str(e))
            await _sync_outcome(
                context, signal, f"<b>Status:</b> IBKR error\n<i>{escape(str(e))}</i>"
            )
            log.exception("Unexpected error executing signal %s", signal_id)
            return

        store.mark_executed(signal_id, order_ids)
        order_ids_str = ", ".join(str(i) for i in order_ids)
        await _sync_outcome(
            context, signal, f"<b>Status:</b> Executed\n<b>Order IDs:</b> {order_ids_str}"
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
