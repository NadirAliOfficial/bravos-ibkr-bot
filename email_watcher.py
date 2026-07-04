"""Polls an IMAP inbox for Bravos Research trade notification emails."""

import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header

import config

SUBJECT_RE = re.compile(
    r"the post:\s*(.+?)\s*has been published", re.I
)
URL_RE = re.compile(r"https?://bravosresearch\.com/news-feed/[^\s\)>\]]+", re.I)


@dataclass
class RawAlert:
    uid: bytes
    title: str
    url: str


def _decode(value) -> str:
    if value is None:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _get_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""


class EmailWatcher:
    def __init__(self):
        self.conn: imaplib.IMAP4_SSL | None = None

    def connect(self):
        self.conn = imaplib.IMAP4_SSL(config.IMAP_HOST, config.IMAP_PORT)
        self.conn.login(config.IMAP_USER, config.IMAP_PASSWORD)
        self.conn.select(config.IMAP_FOLDER)

    def close(self):
        if self.conn:
            try:
                self.conn.close()
                self.conn.logout()
            except Exception:
                pass

    def fetch_unseen(self) -> list[RawAlert]:
        assert self.conn is not None
        status, data = self.conn.search(
            None, f'(UNSEEN FROM "{config.BRAVOS_SENDER_FILTER}")'
        )
        if status != "OK":
            return []

        alerts = []
        for uid in data[0].split():
            status, msg_data = self.conn.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode(msg.get("Subject"))
            body = _get_body(msg)

            title_m = SUBJECT_RE.search(subject) or SUBJECT_RE.search(body)
            url_m = URL_RE.search(body)

            if not title_m or not url_m:
                continue

            alerts.append(RawAlert(uid=uid, title=title_m.group(1).strip(), url=url_m.group(0)))
        return alerts

    def mark_seen(self, uid: bytes):
        assert self.conn is not None
        self.conn.store(uid, "+FLAGS", "\\Seen")
