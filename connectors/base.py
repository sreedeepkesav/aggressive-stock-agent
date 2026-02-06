"""Abstract broker connector interface."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from portfolio.models import Order, Position


class BrokerConnector(ABC):
    """All broker integrations implement this interface."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Returns True on success."""
        ...

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get current positions from the broker."""
        ...

    @abstractmethod
    def place_order(self, order: Order) -> Dict:
        """Place an order. Returns order status dict."""
        ...

    @abstractmethod
    def get_account_balance(self) -> float:
        """Get available cash balance."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        ...
