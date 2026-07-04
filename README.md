# Bravos Research Trade Signal Engine (Phase 1)

Monitors an inbox for Bravos Research trade-alert emails, pulls the full
(subscriber-only) article, classifies the alert as a new position, partial
profit booking, close, or non-trade informational update, and extracts the
structured trade data (ticker, price, allocation weight, take-profit levels,
stop-loss). Signals are stored in `signals.db` for Phase 2 (IBKR execution +
Telegram approval) to consume.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # fill in IMAP credentials
```

If using Gmail, `IMAP_PASSWORD` must be an
[app password](https://myaccount.google.com/apppasswords), not your normal
login password.

### One-time Bravos Research login

Article pages require an active subscriber session. Run this once (opens a
visible browser window):

```bash
python fetcher.py login
```

Log in to Bravos Research in the window that opens, then press Enter in the
terminal. The session is saved to `.browser_profile/` and reused headlessly
by the main loop.

## Run

```bash
python main.py
```

Polls the inbox every `POLL_INTERVAL_SECONDS` (default 60s), fetches new
Bravos alerts, and logs/stores each parsed signal.

## Tests

```bash
python -m pytest test_parser.py -v
```

Covers the 5 real alert types Jon provided: new position (SOFI), partial
profit booking (EXEL, GS), close (LSCC, ASML), and a non-trade info update.

## Scope of this phase

- Email monitoring + filtering (ignores non-trade info emails)
- Trade type detection: OPEN / PARTIAL_CLOSE / CLOSE
- Extraction: ticker, price, weight allocation, take-profit levels, stop-loss
- Signal storage (SQLite) ready for Phase 2 to read

Not included yet (Phase 2/3): IBKR order placement, Telegram approval
buttons, backup stop-loss monitoring, VPS deployment.
