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
    status TEXT NOT NULL DEFAULT 'pending',
    telegram_message_id INTEGER,
    decided_at TEXT,
    ibkr_order_ids TEXT,
    error TEXT
);
"""

# Columns added after the original Phase 1 schema — applied via ALTER TABLE so
# an existing signals.db from Phase 1 upgrades in place instead of needing a
# fresh database.
_MIGRATION_COLUMNS = [
    ("telegram_message_id", "INTEGER"),
    ("decided_at", "TEXT"),
    ("ibkr_order_ids", "TEXT"),
    ("error", "TEXT"),
    # JSON list of [chat_id, message_id] pairs — one signal can be sent to
    # several Telegram recipients at once (see config.TELEGRAM_CHAT_IDS).
    ("telegram_messages", "TEXT"),
]


class SignalStore:
    def __init__(self, db_path: str = config.SIGNALS_DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(signals)")}
        for name, coltype in _MIGRATION_COLUMNS:
            if name not in existing:
                self.conn.execute(f"ALTER TABLE signals ADD COLUMN {name} {coltype}")

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

    def recent_signals(self, limit: int = 5) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM signals WHERE action != ? ORDER BY id DESC LIMIT ?",
            (TradeAction.INFO.value, limit),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get(self, signal_id: int) -> dict | None:
        cur = self.conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
        row = cur.fetchone()
        if row is None:
            return None
        cols = [c[0] for c in cur.description]
        return dict(zip(cols, row))

    def find_by_order_id(self, order_id: int) -> dict | None:
        cur = self.conn.execute("SELECT * FROM signals WHERE ibkr_order_ids IS NOT NULL")
        cols = [c[0] for c in cur.description]
        for row in cur.fetchall():
            record = dict(zip(cols, row))
            if order_id in json.loads(record["ibkr_order_ids"] or "[]"):
                return record
        return None

    def mark_sent(self, signal_id: int, chat_message_pairs: list[tuple[str, int]]):
        self.conn.execute(
            "UPDATE signals SET status = 'sent', telegram_messages = ? WHERE id = ?",
            (json.dumps(chat_message_pairs), signal_id),
        )
        self.conn.commit()

    def mark_rejected(self, signal_id: int):
        self.conn.execute(
            "UPDATE signals SET status = 'rejected', decided_at = datetime('now') WHERE id = ?",
            (signal_id,),
        )
        self.conn.commit()

    def mark_executed(self, signal_id: int, ibkr_order_ids: list[int]):
        self.conn.execute(
            """UPDATE signals
               SET status = 'executed', decided_at = datetime('now'), ibkr_order_ids = ?
               WHERE id = ?""",
            (json.dumps(ibkr_order_ids), signal_id),
        )
        self.conn.commit()

    def mark_failed(self, signal_id: int, error: str):
        self.conn.execute(
            """UPDATE signals
               SET status = 'failed', decided_at = datetime('now'), error = ?
               WHERE id = ?""",
            (error, signal_id),
        )
        self.conn.commit()
