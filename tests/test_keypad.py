from datetime import datetime, timezone

from ibkr_shell.client import DryRunBrokerClient, Quote, TerminalSnapshot
from ibkr_shell.config import AppConfig
from ibkr_shell.keypad import TradingState, buy_limit, buy_market, decrease_qty, execute_binding, increase_qty, sell_limit


def make_state(quantity: int = 200, last: float = 900.0, offset: float = 0.25) -> TradingState:
    state = TradingState(quantity=quantity, limit_offset=offset)
    state.snapshot = TerminalSnapshot(
        quote=Quote(
            symbol="NVDA",
            last=last,
            bid=last - 0.01,
            ask=last + 0.01,
            updated_at=datetime.now(timezone.utc),
            source="SIM",
        )
    )
    return state


def test_market_order_messages() -> None:
    config = AppConfig(symbol="NVDA")
    broker = DryRunBrokerClient(config)
    state = make_state()

    assert "BUY 200 NVDA MKT" in buy_market(state, broker)
    assert "BUY 200 NVDA LMT @ 899.75" in buy_limit(state, broker)
    assert "SELL 200 NVDA LMT @ 900.25" in sell_limit(state, broker)


def test_quantity_adjustment() -> None:
    config = AppConfig()
    broker = DryRunBrokerClient(config)
    state = make_state(quantity=100)

    assert increase_qty(state, broker) == "Quantity -> 200"
    assert decrease_qty(state, broker) == "Quantity -> 100"
    assert decrease_qty(state, broker) == "Quantity -> 1"


def test_execute_binding_logs_activity() -> None:
    config = AppConfig(symbol="NVDA")
    broker = DryRunBrokerClient(config)
    state = make_state(quantity=100, last=500.0, offset=0.5)

    result = execute_binding("7", state, broker)

    assert result is not None
    assert "BUY 100 NVDA LMT @ 499.50" in result
    assert any("7 ->" in entry for entry in state.log.entries)
