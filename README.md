# Bravos Research Trade Signal Bot for Interactive Brokers

Turns Bravos Research trade alerts into structured, machine-readable trade
signals and executes them across multiple Interactive Brokers accounts, with
a Telegram approval step before anything trades.

Bravos runs two independent portfolios:

- **Tactical Portfolio** — individual stock/ETF trades (new position, add to
  position, partial profit booking, close), each with a 0-100 weight
- **Quant Portfolio** — a single-instrument regime signal (Cash / Moderate /
  Aggressive) that holds QQQ (Moderate), TQQQ (Aggressive, 3x leveraged), or
  nothing (Cash)

Both are parsed from the same email feed and can be routed independently to
different accounts.

## Features

- IMAP inbox polling with sender filtering — ignores non-trade info emails
- Authenticated fetch of subscriber-gated article pages via Playwright
- Classification of both Tactical (OPEN / INCREASE / PARTIAL_CLOSE / CLOSE)
  and Quant (Cash / Moderate / Aggressive) signal types
- Multi-account routing: each account has its own capital allocation (fixed
  dollar amount or % of account value) and its own Tactical/Quant split
- Multi-login support: a family member's account on a separate IBKR login
  runs its own headless Gateway instance, addressed as a distinct "gateway"
- Telegram approve/reject workflow, with a per-account results breakdown
  after execution, sent to multiple recipients at once
- Interactive Brokers order placement via `ib_insync` — bracket orders for
  new Tactical positions, plain buy/sell for adjustments, and full rebalance
  (sell old instrument, buy new) for Quant signal changes
- A persistent fill watcher (one per gateway) that notifies Telegram when an
  order actually fills, not just when it's submitted
- SQLite-backed signal store
- Test suite covering parsing, position sizing, multi-account execution
  fan-out, and Telegram formatting — no live IBKR connection required

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env             # fill in credentials
cp accounts.example.json accounts.json   # fill in real account IDs/allocations
```

If using Gmail, `IMAP_PASSWORD` must be an
[app password](https://myaccount.google.com/apppasswords), not your normal
login password.

### Account configuration (`accounts.json`)

One entry per IBKR account:

```json
{
  "account_id": "U1234567",
  "label": "Jon TFSA",
  "gateway": "primary",
  "capital_mode": "percent",
  "capital_value": 80,
  "tactical_split": 80,
  "quant_split": 20
}
```

- `gateway` — which running Gateway instance this account lives under
  (`primary` for Jon's own login, `wife` for a separate family login — see
  `config.IBKR_GATEWAYS`)
- `capital_mode` — `"fixed"` (a dollar amount) or `"percent"` (% of the
  account's net liquidation, scales automatically as the account grows)
- `tactical_split` / `quant_split` — how the allocated capital divides
  between the two strategies for this account (must not exceed 100 combined)

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

Four processes run side by side, sharing the same `signals.db`:

```bash
python main.py                # polls the inbox, parses alerts, stores signals
python telegram_bot.py        # sends new signals to Telegram, executes on approval
python fill_watcher.py primary  # notifies Telegram when orders on the primary gateway fill
python fill_watcher.py wife     # same, for the wife gateway (once that login exists)
```

`main.py` polls the inbox every `POLL_INTERVAL_SECONDS` (default 60s).
`telegram_bot.py` checks for newly-parsed signals every
`APPROVAL_POLL_INTERVAL_SECONDS` (default 30s), sends each one to every
configured Telegram recipient with Approve/Reject buttons, and on approval
fans the trade out to every account configured for that signal's strategy.
Each `fill_watcher.py` instance needs a running Gateway for its `gateway`
argument (TWS or IB Gateway, API enabled, per the host/port in
`config.IBKR_GATEWAYS`).

### Order sizing

Bravos gives a 1-10 "weight" per Tactical trade, not a literal percentage.
`config.WEIGHT_UNIT_PCT` converts that to a fraction of an account's
*allocated* capital (default: weight 5 = 10% of what's allocated to that
account/strategy). **Confirm the right multiplier with the client before
trading live** — this is a placeholder default, not a confirmed value.

**Tactical**: new positions (`OPEN`) place a bracket order — a limit buy plus
one take-profit leg and one stop-loss leg. IBKR's native bracket only
supports a single TP/SL pair per parent order — when Bravos gives multiple
take-profit levels, the nearest one is used. `INCREASE` buys the weight
delta. `PARTIAL_CLOSE` and `CLOSE` place plain market sells, sized off the
live IBKR position and the weight ratio in the alert.

**Quant**: on every signal change, the target account's QQQ/TQQQ holdings
are rebalanced to the *full* position for the new signal (per Bravos's own
guidance — not a gradual scale-in). If the target instrument changed (e.g.
Moderate → Aggressive), the old instrument is sold first, then the new one
bought to the sized target.

## Tests

```bash
python -m pytest -v
```

Covers real-world Tactical and Quant alert samples, position-sizing math
(including the Quant rebalance target), multi-account execution fan-out
against a fake IBKR client, and Telegram message formatting. Real IBKR order
placement itself isn't covered by these tests — it requires a live TWS/IB
Gateway connection to exercise.

## Roadmap

Phases 1-3 (notification parsing for both portfolios, multi-account IBKR
execution, Telegram approval, fill notifications) are covered here. Planned
next:

- Backup stop-loss monitoring (Bravos doesn't always publish one on Tactical
  alerts)
- Second Gateway instance for the `wife` login once that account exists
