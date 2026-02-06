"""Base engine interface and result dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EngineResult:
    """Standardized output from every analysis engine."""
    engine_name: str
    symbol: str
    signal: str           # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_DATA
    confidence: float     # 0.0 - 1.0
    reasons: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @property
    def is_bullish(self) -> bool:
        return self.signal in ("STRONG_BUY", "BUY")

    @property
    def is_bearish(self) -> bool:
        return self.signal in ("STRONG_SELL", "SELL")

    @property
    def numeric_signal(self) -> float:
        """Convert signal to -1..+1 scale for weighted combination."""
        mapping = {
            "STRONG_BUY": 1.0,
            "BUY": 0.5,
            "HOLD": 0.0,
            "SELL": -0.5,
            "STRONG_SELL": -1.0,
            "NO_DATA": 0.0,
        }
        return mapping.get(self.signal, 0.0)


class BaseEngine(ABC):
    """All analysis engines implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def analyze(self, symbol: str) -> EngineResult:
        ...
