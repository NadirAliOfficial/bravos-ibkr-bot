"""Phase 1 pipeline: poll email -> fetch gated article -> parse trade signal -> store.

Trade execution and Telegram approval are Phase 2/3 and are not part of this loop.
"""

import logging
import time

import config
from email_watcher import EmailWatcher
from fetcher import ArticleFetcher
from parser import parse_trade
from store import SignalStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bravos-bot")


def run_once(watcher: EmailWatcher, fetcher: ArticleFetcher, store: SignalStore):
    alerts = watcher.fetch_unseen()
    for alert in alerts:
        if store.already_seen(alert.url):
            watcher.mark_seen(alert.uid)
            continue

        log.info("New alert: %s", alert.title)
        body_text = fetcher.fetch_article_text(alert.url)
        signal = parse_trade(alert.title, alert.url, body_text)
        store.save(signal)
        watcher.mark_seen(alert.uid)

        if signal.action.value == "INFO":
            log.info("  -> informational update, skipped")
        else:
            log.info(
                "  -> %s %s price=%s weight=%s/%s tp=%s sl=%s",
                signal.action.value,
                signal.ticker,
                signal.price,
                signal.weight_from or signal.weight,
                signal.weight_to,
                signal.take_profits,
                signal.stop_loss,
            )


def main():
    watcher = EmailWatcher()
    watcher.connect()
    store = SignalStore()
    try:
        with ArticleFetcher() as fetcher:
            if not fetcher.ensure_logged_in():
                log.warning(
                    "Bravos Research session not logged in. Run `python fetcher.py login` first."
                )
            while True:
                try:
                    run_once(watcher, fetcher, store)
                except Exception:
                    # IMAP connections get dropped by the mail server after
                    # sitting idle (Gmail in particular). Without reconnecting
                    # here, every future cycle would hit the same dead socket
                    # and silently never see new mail again.
                    log.exception("Error during poll cycle — reconnecting IMAP")
                    try:
                        watcher.close()
                    except Exception:
                        pass
                    watcher = EmailWatcher()
                    watcher.connect()
                time.sleep(config.POLL_INTERVAL_SECONDS)
    finally:
        watcher.close()
        store.close()


if __name__ == "__main__":
    main()
