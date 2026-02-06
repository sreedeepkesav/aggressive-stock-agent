"""Central configuration for the stock agent. All risk parameters are configurable via env vars."""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class LLMMode(Enum):
    OFF = "off"
    HAIKU = "haiku"
    SONNET = "sonnet"


@dataclass
class RiskParams:
    """Risk management parameters - all configurable via environment variables."""
    max_position_pct: float = 0.10           # Max 10% of portfolio per position
    max_portfolio_heat: float = 0.08         # Max 8% total portfolio at risk
    drawdown_circuit_breaker: float = -0.10  # Stop trading at -10% from peak
    max_simultaneous_positions: int = 5
    max_sector_concentration: float = 0.40   # Max 40% in one sector
    cash_reserve_pct: float = 0.20           # Keep 20% cash
    max_daily_risk: float = 0.05             # 5% daily risk tolerance
    min_profit_target: float = 0.08          # 8% minimum profit target
    stop_loss_atr_swing: float = 2.0         # 2.0 ATR for swing trades
    stop_loss_atr_position: float = 2.5      # 2.5 ATR for position trades

    @classmethod
    def from_env(cls) -> "RiskParams":
        """Load risk parameters from environment variables with safe defaults."""
        return cls(
            max_position_pct=float(os.getenv("MAX_POSITION_PCT", "0.10")),
            max_portfolio_heat=float(os.getenv("MAX_PORTFOLIO_HEAT", "0.08")),
            drawdown_circuit_breaker=float(os.getenv("DRAWDOWN_CIRCUIT_BREAKER", "-0.10")),
            max_simultaneous_positions=int(os.getenv("MAX_SIMULTANEOUS_POSITIONS", "5")),
            max_sector_concentration=float(os.getenv("MAX_SECTOR_CONCENTRATION", "0.40")),
            cash_reserve_pct=float(os.getenv("CASH_RESERVE_PCT", "0.20")),
            max_daily_risk=float(os.getenv("MAX_DAILY_RISK", "0.05")),
            min_profit_target=float(os.getenv("MIN_PROFIT_TARGET", "0.08")),
            stop_loss_atr_swing=float(os.getenv("STOP_LOSS_ATR_SWING", "2.0")),
            stop_loss_atr_position=float(os.getenv("STOP_LOSS_ATR_POSITION", "2.5")),
        )


@dataclass
class Settings:
    """Top-level application settings."""
    risk: RiskParams = field(default_factory=RiskParams.from_env)
    llm_mode: LLMMode = field(default_factory=lambda: LLMMode(os.getenv("LLM_MODE", "off")))

    # API keys (only those actually used)
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    avanza_username: str = field(default_factory=lambda: os.getenv("AVANZA_USERNAME", ""))
    avanza_password: str = field(default_factory=lambda: os.getenv("AVANZA_PASSWORD", ""))
    avanza_totp_secret: str = field(default_factory=lambda: os.getenv("AVANZA_TOTP_SECRET", ""))

    # Default watchlist
    watchlist: List[str] = field(default_factory=lambda: [
        # AI & Semiconductor
        "NVDA", "AMD", "SMCI", "AVGO", "ARM", "TSM", "MRVL", "QCOM",
        # Big Tech
        "AAPL", "MSFT", "GOOGL", "META", "AMZN",
        # Growth & Momentum
        "TSLA", "PLTR", "NET", "CRWD", "SNOW", "DDOG",
        # Fintech
        "COIN", "SQ", "HOOD", "SOFI", "UPST", "AFRM",
        # Biotech
        "MRNA", "BNTX", "REGN", "GILD", "VRTX",
    ])

    # Cache settings
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "300")))

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment."""
        return cls()
