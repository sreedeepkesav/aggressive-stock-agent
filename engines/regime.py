"""Market regime detection - classifies market conditions to adjust engine weights.

Regimes: TRENDING_UP, TRENDING_DOWN, RANGE_BOUND, HIGH_VOLATILITY
Uses SPY as reference with VIX and sector breadth.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import numpy as np
import pandas as pd

from data.indicators import calculate_sma, calculate_rsi, calculate_atr
from data.market_data import get_history

logger = logging.getLogger("stock_agent")


class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGE_BOUND = "RANGE_BOUND"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNKNOWN = "UNKNOWN"


# Regime-adjusted engine weights
REGIME_WEIGHTS: Dict[MarketRegime, Dict[str, float]] = {
    MarketRegime.TRENDING_UP: {
        "momentum": 0.30, "fundamental": 0.20, "technical": 0.25,
        "sector": 0.15, "mean_reversion": 0.10,
    },
    MarketRegime.TRENDING_DOWN: {
        "momentum": 0.10, "fundamental": 0.30, "technical": 0.15,
        "sector": 0.15, "mean_reversion": 0.30,
    },
    MarketRegime.RANGE_BOUND: {
        "momentum": 0.15, "fundamental": 0.25, "technical": 0.20,
        "sector": 0.10, "mean_reversion": 0.30,
    },
    MarketRegime.HIGH_VOLATILITY: {
        "momentum": 0.10, "fundamental": 0.30, "technical": 0.10,
        "sector": 0.20, "mean_reversion": 0.30,
    },
    MarketRegime.UNKNOWN: {
        "momentum": 0.25, "fundamental": 0.25, "technical": 0.20,
        "sector": 0.15, "mean_reversion": 0.15,
    },
}

# Sector ETFs for breadth calculation
BREADTH_ETFS = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC"]


@dataclass
class RegimeInfo:
    """Full regime detection result."""
    regime: MarketRegime
    vix_level: float
    spy_trend: str           # "BULLISH", "BEARISH", "NEUTRAL"
    breadth_pct: float       # % of sectors above SMA50
    spy_daily_return: float  # SPY same-day return
    realized_vol_20d: float  # 20-day realized volatility
    realized_vol_60d: float  # 60-day realized volatility
    weights: Dict[str, float]
    confidence_multiplier: float  # Applied to all signals (1.0 = normal, 0.5 = crisis dampening)
    block_buys: bool         # True = VIX > 35, block all new BUY signals

    @property
    def summary(self) -> str:
        return (f"Regime: {self.regime.value} | VIX: {self.vix_level:.1f} | "
                f"SPY: {self.spy_trend} | Breadth: {self.breadth_pct:.0%} | "
                f"Block buys: {self.block_buys}")


def detect_regime() -> RegimeInfo:
    """Detect current market regime using SPY, VIX, and sector breadth."""
    try:
        # Fetch SPY data (1 year for SMA200)
        spy_df = get_history("SPY", period="1y")
        if spy_df.empty or len(spy_df) < 200:
            return _default_regime()

        spy_close = spy_df["Close"]
        spy_price = spy_close.iloc[-1]

        # SPY trend analysis
        sma50 = calculate_sma(spy_close, 50).iloc[-1]
        sma200 = calculate_sma(spy_close, 200).iloc[-1]

        # SMA50 slope: rate of change over last 10 days
        sma50_series = calculate_sma(spy_close, 50)
        sma50_slope = (sma50_series.iloc[-1] / sma50_series.iloc[-10] - 1) if len(sma50_series) >= 10 else 0

        # SPY daily return
        spy_daily_return = (spy_close.iloc[-1] / spy_close.iloc[-2] - 1) if len(spy_close) >= 2 else 0

        # Realized volatility
        daily_returns = spy_close.pct_change().dropna()
        realized_vol_20d = daily_returns.tail(20).std() * np.sqrt(252) if len(daily_returns) >= 20 else 0.15
        realized_vol_60d = daily_returns.tail(60).std() * np.sqrt(252) if len(daily_returns) >= 60 else 0.15

        # Determine SPY trend
        if spy_price > sma50 > sma200:
            spy_trend = "BULLISH"
        elif spy_price < sma50 < sma200:
            spy_trend = "BEARISH"
        else:
            spy_trend = "NEUTRAL"

        # VIX level (use ^VIX ticker)
        vix_level = _get_vix_level()

        # Sector breadth: % of sector ETFs above their 50-day SMA
        breadth_pct = _calculate_breadth()

        # Classify regime
        regime = _classify_regime(
            spy_price, sma50, sma200, sma50_slope,
            vix_level, breadth_pct,
            realized_vol_20d, realized_vol_60d,
        )

        # Market filters
        block_buys = vix_level > 35
        confidence_multiplier = 1.0

        if spy_daily_return < -0.03:
            confidence_multiplier = 0.5  # SPY down > 3% same day
        elif vix_level > 30:
            confidence_multiplier = 0.7

        weights = REGIME_WEIGHTS[regime].copy()

        return RegimeInfo(
            regime=regime,
            vix_level=vix_level,
            spy_trend=spy_trend,
            breadth_pct=breadth_pct,
            spy_daily_return=spy_daily_return,
            realized_vol_20d=realized_vol_20d,
            realized_vol_60d=realized_vol_60d,
            weights=weights,
            confidence_multiplier=confidence_multiplier,
            block_buys=block_buys,
        )

    except Exception as e:
        logger.error(f"Regime detection failed: {e}")
        return _default_regime()


def _get_vix_level() -> float:
    """Get current VIX level."""
    try:
        vix_df = get_history("^VIX", period="5d")
        if not vix_df.empty:
            return float(vix_df["Close"].iloc[-1])
    except Exception:
        pass
    return 20.0  # Default: normal volatility


def _calculate_breadth() -> float:
    """Calculate market breadth: fraction of sector ETFs above their 50-day SMA."""
    above_count = 0
    total = 0

    for etf in BREADTH_ETFS:
        try:
            df = get_history(etf, period="6mo")
            if df.empty or len(df) < 50:
                continue
            price = df["Close"].iloc[-1]
            sma50 = calculate_sma(df["Close"], 50).iloc[-1]
            if not pd.isna(sma50):
                total += 1
                if price > sma50:
                    above_count += 1
        except Exception:
            continue

    return above_count / total if total > 0 else 0.5


def _classify_regime(
    spy_price: float, sma50: float, sma200: float, sma50_slope: float,
    vix: float, breadth: float,
    vol_20d: float, vol_60d: float,
) -> MarketRegime:
    """Classify into one of 4 regimes based on market conditions."""

    # HIGH_VOLATILITY takes priority (crisis mode)
    if vix > 30 or (vol_20d > vol_60d * 2 and vol_20d > 0.25):
        return MarketRegime.HIGH_VOLATILITY

    # TRENDING_UP: clear bull market
    if spy_price > sma50 > sma200 and vix < 25 and breadth > 0.60:
        return MarketRegime.TRENDING_UP

    # TRENDING_DOWN: clear bear market
    if spy_price < sma50 < sma200 and vix > 20:
        return MarketRegime.TRENDING_DOWN

    # RANGE_BOUND: low slope, price oscillating
    if abs(sma50_slope) < 0.001:
        return MarketRegime.RANGE_BOUND

    # Mixed signals → range bound
    if breadth > 0.4 and breadth < 0.6:
        return MarketRegime.RANGE_BOUND

    # Default: if bullish lean, trending up; if bearish lean, trending down
    if spy_price > sma200:
        return MarketRegime.TRENDING_UP
    else:
        return MarketRegime.TRENDING_DOWN


def _default_regime() -> RegimeInfo:
    """Fallback regime when detection fails."""
    return RegimeInfo(
        regime=MarketRegime.UNKNOWN,
        vix_level=20.0,
        spy_trend="NEUTRAL",
        breadth_pct=0.5,
        spy_daily_return=0.0,
        realized_vol_20d=0.15,
        realized_vol_60d=0.15,
        weights=REGIME_WEIGHTS[MarketRegime.UNKNOWN].copy(),
        confidence_multiplier=1.0,
        block_buys=False,
    )
