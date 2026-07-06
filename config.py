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
