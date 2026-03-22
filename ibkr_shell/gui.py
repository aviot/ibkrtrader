from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import BrokerClient, TerminalSnapshot, build_client
from .config import AppConfig
from .keypad import KEYPAD_BINDINGS, TradingState, execute_binding

try:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtWidgets import (
        QApplication,
        QDoubleSpinBox,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QLabel,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # optional dependency
    QApplication = None


@dataclass(slots=True)
class QuoteViewModel:
    symbol: str
    last: str
    bid: str
    ask: str
    updated: str
    source: str


KEY_LABELS: dict[str, str] = {
    "8": "市价买入",
    "2": "市价卖出",
    "7": "限价买入",
    "1": "限价卖出",
    "0": "全部撤单",
    "+": "数量 +100",
    "-": "数量 -100",
    "4": "缩小偏移",
    "6": "扩大偏移",
}


def format_quote(snapshot: TerminalSnapshot) -> QuoteViewModel:
    quote = snapshot.quote
    return QuoteViewModel(
        symbol=quote.symbol,
        last=f"{quote.last:.2f}",
        bid=f"{quote.bid:.2f}",
        ask=f"{quote.ask:.2f}",
        updated=quote.updated_at.strftime("%H:%M:%S"),
        source=quote.source,
    )


def create_app(argv: list[str]) -> Any:
    if QApplication is None:
        raise RuntimeError("PySide6 is not installed. Install with `pip install .[gui]`.")
    return QApplication(argv)


if QApplication is not None:

    class TradingMainWindow(QMainWindow):
        def __init__(self, config: AppConfig) -> None:
            super().__init__()
            self.config = config
            self.broker: BrokerClient = build_client(config)
            self.state = TradingState(quantity=config.quantity)
            self.setWindowTitle(f"IBKR Trader - {config.symbol} ({'SIM' if config.dry_run else 'LIVE'})")
            self.resize(1380, 860)

            self.status = QStatusBar(self)
            self.setStatusBar(self.status)

            self.header_mode = QLabel()
            self.header_quote = QLabel()
            self.header_controls = QLabel()

            self.quote_labels: dict[str, QLabel] = {}
            self.account_labels: dict[str, QLabel] = {}
            self.positions_table = QTableWidget(0, 6)
            self.orders_table = QTableWidget(0, 6)
            self.hotkeys_table = QTableWidget(0, 2)
            self.activity_log = QPlainTextEdit()
            self.qty_spin = QSpinBox()
            self.offset_spin = QDoubleSpinBox()

            self._setup_ui()
            self._setup_shortcuts()
            self._connect_broker()
            self._refresh_ui()

            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self._refresh_ui)
            self.refresh_timer.start(max(50, int(1000 / max(1, config.refresh_hz))))

        def _setup_ui(self) -> None:
            root = QWidget(self)
            self.setCentralWidget(root)
            layout = QVBoxLayout(root)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(12)

            header = QGroupBox("交易概览")
            header_layout = QVBoxLayout(header)
            header_layout.addWidget(self.header_mode)
            header_layout.addWidget(self.header_quote)
            header_layout.addWidget(self.header_controls)
            layout.addWidget(header)

            body = QGridLayout()
            body.setSpacing(12)
            body.addWidget(self._build_quote_group(), 0, 0)
            body.addWidget(self._build_account_group(), 1, 0)
            body.addWidget(self._build_order_entry_group(), 2, 0)
            body.addWidget(self._build_positions_group(), 0, 1, 2, 1)
            body.addWidget(self._build_orders_group(), 2, 1)
            body.addWidget(self._build_hotkeys_group(), 0, 2)
            body.addWidget(self._build_activity_group(), 1, 2, 2, 1)
            body.setColumnStretch(1, 2)
            body.setColumnStretch(2, 2)
            layout.addLayout(body)

        def _build_quote_group(self) -> QGroupBox:
            group = QGroupBox("实时行情")
            form = QFormLayout(group)
            for key in ("symbol", "last", "bid", "ask", "updated", "source"):
                label = QLabel("-")
                self.quote_labels[key] = label
                form.addRow(key.capitalize(), label)
            return group

        def _build_account_group(self) -> QGroupBox:
            group = QGroupBox("账户")
            form = QFormLayout(group)
            for key in ("buying_power", "net_liquidation", "realized_pnl", "unrealized_pnl"):
                label = QLabel("-")
                self.account_labels[key] = label
                form.addRow(key.replace("_", " ").title(), label)
            return group

        def _build_order_entry_group(self) -> QGroupBox:
            group = QGroupBox("快捷下单")
            layout = QVBoxLayout(group)

            self.qty_spin.setRange(1, 1_000_000)
            self.qty_spin.setSingleStep(100)
            self.qty_spin.setValue(self.state.quantity)
            self.qty_spin.valueChanged.connect(self._on_qty_changed)

            self.offset_spin.setRange(0.01, 1000.0)
            self.offset_spin.setDecimals(2)
            self.offset_spin.setSingleStep(0.01)
            self.offset_spin.setValue(self.state.limit_offset)
            self.offset_spin.valueChanged.connect(self._on_offset_changed)

            form = QFormLayout()
            form.addRow("数量", self.qty_spin)
            form.addRow("限价偏移", self.offset_spin)
            layout.addLayout(form)

            buttons = QGridLayout()
            buttons.addWidget(self._make_button("市价买入  [8]", "8"), 0, 0)
            buttons.addWidget(self._make_button("市价卖出  [2]", "2"), 0, 1)
            buttons.addWidget(self._make_button("限价买入  [7]", "7"), 1, 0)
            buttons.addWidget(self._make_button("限价卖出  [1]", "1"), 1, 1)
            buttons.addWidget(self._make_button("全部撤单  [0]", "0"), 2, 0, 1, 2)
            layout.addLayout(buttons)
            return group

        def _build_positions_group(self) -> QGroupBox:
            group = QGroupBox("持仓")
            layout = QVBoxLayout(group)
            self.positions_table.setHorizontalHeaderLabels(["SYM", "QTY", "AVG", "LAST", "MKTVAL", "UPNL"])
            self.positions_table.verticalHeader().setVisible(False)
            layout.addWidget(self.positions_table)
            return group

        def _build_orders_group(self) -> QGroupBox:
            group = QGroupBox("未成交订单")
            layout = QVBoxLayout(group)
            self.orders_table.setHorizontalHeaderLabels(["ID", "SIDE", "QTY", "TYPE", "STATUS", "LIMIT"])
            self.orders_table.verticalHeader().setVisible(False)
            layout.addWidget(self.orders_table)
            return group

        def _build_hotkeys_group(self) -> QGroupBox:
            group = QGroupBox("小键盘映射")
            layout = QVBoxLayout(group)
            self.hotkeys_table.setHorizontalHeaderLabels(["按键", "动作"])
            self.hotkeys_table.verticalHeader().setVisible(False)
            self.hotkeys_table.setRowCount(len(KEY_LABELS))
            for row, (key, desc) in enumerate(KEY_LABELS.items()):
                self.hotkeys_table.setItem(row, 0, QTableWidgetItem(key))
                self.hotkeys_table.setItem(row, 1, QTableWidgetItem(desc))
            layout.addWidget(self.hotkeys_table)
            return group

        def _build_activity_group(self) -> QGroupBox:
            group = QGroupBox("活动日志")
            layout = QVBoxLayout(group)
            self.activity_log.setReadOnly(True)
            layout.addWidget(self.activity_log)
            return group

        def _make_button(self, text: str, key: str) -> QPushButton:
            button = QPushButton(text)
            button.clicked.connect(lambda: self._execute_key(key))
            return button

        def _setup_shortcuts(self) -> None:
            for key in KEYPAD_BINDINGS:
                action = QAction(self)
                sequence = key if key not in {"+", "-"} else f"Shift+{key}"
                action.setShortcut(QKeySequence(sequence))
                action.triggered.connect(lambda checked=False, hotkey=key: self._execute_key(hotkey))
                self.addAction(action)

            quit_action = QAction(self)
            quit_action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
            quit_action.triggered.connect(self.close)
            self.addAction(quit_action)

        def keyPressEvent(self, event) -> None:  # type: ignore[override]
            text = event.text()
            if text in KEYPAD_BINDINGS:
                self._execute_key(text)
                event.accept()
                return
            super().keyPressEvent(event)

        def _connect_broker(self) -> None:
            self.broker.connect()
            self.state.log.add("Connected to broker")
            self.status.showMessage("Connected", 3000)

        def _on_qty_changed(self, value: int) -> None:
            self.state.quantity = value
            self.state.log.add(f"Qty spin -> {value}")
            self._sync_log()

        def _on_offset_changed(self, value: float) -> None:
            self.state.limit_offset = round(value, 2)
            self.state.log.add(f"Offset spin -> {value:.2f}")
            self._sync_log()

        def _execute_key(self, key: str) -> None:
            self.state.quantity = self.qty_spin.value()
            self.state.limit_offset = round(self.offset_spin.value(), 2)
            result = execute_binding(key, self.state, self.broker)
            if result is None:
                self.status.showMessage(f"Ignored key: {key}", 2000)
                return
            self.status.showMessage(result, 4000)
            self._refresh_ui()

        def _refresh_ui(self) -> None:
            snapshot = self.broker.refresh_snapshot()
            self.state.snapshot = snapshot
            self._render_header(snapshot)
            self._render_quote(snapshot)
            self._render_account(snapshot)
            self._render_positions(snapshot)
            self._render_orders(snapshot)
            self._sync_log()

        def _render_header(self, snapshot: TerminalSnapshot) -> None:
            quote = snapshot.quote
            mode = "SIM" if self.config.dry_run else "LIVE"
            self.header_mode.setText(f"{self.config.symbol} | {mode} | IBKR desktop terminal")
            self.header_quote.setText(
                f"Last {quote.last:.2f}    Bid {quote.bid:.2f}    Ask {quote.ask:.2f}    Updated {quote.updated_at.strftime('%H:%M:%S')}    Feed {quote.source}"
            )
            self.header_controls.setText(
                f"数量 {self.state.quantity}    限价偏移 {self.state.limit_offset:.2f}    小键盘: 8买 / 2卖 / 7买限 / 1卖限 / 0全撤 / +/- 调整数量 / 4/6 调整偏移"
            )

        def _render_quote(self, snapshot: TerminalSnapshot) -> None:
            view = format_quote(snapshot)
            self.quote_labels["symbol"].setText(view.symbol)
            self.quote_labels["last"].setText(view.last)
            self.quote_labels["bid"].setText(view.bid)
            self.quote_labels["ask"].setText(view.ask)
            self.quote_labels["updated"].setText(view.updated)
            self.quote_labels["source"].setText(view.source)

        def _render_account(self, snapshot: TerminalSnapshot) -> None:
            account = snapshot.account
            if account is None:
                for label in self.account_labels.values():
                    label.setText("-")
                return
            self.account_labels["buying_power"].setText(f"{account.buying_power:,.2f}")
            self.account_labels["net_liquidation"].setText(f"{account.net_liquidation:,.2f}")
            self.account_labels["realized_pnl"].setText(f"{account.realized_pnl:,.2f}")
            self.account_labels["unrealized_pnl"].setText(f"{account.unrealized_pnl:,.2f}")

        def _render_positions(self, snapshot: TerminalSnapshot) -> None:
            self.positions_table.setRowCount(len(snapshot.positions))
            for row, pos in enumerate(snapshot.positions):
                values = [
                    pos.symbol,
                    str(pos.quantity),
                    f"{pos.avg_cost:.2f}",
                    f"{pos.market_price:.2f}",
                    f"{pos.market_value:.2f}",
                    f"{pos.unrealized_pnl:.2f}",
                ]
                for col, value in enumerate(values):
                    self.positions_table.setItem(row, col, QTableWidgetItem(value))

        def _render_orders(self, snapshot: TerminalSnapshot) -> None:
            self.orders_table.setRowCount(len(snapshot.open_orders))
            for row, order in enumerate(snapshot.open_orders):
                values = [
                    order.order_id,
                    order.side,
                    str(order.quantity),
                    order.order_type,
                    order.status,
                    "-" if order.limit_price is None else f"{order.limit_price:.2f}",
                ]
                for col, value in enumerate(values):
                    self.orders_table.setItem(row, col, QTableWidgetItem(value))

        def _sync_log(self) -> None:
            self.activity_log.setPlainText("\n".join(self.state.log.entries))
            scrollbar = self.activity_log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        def closeEvent(self, event) -> None:  # type: ignore[override]
            if hasattr(self, "refresh_timer"):
                self.refresh_timer.stop()
            self.broker.disconnect()
            super().closeEvent(event)


else:

    class TradingMainWindow:  # pragma: no cover - placeholder when PySide6 missing
        def __init__(self, config: AppConfig) -> None:
            raise RuntimeError("PySide6 is not installed. Install with `pip install .[gui]`.")


def launch(config: AppConfig, argv: list[str]) -> int:
    app = create_app(argv)
    window = TradingMainWindow(config)
    window.show()
    return app.exec()
