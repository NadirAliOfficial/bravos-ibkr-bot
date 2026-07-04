import re

from models import TradeAction, TradeSignal

OPEN_TITLE_RE = re.compile(r"\b(Initiating|Opening)\b", re.I)
PARTIAL_TITLE_RE = re.compile(r"\b(Booking Partial Profits|Trimming|Reducing)\b", re.I)
CLOSE_TITLE_RE = re.compile(r"\bClosing\b", re.I)

TICKER_RE = re.compile(r"\(\$([A-Z]{1,6}(?:\.[A-Z])?)\)")
COMPANY_RE = re.compile(r"^(.*?)\s*\(\$[A-Z]{1,6}(?:\.[A-Z])?\)")

PRICE_AT_RE = re.compile(r"\bat\s*\$([\d,]+\.?\d*)")
ENTRY_LINE_RE = re.compile(r"Entry:\s*\$([\d,]+\.?\d*)", re.I)
TP_LINE_RE = re.compile(r"Take Profit \(TP\):\s*(.+)", re.I)
SL_LINE_RE = re.compile(r"Suggested Stop Loss \(SL\):\s*\$([\d,]+\.?\d*)", re.I)
WEIGHT_ALLOC_RE = re.compile(r"weight allocation of\s*(\d+(?:\.\d+)?)", re.I)
WEIGHT_FROM_TO_RE = re.compile(
    r"weight of\s*(\d+(?:\.\d+)?)\s*to(?:\s*a weight of)?\s*(\d+(?:\.\d+)?)", re.I
)
WEIGHT_FROM_TO_ALT_RE = re.compile(
    r"weight from\s*(\d+(?:\.\d+)?)\s*to\s*(\d+(?:\.\d+)?)", re.I
)
DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def classify_action(title: str) -> TradeAction:
    if PARTIAL_TITLE_RE.search(title):
        return TradeAction.PARTIAL_CLOSE
    if CLOSE_TITLE_RE.search(title):
        return TradeAction.CLOSE
    if OPEN_TITLE_RE.search(title):
        return TradeAction.OPEN
    return TradeAction.INFO


def extract_ticker(title: str) -> tuple[str | None, str | None]:
    m = TICKER_RE.search(title)
    ticker = m.group(1) if m else None
    company = None
    cm = COMPANY_RE.search(title)
    if cm:
        company = cm.group(1).strip()
    return ticker, company


def parse_trade(title: str, url: str, body_text: str) -> TradeSignal:
    action = classify_action(title)
    ticker, company = extract_ticker(title)

    signal = TradeSignal(
        action=action,
        ticker=ticker,
        company=company,
        title=title.strip(),
        url=url,
        raw_text=body_text,
    )

    date_m = DATE_RE.search(body_text)
    if date_m:
        signal.published_date = date_m.group(1)

    if action == TradeAction.INFO:
        return signal

    price_m = ENTRY_LINE_RE.search(body_text) or PRICE_AT_RE.search(body_text)
    if price_m:
        signal.price = _to_float(price_m.group(1))

    if action == TradeAction.OPEN:
        wm = WEIGHT_ALLOC_RE.search(body_text)
        if wm:
            signal.weight = _to_float(wm.group(1))

        tp_m = TP_LINE_RE.search(body_text)
        if tp_m:
            signal.take_profits = [
                _to_float(p) for p in re.findall(r"\$?(\d[\d,]*\.?\d*)", tp_m.group(1))
            ]

        sl_m = SL_LINE_RE.search(body_text)
        if sl_m:
            signal.stop_loss = _to_float(sl_m.group(1))

    elif action == TradeAction.PARTIAL_CLOSE:
        wm = WEIGHT_FROM_TO_RE.search(body_text) or WEIGHT_FROM_TO_ALT_RE.search(body_text)
        if wm:
            signal.weight_from = _to_float(wm.group(1))
            signal.weight_to = _to_float(wm.group(2))

    return signal
