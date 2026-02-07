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
    # Lead indicators
    credit_stress: float = 0.0             # 0-1 scale (1 = high stress)
    yield_curve_inverted: bool = False
    vix_term_structure: str = "flat"       # "contango" / "flat" / "backwardation"
    risk_appetite: str = "neutral"         # "risk_on" / "neutral" / "risk_off"

    @property
    def summary(self) -> str:
        lead = f"Credit: {self.credit_stress:.2f} | YC: {'INV' if self.yield_curve_inverted else 'OK'} | VTS: {self.vix_term_structure} | Risk: {self.risk_appetite}"
        return (f"Regime: {self.regime.value} | VIX: {self.vix_level:.1f} | "
                f"SPY: {self.spy_trend} | Breadth: {self.breadth_pct:.0%} | "
                f"Block buys: {self.block_buys}\n"
                f"  Lead: {lead}")


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

        # Fetch lead indicators
        credit = _get_credit_stress()
        yield_curve = _get_yield_curve_signal()
        vix_term = _get_vix_term_structure()
        risk_app = _get_risk_appetite()

        lead_indicators = {
            "credit": credit,
            "yield_curve": yield_curve,
            "vix_term": vix_term,
            "risk_appetite": risk_app,
        }

        # Classify regime (with lead indicators)
        regime = _classify_regime(
            spy_price, sma50, sma200, sma50_slope,
            vix_level, breadth_pct,
            realized_vol_20d, realized_vol_60d,
            lead_indicators=lead_indicators,
        )

        # Market filters
        block_buys = vix_level > 35
        confidence_multiplier = 1.0

        if spy_daily_return < -0.03:
            confidence_multiplier = 0.5  # SPY down > 3% same day
        elif vix_level > 30:
            confidence_multiplier = 0.7

        # Lead indicator confidence adjustment
        if credit.get("credit_deteriorating") and vix_term.get("backwardation"):
            confidence_multiplier *= 0.8  # Extra dampening on double stress signal

        weights = REGIME_WEIGHTS[regime].copy()

        # Yield curve steepening → boost fundamental, reduce momentum
        if yield_curve.get("steepening"):
            weights["fundamental"] = min(0.40, weights.get("fundamental", 0.25) + 0.05)
            weights["momentum"] = max(0.05, weights.get("momentum", 0.25) - 0.05)
            # Renormalize
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}

        # Derive lead indicator summary fields
        credit_stress = 0.0
        if credit.get("credit_deteriorating"):
            credit_stress = 0.5
            if credit.get("hyg_return_10d", 0) < -0.02:
                credit_stress = 0.8
        if vix_term.get("backwardation"):
            credit_stress = min(1.0, credit_stress + 0.3)

        vts_label = "contango" if vix_term.get("contango") else ("backwardation" if vix_term.get("backwardation") else "flat")
        ra_label = "risk_off" if risk_app.get("risk_off") else "risk_on" if risk_app.get("gld_spy_ratio_trend", 0) < -0.02 else "neutral"

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
            credit_stress=credit_stress,
            yield_curve_inverted=yield_curve.get("inverted", False),
            vix_term_structure=vts_label,
            risk_appetite=ra_label,
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


def _get_credit_stress() -> dict:
    """Assess credit market stress via HYG/LQD spread."""
    result = {"credit_ratio": 1.0, "credit_deteriorating": False, "hyg_return_10d": 0.0}
    try:
        hyg_df = get_history("HYG", period="3mo")
        lqd_df = get_history("LQD", period="3mo")
        if hyg_df.empty or lqd_df.empty or len(hyg_df) < 20 or len(lqd_df) < 20:
            return result

        # HYG/LQD ratio - declining means credit deterioration
        ratio_now = hyg_df["Close"].iloc[-1] / lqd_df["Close"].iloc[-1]
        ratio_20d = hyg_df["Close"].iloc[-20] / lqd_df["Close"].iloc[-20]
        result["credit_ratio"] = float(ratio_now)
        result["credit_deteriorating"] = ratio_now < ratio_20d * 0.99  # >1% decline

        # HYG 10-day return
        hyg_10d = (hyg_df["Close"].iloc[-1] / hyg_df["Close"].iloc[-10] - 1) if len(hyg_df) >= 10 else 0
        result["hyg_return_10d"] = float(hyg_10d)
    except Exception as e:
        logger.debug(f"Credit stress check failed: {e}")
    return result


def _get_yield_curve_signal() -> dict:
    """Yield curve signal from 10Y-3M spread."""
    result = {"spread": 1.0, "inverted": False, "steepening": False}
    try:
        tnx = get_history("^TNX", period="3mo")  # 10-year yield
        irx = get_history("^IRX", period="3mo")   # 13-week T-bill
        if tnx.empty or irx.empty or len(tnx) < 20 or len(irx) < 20:
            return result

        spread_now = float(tnx["Close"].iloc[-1] - irx["Close"].iloc[-1])
        spread_20d = float(tnx["Close"].iloc[-20] - irx["Close"].iloc[-20])
        result["spread"] = spread_now
        result["inverted"] = spread_now < 0
        # Rapid steepening = spread widened by >0.5% in 20 days
        result["steepening"] = (spread_now - spread_20d) > 0.5
    except Exception as e:
        logger.debug(f"Yield curve check failed: {e}")
    return result


def _get_vix_term_structure() -> dict:
    """VIX term structure: VIX vs VIX3M ratio."""
    result = {"ratio": 0.9, "backwardation": False, "contango": True}
    try:
        vix_df = get_history("^VIX", period="1mo")
        vix3m_df = get_history("^VIX3M", period="1mo")
        if vix_df.empty or vix3m_df.empty:
            return result

        vix_val = float(vix_df["Close"].iloc[-1])
        vix3m_val = float(vix3m_df["Close"].iloc[-1])
        if vix3m_val > 0:
            ratio = vix_val / vix3m_val
            result["ratio"] = ratio
            result["backwardation"] = ratio > 1.0  # VIX > VIX3M = panic
            result["contango"] = ratio < 0.85      # Normal/complacent
    except Exception as e:
        logger.debug(f"VIX term structure check failed: {e}")
    return result


def _get_risk_appetite() -> dict:
    """Risk appetite from GLD/SPY ratio trend."""
    result = {"gld_spy_ratio_trend": 0.0, "risk_off": False}
    try:
        gld_df = get_history("GLD", period="3mo")
        spy_df = get_history("SPY", period="3mo")
        if gld_df.empty or spy_df.empty or len(gld_df) < 60 or len(spy_df) < 60:
            return result

        # Current GLD/SPY ratio vs 60-day average
        ratio_20d = float(gld_df["Close"].iloc[-1] / spy_df["Close"].iloc[-1])
        # 60-day average ratio
        ratios = gld_df["Close"].tail(60).values / spy_df["Close"].tail(60).values
        avg_60d = float(np.mean(ratios))

        trend = (ratio_20d - avg_60d) / avg_60d if avg_60d > 0 else 0
        result["gld_spy_ratio_trend"] = trend
        result["risk_off"] = trend > 0.02  # GLD/SPY rising >2% vs average = risk-off rotation
    except Exception as e:
        logger.debug(f"Risk appetite check failed: {e}")
    return result


def _classify_regime(
    spy_price: float, sma50: float, sma200: float, sma50_slope: float,
    vix: float, breadth: float,
    vol_20d: float, vol_60d: float,
    lead_indicators: Optional[dict] = None,
) -> MarketRegime:
    """Classify into one of 4 regimes based on market conditions and lead indicators."""
    lead = lead_indicators or {}

    # Base classification from lagging indicators
    # HIGH_VOLATILITY takes priority (crisis mode)
    if vix > 30 or (vol_20d > vol_60d * 2 and vol_20d > 0.25):
        return MarketRegime.HIGH_VOLATILITY

    # Lead indicator early-warning: upgrade severity (never downgrade)
    credit = lead.get("credit", {})
    vts = lead.get("vix_term", {})
    yc = lead.get("yield_curve", {})
    risk = lead.get("risk_appetite", {})

    # Credit deteriorating + VIX backwardation → HIGH_VOLATILITY even if VIX < 30
    if credit.get("credit_deteriorating") and vts.get("backwardation"):
        return MarketRegime.HIGH_VOLATILITY

    # TRENDING_UP: clear bull market
    if spy_price > sma50 > sma200 and vix < 25 and breadth > 0.60:
        # But if credit is deteriorating + risk-off, downgrade to RANGE_BOUND
        if credit.get("credit_deteriorating") and risk.get("risk_off"):
            return MarketRegime.RANGE_BOUND
        return MarketRegime.TRENDING_UP

    # TRENDING_DOWN: clear bear market
    if spy_price < sma50 < sma200 and vix > 20:
        return MarketRegime.TRENDING_DOWN

    # GLD/SPY rising + credit deteriorating → lean TRENDING_DOWN
    if risk.get("risk_off") and credit.get("credit_deteriorating"):
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
