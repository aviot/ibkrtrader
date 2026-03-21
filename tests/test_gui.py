from ibkr_shell.client import Quote, TerminalSnapshot
from ibkr_shell.gui import KEY_LABELS, format_quote
from datetime import datetime, timezone


def test_format_quote_returns_strings() -> None:
    snapshot = TerminalSnapshot(
        quote=Quote(
            symbol="AAPL",
            last=123.45,
            bid=123.4,
            ask=123.5,
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source="SIM",
        )
    )

    view = format_quote(snapshot)

    assert view.symbol == "AAPL"
    assert view.last == "123.45"
    assert view.bid == "123.40"
    assert view.ask == "123.50"
    assert view.source == "SIM"


def test_hotkey_labels_cover_expected_bindings() -> None:
    assert KEY_LABELS["8"] == "市价买入"
    assert KEY_LABELS["0"] == "全部撤单"
    assert "+" in KEY_LABELS
