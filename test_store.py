from models import TradeAction, TradeSignal
from store import SignalStore


def _make_store(tmp_path):
    return SignalStore(db_path=str(tmp_path / "signals.db"))


def _tactical_signal(url="http://x/1"):
    return TradeSignal(
        action=TradeAction.OPEN,
        ticker="AAPL",
        company="Apple",
        title="t",
        url=url,
        price=200.0,
        weight=1,
        take_profits=[210],
        stop_loss=190,
    )


def _quant_signal(url="http://x/quant"):
    return TradeSignal(
        action=TradeAction.QUANT,
        ticker="QQQ",
        company=None,
        title="Model Signal (Moderate)",
        url=url,
        quant_level="MODERATE",
    )


def test_save_and_get_round_trips_all_fields(tmp_path):
    store = _make_store(tmp_path)
    sid = store.save(_tactical_signal())
    row = store.get(sid)
    assert row["ticker"] == "AAPL"
    assert row["status"] == "pending"
    store.close()


def test_save_and_get_round_trips_quant_level(tmp_path):
    """Regression test: quant_level was added to the TradeSignal dataclass
    but the actual DB column/INSERT was forgotten, so every real QUANT signal
    threw a KeyError the moment the Telegram bot tried to read it back."""
    store = _make_store(tmp_path)
    sid = store.save(_quant_signal())
    row = store.get(sid)
    assert row["quant_level"] == "MODERATE"
    assert row["action"] == "QUANT"
    store.close()


def test_pending_trade_signals_includes_quant(tmp_path):
    store = _make_store(tmp_path)
    store.save(_quant_signal())
    pending = store.pending_trade_signals()
    assert len(pending) == 1
    assert pending[0]["quant_level"] == "MODERATE"
    store.close()


def test_mark_executed_sets_status_from_account_results(tmp_path):
    store = _make_store(tmp_path)
    sid = store.save(_tactical_signal())
    store.mark_executed(sid, {"U1": {"status": "executed", "order_ids": [1, 2, 3]}})
    assert store.get(sid)["status"] == "executed"
    store.close()


def test_mark_executed_all_failed_sets_status_failed(tmp_path):
    store = _make_store(tmp_path)
    sid = store.save(_tactical_signal())
    store.mark_executed(sid, {"U1": {"status": "failed", "error": "no shares"}})
    assert store.get(sid)["status"] == "failed"
    store.close()


def test_find_by_order_id_across_accounts(tmp_path):
    store = _make_store(tmp_path)
    sid = store.save(_tactical_signal())
    store.mark_executed(
        sid,
        {
            "U1": {"status": "executed", "order_ids": [1, 2]},
            "U2": {"status": "executed", "order_ids": [3, 4]},
        },
    )
    assert store.find_by_order_id(3)["id"] == sid
    assert store.find_by_order_id(999) is None
    store.close()


def test_already_seen(tmp_path):
    store = _make_store(tmp_path)
    store.save(_tactical_signal(url="http://x/dup"))
    assert store.already_seen("http://x/dup") is True
    assert store.already_seen("http://x/not-there") is False
    store.close()
