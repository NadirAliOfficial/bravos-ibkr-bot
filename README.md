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
- Telegram approve/reject workflow for every signal before any order is sent
- Interactive Brokers order placement via `ib_insync` (bracket orders for new
  positions, plain sells for partial/full closes)
- Test suite built from real alert samples (new position, partial profit
  booking, full close, informational update) plus position-sizing and
  Telegram message formatting unit tests

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

Two processes run side by side, sharing the same `signals.db`:

```bash
python main.py           # polls the inbox, parses alerts, stores signals
python telegram_bot.py   # sends new signals to Telegram, executes on approval
```

`main.py` polls the inbox every `POLL_INTERVAL_SECONDS` (default 60s).
`telegram_bot.py` checks for newly-parsed signals every
`APPROVAL_POLL_INTERVAL_SECONDS` (default 30s), sends each one to Telegram
with Approve/Reject buttons, and on approval places the order through IBKR
(TWS or IB Gateway must be running with the API enabled on `IBKR_PORT`).

### IBKR order sizing

Bravos gives a 1-10 "weight" per trade, not a literal percentage. `config.py`
converts that to a fraction of account equity via `WEIGHT_UNIT_PCT`
(default: weight 5 = 10% of the account). **Confirm the right multiplier
with the client before trading live** — this is a placeholder default, not a
confirmed value.

New positions (`OPEN`) place a bracket order: a limit buy plus one
take-profit leg and one stop-loss leg. IBKR's native bracket only supports a
single TP/SL pair per parent order — when Bravos gives multiple take-profit
levels, the nearest one is used. `PARTIAL_CLOSE` and `CLOSE` place plain
market sells, sized off the live IBKR position and the weight ratio in the
alert.

## Tests

```bash
python -m pytest -v
```

Covers 5 real-world alert types (new position, partial profit booking, full
close, non-trade info update), position-sizing math for all three signal
types, and Telegram message formatting/keyboard construction. IBKR order
placement itself isn't covered by these tests — it requires a live TWS/IB
Gateway connection to exercise.

## Roadmap

Phases 1 and 2 (notification parsing, signal generation, IBKR execution,
Telegram approval) are covered here. Planned next:

- Backup stop-loss monitoring (Bravos doesn't always publish one)
- VPS deployment for always-on monitoring
