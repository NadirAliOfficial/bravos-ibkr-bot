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
IBKR_ACCOUNT = os.getenv("IBKR_ACCOUNT", "")

# --- Phase 3: multi-account, multi-login ---

# One IBKR login can hold several accounts (e.g. Jon's TFSA/RRSP/Non-reg all
# under one username) — that's one "gateway". A spouse or other family
# member's account needs its own login, which means its own headless Gateway
# process on a different port/clientId. Each entry here is one running
# Gateway instance; accounts.json points each account at one of these by name.
IBKR_GATEWAYS = {
    "primary": {
        "host": IBKR_HOST,
        "port": IBKR_PORT,
        "client_id": IBKR_CLIENT_ID,
    },
    "wife": {
        "host": os.getenv("IBKR_WIFE_HOST", "127.0.0.1"),
        "port": int(os.getenv("IBKR_WIFE_PORT", "4003")),
        "client_id": int(os.getenv("IBKR_WIFE_CLIENT_ID", "27")),
    },
}

# The fill watcher holds its own persistent connection per gateway, alongside
# the short-lived ones execution.py opens per order — each IBKR API client on
# the same Gateway needs a distinct clientId, or Gateway rejects the
# connection. One fill_watcher.py process runs per gateway (see
# `python fill_watcher.py <gateway-name>`).
IBKR_WATCHER_CLIENT_IDS = {
    "primary": int(os.getenv("IBKR_WATCHER_CLIENT_ID", "18")),
    "wife": int(os.getenv("IBKR_WIFE_WATCHER_CLIENT_ID", "28")),
}

ACCOUNTS_CONFIG_PATH = os.getenv("ACCOUNTS_CONFIG_PATH", "accounts.json")

# Bravos "weight" is a 1-10 sizing scale, not a literal percentage. This maps
# one weight point to a fraction of an account's *allocated* capital (not the
# whole account) — confirm the right multiplier with the client before going
# live; 0.02 (weight 5 = 10% of allocated capital) is a placeholder default.
WEIGHT_UNIT_PCT = float(os.getenv("WEIGHT_UNIT_PCT", "0.02"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Comma-separated list — every signal and fill notification goes to all of
# these chats. Any one recipient can approve/reject; the others' copies get
# updated to match so nobody double-approves.
TELEGRAM_CHAT_IDS = [c.strip() for c in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]

APPROVAL_POLL_INTERVAL_SECONDS = int(os.getenv("APPROVAL_POLL_INTERVAL_SECONDS", "30"))
