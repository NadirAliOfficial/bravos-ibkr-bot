"""Client-facing demo: runs the test suite, then shows the real parsed signal
already captured from a live Bravos Research alert."""

import json
import subprocess
import sys

from store import SignalStore

SEP = "=" * 64


def run_tests():
    print(SEP)
    print("STEP 1 — Unit tests against 5 real Bravos alert samples")
    print(SEP, flush=True)
    subprocess.run([sys.executable, "-m", "pytest", "test_parser.py", "-v"], check=False)


def show_live_signal():
    print()
    print(SEP)
    print("STEP 2 — Real signal parsed from a live Bravos Research alert")
    print(SEP)
    store = SignalStore()
    rows = store.pending_trade_signals()
    if not rows:
        print("No signals captured yet.")
        store.close()
        return

    row = rows[-1]
    tps = json.loads(row["take_profits"] or "[]")
    print(f"Alert title:     {row['title']}")
    print(f"Source URL:      {row['url']}")
    print(f"Published:       {row['published_date']}")
    print()
    print(f"Action:          {row['action']}")
    print(f"Ticker:          {row['ticker']}")
    print(f"Entry price:     ${row['price']}")
    print(f"Weight:          {row['weight']}")
    print(f"Take profits:    {tps}")
    print(f"Stop loss:       ${row['stop_loss']}")
    print()
    print("(Signal parsed automatically from the article's raw text — no manual entry.)")
    store.close()


if __name__ == "__main__":
    run_tests()
    show_live_signal()
