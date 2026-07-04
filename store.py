import json
import sqlite3

import config
from models import TradeAction, TradeSignal

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    ticker TEXT,
    company TEXT,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    price REAL,
    weight_from REAL,
    weight_to REAL,
    weight REAL,
    take_profits TEXT,
    stop_loss REAL,
    published_date TEXT,
    raw_text TEXT,
    received_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
"""


class SignalStore:
    def __init__(self, db_path: str = config.SIGNALS_DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def already_seen(self, url: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM signals WHERE url = ?", (url,))
        return cur.fetchone() is not None

    def save(self, signal: TradeSignal) -> int:
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO signals
                (action, ticker, company, title, url, price, weight_from, weight_to,
                 weight, take_profits, stop_loss, published_date, raw_text, received_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                signal.action.value,
                signal.ticker,
                signal.company,
                signal.title,
                signal.url,
                signal.price,
                signal.weight_from,
                signal.weight_to,
                signal.weight,
                json.dumps(signal.take_profits),
                signal.stop_loss,
                signal.published_date,
                signal.raw_text,
                signal.received_at,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def pending_trade_signals(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM signals WHERE status = 'pending' AND action != ? ORDER BY id",
            (TradeAction.INFO.value,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
