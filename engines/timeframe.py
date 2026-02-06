"""Multi-timeframe confirmation: weekly trend filters daily signals to reduce noise.

Rules:
- Daily BUY + weekly downtrend → demote (reduce confidence 40%)
- Daily SELL + weekly uptrend → demote (reduce confidence 40%)
- Daily and weekly agree → boost confidence 20%
"""

import logging

import pandas as pd

from data.indicators import calculate_sma, calculate_rsi, calculate_macd
from data.market_data import get_weekly_history
from engines.signal_combiner import CombinedSignal

logger = logging.getLogger("stock_agent")


def get_weekly_trend(symbol: str) -> dict:
    """Analyze weekly trend for a symbol.

    Returns:
        dict with 'trend' (BULLISH/BEARISH/NEUTRAL), 'weekly_rsi', 'weekly_macd_dir'
    """
    try:
        df = get_weekly_history(symbol, period="1y")
        if df.empty or len(df) < 40:
            return {"trend": "NEUTRAL", "weekly_rsi": 50.0, "weekly_macd_dir": "flat"}

        close = df["Close"]

        # Weekly SMAs: SMA10w ≈ SMA50d, SMA40w ≈ SMA200d
        sma10w = calculate_sma(close, 10).iloc[-1]
        sma40w = calculate_sma(close, 40).iloc[-1] if len(close) >= 40 else sma10w
        price = close.iloc[-1]

        # Weekly RSI
        weekly_rsi = calculate_rsi(close, 14).iloc[-1]
        if pd.isna(weekly_rsi):
            weekly_rsi = 50.0

        # Weekly MACD direction
        macd_line, signal_line, histogram = calculate_macd(close)
        macd_dir = "flat"
        if len(histogram) >= 2:
            h_curr = histogram.iloc[-1]
            h_prev = histogram.iloc[-2]
            if not pd.isna(h_curr) and not pd.isna(h_prev):
                if h_curr > h_prev and h_curr > 0:
                    macd_dir = "bullish"
                elif h_curr < h_prev and h_curr < 0:
                    macd_dir = "bearish"

        # Determine weekly trend
        if pd.isna(sma10w) or pd.isna(sma40w):
            trend = "NEUTRAL"
        elif price > sma10w > sma40w:
            trend = "BULLISH"
        elif price < sma10w < sma40w:
            trend = "BEARISH"
        elif price > sma10w:
            trend = "MILDLY_BULLISH"
        elif price < sma10w:
            trend = "MILDLY_BEARISH"
        else:
            trend = "NEUTRAL"

        return {
            "trend": trend,
            "weekly_rsi": round(float(weekly_rsi), 1),
            "weekly_macd_dir": macd_dir,
        }

    except Exception as e:
        logger.error(f"Weekly trend analysis failed for {symbol}: {e}")
        return {"trend": "NEUTRAL", "weekly_rsi": 50.0, "weekly_macd_dir": "flat"}


def apply_timeframe_filter(signal: CombinedSignal) -> CombinedSignal:
    """Apply multi-timeframe filter as post-processing on CombinedSignal.

    Modifies confidence and potentially action based on weekly trend agreement.
    """
    try:
        weekly = get_weekly_trend(signal.symbol)
        weekly_trend = weekly["trend"]

        daily_bullish = signal.action in ("STRONG_BUY", "BUY")
        daily_bearish = signal.action in ("STRONG_SELL", "SELL")
        weekly_bullish = weekly_trend in ("BULLISH", "MILDLY_BULLISH")
        weekly_bearish = weekly_trend in ("BEARISH", "MILDLY_BEARISH")

        reasons = list(signal.reasons)

        if daily_bullish and weekly_bearish:
            # Daily BUY + weekly downtrend → demote
            new_confidence = signal.confidence * 0.6
            new_score = signal.combined_score * 0.7
            reasons.insert(1, f"[Timeframe] Weekly downtrend ({weekly_trend}) - confidence reduced")

            # Potentially demote action
            if signal.action == "STRONG_BUY":
                action = "BUY"
            elif signal.action == "BUY" and new_confidence < 0.4:
                action = "HOLD"
            else:
                action = signal.action

            return CombinedSignal(
                symbol=signal.symbol,
                action=action,
                combined_score=round(new_score, 4),
                confidence=round(new_confidence, 4),
                engine_results=signal.engine_results,
                reasons=reasons[:12],
                agreement_pct=signal.agreement_pct,
                regime=signal.regime,
            )

        elif daily_bearish and weekly_bullish:
            # Daily SELL + weekly uptrend → demote
            new_confidence = signal.confidence * 0.6
            new_score = signal.combined_score * 0.7
            reasons.insert(1, f"[Timeframe] Weekly uptrend ({weekly_trend}) - sell signal reduced")

            if signal.action == "STRONG_SELL":
                action = "SELL"
            elif signal.action == "SELL" and new_confidence < 0.4:
                action = "HOLD"
            else:
                action = signal.action

            return CombinedSignal(
                symbol=signal.symbol,
                action=action,
                combined_score=round(new_score, 4),
                confidence=round(new_confidence, 4),
                engine_results=signal.engine_results,
                reasons=reasons[:12],
                agreement_pct=signal.agreement_pct,
                regime=signal.regime,
            )

        elif (daily_bullish and weekly_bullish) or (daily_bearish and weekly_bearish):
            # Daily and weekly agree → boost
            new_confidence = min(1.0, signal.confidence * 1.2)
            reasons.insert(1, f"[Timeframe] Weekly confirms ({weekly_trend}) - confidence boosted")

            return CombinedSignal(
                symbol=signal.symbol,
                action=signal.action,
                combined_score=signal.combined_score,
                confidence=round(new_confidence, 4),
                engine_results=signal.engine_results,
                reasons=reasons[:12],
                agreement_pct=signal.agreement_pct,
                regime=signal.regime,
            )

        else:
            # No strong agreement or disagreement
            reasons.insert(1, f"[Timeframe] Weekly neutral ({weekly_trend})")
            return CombinedSignal(
                symbol=signal.symbol,
                action=signal.action,
                combined_score=signal.combined_score,
                confidence=signal.confidence,
                engine_results=signal.engine_results,
                reasons=reasons[:12],
                agreement_pct=signal.agreement_pct,
                regime=signal.regime,
            )

    except Exception as e:
        logger.error(f"Timeframe filter failed for {signal.symbol}: {e}")
        return signal
