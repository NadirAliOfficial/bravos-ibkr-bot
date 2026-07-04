# Bravos Research Trade Signal Bot for Interactive Brokers

Turns Bravos Research email trade alerts into structured, machine-readable
trade signals for Interactive Brokers automation. Monitors an inbox for
alert emails, pulls the full subscriber-only article, classifies the alert
(new position, partial profit booking, close, or non-trade informational
update), and extracts the structured trade data: ticker, entry price,
portfolio allocation weight, take-profit levels, and stop-loss.

## Features

- IMAP inbox polling with sender filtering — ignores non-trade info emails
- Authenticated fetch of subscriber-gated article pages via Playwright
- Regex-based trade classification: OPEN / PARTIAL_CLOSE / CLOSE
- Extraction of ticker, price, allocation weight, take-profit levels, stop-loss
- SQLite-backed signal store, ready for a downstream execution engine
- Test suite built from real alert samples (new position, partial profit
  booking, full close, informational update)

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

Covers 5 real-world alert types: new position (SOFI), partial profit
booking (EXEL, GS), close (LSCC, ASML), and a non-trade info update.

## Roadmap

This repo covers notification parsing and signal generation. Planned next:

- Interactive Brokers order placement via the TWS API
- Telegram approve/reject workflow before any order is sent
- Backup stop-loss monitoring (Bravos doesn't always publish one)
- VPS deployment for always-on monitoring
