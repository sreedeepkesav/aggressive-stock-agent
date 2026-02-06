"""Momentum breakout engine - with divergence detection, ROC confirmation, OBV trend."""

import logging
from typing import Dict

import numpy as np
import pandas as pd

from data.market_data import get_history_with_indicators
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class MomentumEngine(BaseEngine):
    """Detects momentum breakouts using volume surge, trend, RSI/MACD confluence,
    divergence detection, and rate-of-change confirmation."""

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
                confidence += 0.25
                if avg_vol_ratio > 4.0:
                    confidence += 0.15

            # 2. Trend structure
            price = latest["Close"]
            sma20 = latest["SMA_20"]
            sma50 = latest["SMA_50"]

            if price > sma20 > sma50:
                reasons.append("Bullish trend structure")
                confidence += 0.2
                resistance = recent_20d["Close"].max()
                if price > resistance * 1.02:
                    reasons.append(f"Resistance breakout above {resistance:.2f}")
                    confidence += 0.2

            # 3. RSI divergence detection (strongest momentum signal)
            rsi = latest["RSI"]
            rsi_div = self._detect_rsi_divergence(df)
            if rsi_div == "bullish":
                reasons.append("Bullish RSI divergence (price new low, RSI higher)")
                confidence += 0.3
            elif rsi_div == "bearish":
                reasons.append("Bearish RSI divergence (price new high, RSI lower)")
                confidence -= 0.2

            # 4. MACD signal line crossover (actual cross events, not just histogram)
            macd_cross = self._detect_macd_crossover(df)
            if macd_cross == "bullish":
                reasons.append("MACD bullish crossover")
                confidence += 0.2
            elif macd_cross == "bearish":
                reasons.append("MACD bearish crossover")
                confidence -= 0.15

            # 5. Stochastic RSI (smoothed momentum at extremes)
            stoch_k = latest.get("Stoch_K", 50)
            stoch_d = latest.get("Stoch_D", 50)
            if not pd.isna(stoch_k) and not pd.isna(stoch_d):
                if stoch_k < 20 and stoch_k > stoch_d:
                    reasons.append(f"Stochastic oversold cross up ({stoch_k:.0f})")
                    confidence += 0.15
                elif stoch_k > 80 and stoch_k < stoch_d:
                    reasons.append(f"Stochastic overbought cross down ({stoch_k:.0f})")
                    confidence -= 0.1

            # 6. Rate of change confirmation
            roc = latest.get("ROC_12", 0)
            if not pd.isna(roc):
                if roc > 10:
                    reasons.append(f"Strong ROC {roc:.1f}%")
                    confidence += 0.1
                elif roc < -10:
                    confidence -= 0.1

            # 7. OBV trend (accumulated buying pressure, not just volume spike)
            obv_trend = self._obv_trend(df)
            if obv_trend == "rising":
                reasons.append("OBV trend rising (accumulation)")
                confidence += 0.1
            elif obv_trend == "falling":
                confidence -= 0.1

            # 8. RSI relative threshold (above/below 50-period RSI average)
            rsi_avg = df["RSI"].rolling(50).mean().iloc[-1]
            if not pd.isna(rsi_avg) and not pd.isna(rsi):
                if rsi > rsi_avg + 10 and rsi < 80:
                    reasons.append(f"RSI above avg ({rsi:.0f} vs {rsi_avg:.0f})")
                    confidence += 0.1

            # 9. Volatility expansion
            current_atr = latest["ATR"]
            avg_atr = df["ATR"].rolling(50).mean().iloc[-1]
            if not pd.isna(avg_atr) and current_atr > avg_atr * 1.3:
                reasons.append("Volatility expansion")
                confidence += 0.1

            confidence = max(0.0, min(1.0, confidence))

            if confidence >= 0.8:
                signal = "STRONG_BUY"
            elif confidence >= 0.6:
                signal = "BUY"
            elif confidence <= 0.15:
                signal = "SELL"
            else:
                signal = "HOLD"

            return EngineResult(
                self.name, symbol, signal, confidence, reasons,
                metadata={
                    "rsi": round(float(rsi) if not pd.isna(rsi) else 50, 1),
                    "volume_ratio": round(avg_vol_ratio, 2),
                    "entry": round(price, 2),
                    "stop_loss": round(price - current_atr * 2.0, 2),
                    "target": round(price + current_atr * 4.0, 2),
                    "rsi_divergence": rsi_div,
                    "macd_cross": macd_cross,
                },
            )
        except Exception as e:
            logger.error(f"Momentum analysis failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])

    @staticmethod
    def _detect_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> str:
        """Detect bullish/bearish RSI divergence over lookback period."""
        try:
            if len(df) < lookback + 5:
                return "none"
            recent = df.iloc[-lookback:]
            prices = recent["Close"].values
            rsi_vals = recent["RSI"].values

            # Filter NaN
            valid = ~(np.isnan(prices) | np.isnan(rsi_vals))
            if valid.sum() < lookback // 2:
                return "none"

            # Bullish: price makes lower low, RSI makes higher low
            price_min_idx = np.nanargmin(prices[-10:])
            price_prev_min_idx = np.nanargmin(prices[:10])

            if prices[-10:][price_min_idx] < prices[:10][price_prev_min_idx]:
                if rsi_vals[-10:][price_min_idx] > rsi_vals[:10][price_prev_min_idx]:
                    return "bullish"

            # Bearish: price makes higher high, RSI makes lower high
            price_max_idx = np.nanargmax(prices[-10:])
            price_prev_max_idx = np.nanargmax(prices[:10])

            if prices[-10:][price_max_idx] > prices[:10][price_prev_max_idx]:
                if rsi_vals[-10:][price_max_idx] < rsi_vals[:10][price_prev_max_idx]:
                    return "bearish"

            return "none"
        except Exception:
            return "none"

    @staticmethod
    def _detect_macd_crossover(df: pd.DataFrame) -> str:
        """Detect recent MACD signal line crossover (within last 3 bars)."""
        try:
            if len(df) < 5:
                return "none"
            macd = df["MACD"].iloc[-4:]
            signal = df["MACD_Signal"].iloc[-4:]

            for i in range(1, len(macd)):
                prev_diff = macd.iloc[i - 1] - signal.iloc[i - 1]
                curr_diff = macd.iloc[i] - signal.iloc[i]
                if pd.isna(prev_diff) or pd.isna(curr_diff):
                    continue
                if prev_diff <= 0 and curr_diff > 0:
                    return "bullish"
                elif prev_diff >= 0 and curr_diff < 0:
                    return "bearish"
            return "none"
        except Exception:
            return "none"

    @staticmethod
    def _obv_trend(df: pd.DataFrame, lookback: int = 20) -> str:
        """Determine OBV trend direction using linear regression slope."""
        try:
            if len(df) < lookback:
                return "flat"
            obv = df["OBV"].iloc[-lookback:].values
            if np.any(np.isnan(obv)):
                return "flat"
            x = np.arange(len(obv))
            slope = np.polyfit(x, obv, 1)[0]
            # Normalize slope by OBV magnitude
            avg_obv = np.abs(obv).mean()
            if avg_obv == 0:
                return "flat"
            normalized_slope = slope / avg_obv
            if normalized_slope > 0.02:
                return "rising"
            elif normalized_slope < -0.02:
                return "falling"
            return "flat"
        except Exception:
            return "flat"
