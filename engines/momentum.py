"""Momentum breakout engine - adapted from MomentumBreakoutEngine."""

import logging
from typing import Dict

from data.market_data import get_history_with_indicators
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class MomentumEngine(BaseEngine):
    """Detects momentum breakouts using volume surge, trend structure, RSI/MACD confluence."""

    @property
    def name(self) -> str:
        return "momentum"

    def analyze(self, symbol: str) -> EngineResult:
        df = get_history_with_indicators(symbol, period="6mo")
        if df.empty:
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, ["Insufficient data"])

        try:
            latest = df.iloc[-1]
            recent_5d = df.iloc[-6:-1]
            recent_20d = df.iloc[-21:-1]

            reasons = []
            confidence = 0.0

            # 1. Volume surge (smart money)
            avg_vol_ratio = recent_5d["Volume_Ratio"].mean()
            if avg_vol_ratio > 2.5:
                reasons.append(f"Volume surge {avg_vol_ratio:.1f}x")
                confidence += 0.3
                if avg_vol_ratio > 4.0:
                    confidence += 0.2

            # 2. Trend structure
            price = latest["Close"]
            sma20 = latest["SMA_20"]
            sma50 = latest["SMA_50"]

            if price > sma20 > sma50:
                reasons.append("Bullish trend structure")
                confidence += 0.25
                # Breakout above recent resistance (exclude current day)
                resistance = recent_20d["Close"].max()
                if price > resistance * 1.02:
                    reasons.append(f"Resistance breakout above {resistance:.2f}")
                    confidence += 0.25

            # 3. Momentum indicators
            rsi = latest["RSI"]
            macd_hist = latest["MACD_Histogram"]
            if 55 < rsi < 80 and macd_hist > 0:
                reasons.append(f"Momentum confluence (RSI {rsi:.0f})")
                confidence += 0.2

            # 4. Volatility expansion
            current_atr = latest["ATR"]
            avg_atr = df["ATR"].rolling(50).mean().iloc[-1]
            if current_atr > avg_atr * 1.3:
                reasons.append("Volatility expansion")
                confidence += 0.15

            confidence = min(1.0, confidence)

            if confidence >= 0.8:
                signal = "STRONG_BUY"
            elif confidence >= 0.6:
                signal = "BUY"
            elif confidence >= 0.4:
                signal = "HOLD"
            else:
                signal = "HOLD"

            return EngineResult(
                self.name, symbol, signal, confidence, reasons,
                metadata={
                    "rsi": round(rsi, 1),
                    "volume_ratio": round(avg_vol_ratio, 2),
                    "entry": round(price, 2),
                    "stop_loss": round(price - current_atr * 2.0, 2),
                    "target": round(price + current_atr * 4.0, 2),
                },
            )
        except Exception as e:
            logger.error(f"Momentum analysis failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])
