from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import random
from typing import Protocol

from .config import AppConfig

try:
    from ib_insync import IB, LimitOrder, MarketOrder, Stock
except ImportError:  # optional dependency
    IB = LimitOrder = MarketOrder = Stock = None


@dataclass(slots=True)
class OrderRequest:
    side: str
    quantity: int
    order_type: str = "MKT"
    limit_price: float | None = None


@dataclass(slots=True)
class Quote:
    symbol: str
    last: float
    bid: float
    ask: float
    updated_at: datetime
    source: str


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: int
    avg_cost: float
    market_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.market_price - self.avg_cost) * self.quantity


@dataclass(slots=True)
class OpenOrder:
    order_id: str
    side: str
    quantity: int
    order_type: str
    status: str
    limit_price: float | None = None


@dataclass(slots=True)
class AccountSnapshot:
    buying_power: float
    net_liquidation: float
    realized_pnl: float
    unrealized_pnl: float


@dataclass(slots=True)
class TerminalSnapshot:
    quote: Quote
    positions: list[Position] = field(default_factory=list)
    open_orders: list[OpenOrder] = field(default_factory=list)
    account: AccountSnapshot | None = None


class BrokerClient(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def refresh_snapshot(self) -> TerminalSnapshot: ...
    def place_order(self, request: OrderRequest) -> str: ...
    def cancel_all(self) -> str: ...


class DryRunBrokerClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.connected = False
        self._next_order_id = 1
        self._quote = Quote(
            symbol=config.symbol,
            last=100.0,
            bid=99.99,
            ask=100.01,
            updated_at=datetime.now(timezone.utc),
            source="SIM",
        )
        self._position = Position(symbol=config.symbol, quantity=0, avg_cost=0.0, market_price=self._quote.last)
        self._open_orders: list[OpenOrder] = []
        self._realized_pnl = 0.0
        self._tick = 0

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def _update_quote(self) -> None:
        self._tick += 1
        drift = math.sin(self._tick / 6) * 0.18
        noise = random.uniform(-0.06, 0.06)
        last = max(1.0, round(self._quote.last + drift + noise, 2))
        self._quote = Quote(
            symbol=self.config.symbol,
            last=last,
            bid=round(last - 0.01, 2),
            ask=round(last + 0.01, 2),
            updated_at=datetime.now(timezone.utc),
            source="SIM",
        )
        self._position.market_price = last

    def refresh_snapshot(self) -> TerminalSnapshot:
        self._update_quote()
        account = AccountSnapshot(
            buying_power=100_000.0,
            net_liquidation=100_000.0 + self._position.unrealized_pnl + self._realized_pnl,
            realized_pnl=self._realized_pnl,
            unrealized_pnl=self._position.unrealized_pnl,
        )
        positions = [self._position] if self._position.quantity != 0 else []
        return TerminalSnapshot(
            quote=self._quote,
            positions=positions,
            open_orders=list(self._open_orders),
            account=account,
        )

    def place_order(self, request: OrderRequest) -> str:
        order_id = f"SIM-{self._next_order_id}"
        self._next_order_id += 1
        fill_price = request.limit_price if request.limit_price is not None else self._quote.last
        side_sign = 1 if request.side == "BUY" else -1
        previous_qty = self._position.quantity
        new_qty = previous_qty + side_sign * request.quantity

        if previous_qty == 0 or previous_qty * new_qty > 0:
            total_shares = abs(previous_qty) + request.quantity
            weighted_cost = (abs(previous_qty) * self._position.avg_cost) + (request.quantity * fill_price)
            self._position.avg_cost = weighted_cost / total_shares if total_shares else 0.0
        else:
            closed_qty = min(abs(previous_qty), request.quantity)
            if previous_qty > 0:
                self._realized_pnl += (fill_price - self._position.avg_cost) * closed_qty
            else:
                self._realized_pnl += (self._position.avg_cost - fill_price) * closed_qty
            if new_qty == 0:
                self._position.avg_cost = 0.0
            elif previous_qty * new_qty < 0:
                self._position.avg_cost = fill_price

        self._position.quantity = new_qty
        self._position.market_price = self._quote.last
        return f"[SIM] {order_id} {request.side} {request.quantity} {self.config.symbol} {request.order_type} @ {fill_price:.2f}"

    def cancel_all(self) -> str:
        count = len(self._open_orders)
        self._open_orders.clear()
        return f"[SIM] canceled {count} open orders"


class IbkrBrokerClient:
    def __init__(self, config: AppConfig) -> None:
        if IB is None:
            raise RuntimeError(
                "ib_insync is not installed. Install with `pip install .[ibkr]` to enable live trading."
            )
        self.config = config
        self.ib = IB()
        self.contract = Stock(config.symbol, config.exchange, config.currency)
        self.ticker = None

    def connect(self) -> None:
        self.ib.connect(self.config.host, self.config.port, clientId=self.config.client_id)
        self.ib.qualifyContracts(self.contract)
        self.ticker = self.ib.reqMktData(self.contract, "", False, False)

    def disconnect(self) -> None:
        if self.ticker is not None:
            self.ib.cancelMktData(self.contract)
        if self.ib.isConnected():
            self.ib.disconnect()

    def refresh_snapshot(self) -> TerminalSnapshot:
        self.ib.sleep(0)
        last = float(self.ticker.last or self.ticker.marketPrice() or 0.0)
        bid = float(self.ticker.bid or last or 0.0)
        ask = float(self.ticker.ask or last or 0.0)
        quote = Quote(
            symbol=self.config.symbol,
            last=last,
            bid=bid,
            ask=ask,
            updated_at=datetime.now(timezone.utc),
            source="IBKR",
        )
        positions = [
            Position(
                symbol=pos.contract.symbol,
                quantity=int(pos.position),
                avg_cost=float(pos.avgCost),
                market_price=quote.last or float(pos.avgCost),
            )
            for pos in self.ib.positions()
            if pos.contract.symbol == self.config.symbol
        ]
        open_orders = [
            OpenOrder(
                order_id=str(trade.order.orderId),
                side=trade.order.action,
                quantity=int(trade.order.totalQuantity),
                order_type=trade.order.orderType,
                status=trade.orderStatus.status,
                limit_price=float(trade.order.lmtPrice) if getattr(trade.order, "lmtPrice", 0) else None,
            )
            for trade in self.ib.openTrades()
            if trade.contract.symbol == self.config.symbol
        ]
        summary = {item.tag: item.value for item in self.ib.accountSummary()}
        account = AccountSnapshot(
            buying_power=float(summary.get("BuyingPower", 0.0)),
            net_liquidation=float(summary.get("NetLiquidation", 0.0)),
            realized_pnl=float(summary.get("RealizedPnL", 0.0)),
            unrealized_pnl=float(summary.get("UnrealizedPnL", 0.0)),
        )
        return TerminalSnapshot(quote=quote, positions=positions, open_orders=open_orders, account=account)

    def place_order(self, request: OrderRequest) -> str:
        if request.order_type == "LMT":
            if request.limit_price is None:
                raise ValueError("Limit order requires limit_price")
            order = LimitOrder(request.side, request.quantity, request.limit_price)
        else:
            order = MarketOrder(request.side, request.quantity)
        trade = self.ib.placeOrder(self.contract, order)
        return f"Placed {request.order_type} {request.side} order, IBKR trade id={trade.order.orderId}"

    def cancel_all(self) -> str:
        self.ib.reqGlobalCancel()
        return "Requested global cancel"


def build_client(config: AppConfig) -> BrokerClient:
    if config.dry_run:
        return DryRunBrokerClient(config)
    return IbkrBrokerClient(config)
