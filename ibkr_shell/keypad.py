from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .client import BrokerClient, OrderRequest, TerminalSnapshot
from .config import AppConfig


@dataclass(slots=True)
class ActivityLog:
    entries: list[str] = field(default_factory=list)
    capacity: int = 12

    def add(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.entries.append(f"[{stamp}] {message}")
        self.entries = self.entries[-self.capacity :]


@dataclass(slots=True)
class TradingState:
    quantity: int
    limit_offset: float = 0.05
    snapshot: TerminalSnapshot | None = None
    log: ActivityLog = field(default_factory=ActivityLog)

    @property
    def last_price(self) -> float:
        return self.snapshot.quote.last if self.snapshot is not None else 0.0


Handler = Callable[[TradingState, BrokerClient], str]


def buy_market(state: TradingState, broker: BrokerClient) -> str:
    return broker.place_order(OrderRequest(side="BUY", quantity=state.quantity, order_type="MKT"))


def sell_market(state: TradingState, broker: BrokerClient) -> str:
    return broker.place_order(OrderRequest(side="SELL", quantity=state.quantity, order_type="MKT"))


def buy_limit(state: TradingState, broker: BrokerClient) -> str:
    price = round(max(0.01, state.last_price - state.limit_offset), 2)
    return broker.place_order(
        OrderRequest(side="BUY", quantity=state.quantity, order_type="LMT", limit_price=price)
    )


def sell_limit(state: TradingState, broker: BrokerClient) -> str:
    price = round(max(0.01, state.last_price + state.limit_offset), 2)
    return broker.place_order(
        OrderRequest(side="SELL", quantity=state.quantity, order_type="LMT", limit_price=price)
    )


def cancel_all(state: TradingState, broker: BrokerClient) -> str:
    return broker.cancel_all()


def increase_qty(state: TradingState, broker: BrokerClient) -> str:
    state.quantity += 100
    return f"Quantity -> {state.quantity}"


def decrease_qty(state: TradingState, broker: BrokerClient) -> str:
    state.quantity = max(1, state.quantity - 100)
    return f"Quantity -> {state.quantity}"


def tighten_offset(state: TradingState, broker: BrokerClient) -> str:
    state.limit_offset = max(0.01, round(state.limit_offset - 0.01, 2))
    return f"Limit offset -> {state.limit_offset:.2f}"


def widen_offset(state: TradingState, broker: BrokerClient) -> str:
    state.limit_offset = round(state.limit_offset + 0.01, 2)
    return f"Limit offset -> {state.limit_offset:.2f}"


KEYPAD_BINDINGS: dict[str, tuple[str, Handler]] = {
    "8": ("市价买入", buy_market),
    "2": ("市价卖出", sell_market),
    "7": ("限价买入(last-offset)", buy_limit),
    "1": ("限价卖出(last+offset)", sell_limit),
    "0": ("全部撤单", cancel_all),
    "+": ("增加数量(+100)", increase_qty),
    "-": ("减少数量(-100)", decrease_qty),
    "4": ("缩小限价偏移", tighten_offset),
    "6": ("扩大限价偏移", widen_offset),
}


def execute_binding(key: str, state: TradingState, broker: BrokerClient) -> str | None:
    binding = KEYPAD_BINDINGS.get(key)
    if binding is None:
        return None
    _, handler = binding
    result = handler(state, broker)
    state.log.add(f"{key} -> {result}")
    return result


def help_lines(config: AppConfig) -> list[str]:
    lines = [
        f"{config.symbol}  {'SIM' if config.dry_run else 'LIVE'}  keypad trading",
        "8 买 / 2 卖 / 7 买限 / 1 卖限 / 0 全撤 / +/- 调数量 / 4/6 调offset / q 退出",
    ]
    return lines
