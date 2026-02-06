"""Data models for portfolio management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class TradeStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass
class Position:
    """An open position in the portfolio."""
    symbol: str
    quantity: int
    entry_price: float
    entry_date: str
    stop_loss: float
    target_price: float
    sector: str = ""
    current_price: float = 0.0
    id: Optional[int] = None

    @property
    def market_value(self) -> float:
        return self.quantity * (self.current_price or self.entry_price)

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        if self.current_price <= 0:
            return 0.0
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price


@dataclass
class Trade:
    """A completed (closed) trade."""
    symbol: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_date: str
    exit_date: str
    pnl: float
    pnl_pct: float
    reason: str = ""
    id: Optional[int] = None


@dataclass
class Order:
    """A pending or executed order."""
    symbol: str
    side: str  # BUY or SELL
    order_type: str  # MARKET, LIMIT, STOP
    quantity: int
    price: float
    stop_loss: float = 0.0
    target_price: float = 0.0
    status: str = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: Optional[int] = None
