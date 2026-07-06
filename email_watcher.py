"""Polls an IMAP inbox for Bravos Research trade notification emails."""

import email
import email.message
import html
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header

import config

SUBJECT_RE = re.compile(
    r"the post:\s*(.+?)\s*has been published", re.I | re.S
)
URL_RE = re.compile(r"https?://bravosresearch\.com/news-feed/[^\s\)>\]\"']+", re.I)

_STYLE_SCRIPT_RE = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.I | re.S)
_BLOCK_TAG_RE = re.compile(r"</(p|div|tr|li|br|h[1-6])\s*>|<br\s*/?>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


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


def _html_to_text(raw_html: str) -> str:
    text = _STYLE_SCRIPT_RE.sub("", raw_html)
    text = _BLOCK_TAG_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text


def _get_body(msg: email.message.Message) -> str:
    plain, rich = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            decoded = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/plain" and not plain:
                plain = decoded
            elif ctype == "text/html" and not rich:
                rich = decoded
    else:
        payload = msg.get_payload(decode=True)
        decoded = payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""
        if msg.get_content_type() == "text/html":
            rich = decoded
        else:
            plain = decoded

    if plain:
        return plain
    if rich:
        return _html_to_text(rich)
    return ""


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
            status, msg_data = self.conn.fetch(uid, "(BODY.PEEK[])")
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
