from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TradeAction(str, Enum):
    OPEN = "OPEN"
    INCREASE = "INCREASE"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    CLOSE = "CLOSE"
    INFO = "INFO"


@dataclass
class TradeSignal:
    action: TradeAction
    ticker: Optional[str]
    company: Optional[str]
    title: str
    url: str
    price: Optional[float] = None
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    weight: Optional[float] = None
    take_profits: list[float] = field(default_factory=list)
    stop_loss: Optional[float] = None
    published_date: Optional[str] = None
    raw_text: str = ""
    received_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["action"] = self.action.value
        return d
