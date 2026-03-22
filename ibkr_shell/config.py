from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 7
    symbol: str = "AAPL"
    exchange: str = "SMART"
    currency: str = "USD"
    quantity: int = 100
    dry_run: bool = True
    refresh_hz: int = 10

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "7497")),
            client_id=int(os.getenv("IBKR_CLIENT_ID", "7")),
            symbol=os.getenv("IBKR_SYMBOL", "AAPL"),
            exchange=os.getenv("IBKR_EXCHANGE", "SMART"),
            currency=os.getenv("IBKR_CURRENCY", "USD"),
            quantity=int(os.getenv("IBKR_QUANTITY", "100")),
            dry_run=os.getenv("IBKR_DRY_RUN", "true").lower() not in {"0", "false", "no"},
            refresh_hz=int(os.getenv("IBKR_REFRESH_HZ", "10")),
        )
