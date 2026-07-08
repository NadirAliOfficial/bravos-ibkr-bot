import os

from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
BRAVOS_SENDER_FILTER = os.getenv("BRAVOS_SENDER_FILTER", "bravosresearch.com")
BRAVOS_EMAIL = os.getenv("BRAVOS_EMAIL", "")
BRAVOS_PASSWORD = os.getenv("BRAVOS_PASSWORD", "")

BROWSER_PROFILE_DIR = os.getenv("BROWSER_PROFILE_DIR", ".browser_profile")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

SIGNALS_DB_PATH = os.getenv("SIGNALS_DB_PATH", "signals.db")

# --- Phase 2: IBKR + Telegram ---

IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "7497"))  # 7497 TWS paper, 7496 TWS live
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "17"))
# The fill watcher holds its own persistent connection alongside the
# short-lived one execution.py opens per order — each IBKR API client needs a
# distinct clientId, or Gateway rejects the second connection.
IBKR_WATCHER_CLIENT_ID = int(os.getenv("IBKR_WATCHER_CLIENT_ID", "18"))
IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT", "")

# Bravos "weight" is a 1-10 sizing scale, not a literal percentage. This maps
# one weight point to a fraction of total account equity — confirm the right
# multiplier with the client before going live; 0.02 (weight 5 = 10% of
# portfolio) is a placeholder default.
WEIGHT_UNIT_PCT = float(os.getenv("WEIGHT_UNIT_PCT", "0.02"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

APPROVAL_POLL_INTERVAL_SECONDS = int(os.getenv("APPROVAL_POLL_INTERVAL_SECONDS", "30"))
