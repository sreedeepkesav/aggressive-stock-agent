"""Mean reversion detector - regime-gated with divergences, stochastic, detrended analysis, exhaustion."""

import logging

import numpy as np
import pandas as pd

from data.indicators import calculate_rsi, calculate_bollinger_bands
from data.market_data import get_history_with_indicators
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class MeanReversionEngine(BaseEngine):
    """Detects mean reversion setups. Best in RANGE_BOUND and HIGH_VOLATILITY regimes."""

    @property
    def name(self) -> str:
        return "mean_reversion"

    def analyze(self, symbol: str, regime: str = "UNKNOWN") -> EngineResult:
        df = get_history_with_indicators(symbol, period="1y")
        if df.empty:
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, ["Insufficient data"])

        try:
            df["Price_Percentile"] = df["Close"].rolling(252, min_periods=50).rank(pct=True)

            reasons = []
            score = 0.0

            # Regime gate: boost mean reversion in range-bound/volatile, dampen in trending
            regime_multiplier = 1.0
            if regime in ("RANGE_BOUND", "HIGH_VOLATILITY"):
                regime_multiplier = 1.3
                reasons.append(f"Regime favorable ({regime})")
            elif regime == "TRENDING_UP":
                regime_multiplier = 0.7
            elif regime == "TRENDING_DOWN":
                regime_multiplier = 0.8

            # 1. Detrended price deviation (linear regression, not just SMA200) (0.25 weight)
            pd_result = self._detrended_deviation(df)
            score += pd_result["score"] * 0.25
            if pd_result.get("signal"):
                reasons.append(pd_result["signal"])

            # 2. RSI divergence (0.2 weight)
            rsi_div = self._rsi_divergence(df)
            score += rsi_div["score"] * 0.2
            if rsi_div.get("signal"):
                reasons.append(rsi_div["signal"])

            # 3. Stochastic extremes with crossovers (0.2 weight)
            stoch = self._stochastic_extremes(df)
            score += stoch["score"] * 0.2
            if stoch.get("signal"):
                reasons.append(stoch["signal"])

            # 4. Exhaustion detection: volume spike + extreme RSI + wide BB (0.15 weight)
            exhaust = self._exhaustion_detection(df)
            score += exhaust["score"] * 0.15
            if exhaust.get("signal"):
                reasons.append(exhaust["signal"])

            # 5. Volume divergence (0.1 weight)
            vol_result = self._volume_divergence(df)
            score += vol_result["score"] * 0.1
            if vol_result.get("signal"):
                reasons.append(vol_result["signal"])

            # 6. Support bounce (0.1 weight)
            sr_result = self._support_bounce(df)
            score += sr_result["score"] * 0.1
            if sr_result.get("signal"):
                reasons.append(sr_result["signal"])

            # Apply regime multiplier
            score = score * regime_multiplier
            score = max(0.0, min(1.0, score))

            # Determine direction
            bullish = any("oversold" in r.lower() or "bullish" in r.lower() for r in reasons)
            bearish = any("overbought" in r.lower() or "bearish" in r.lower() for r in reasons)

            if score >= 0.6:
                signal = "BUY" if bullish else ("SELL" if bearish else "HOLD")
            elif score >= 0.4:
                signal = "HOLD"
            else:
                signal = "HOLD"

            return EngineResult(self.name, symbol, signal, score, reasons,
                                metadata={"regime_multiplier": regime_multiplier})

        except Exception as e:
            logger.error(f"Mean reversion failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])

    @staticmethod
    def _detrended_deviation(df) -> dict:
        """Calculate deviation from linear regression (not just SMA200)."""
        try:
            close = df["Close"].values
            if len(close) < 50:
                return {"score": 0.0}

            # Use last 100 bars for regression
            lookback = min(100, len(close))
            prices = close[-lookback:]
            x = np.arange(lookback)

            # Linear regression
            coeffs = np.polyfit(x, prices, 1)
            trend_value = np.polyval(coeffs, lookback - 1)

            deviation = (close[-1] - trend_value) / trend_value

            if deviation < -0.15:
                return {"score": 0.9, "signal": f"Extreme oversold vs trend ({deviation:.0%})"}
            elif deviation > 0.15:
                return {"score": 0.8, "signal": f"Extreme overbought vs trend (+{deviation:.0%})"}
            elif deviation < -0.08:
                return {"score": 0.6, "signal": f"Oversold vs trend ({deviation:.0%})"}
            elif deviation > 0.08:
                return {"score": 0.5, "signal": f"Overbought vs trend (+{deviation:.0%})"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _rsi_divergence(df) -> dict:
        """RSI divergence for mean reversion (inverted from momentum)."""
        try:
            if len(df) < 25:
                return {"score": 0.0}
            recent = df.iloc[-20:]
            prices = recent["Close"].values
            rsi_vals = recent["RSI"].values

            valid = ~(np.isnan(prices) | np.isnan(rsi_vals))
            if valid.sum() < 10:
                return {"score": 0.0}

            # Bearish divergence: price higher high, RSI lower high → reversal down
            price_max_recent = np.nanmax(prices[-10:])
            price_max_prev = np.nanmax(prices[:10])
            rsi_max_recent = np.nanmax(rsi_vals[-10:])
            rsi_max_prev = np.nanmax(rsi_vals[:10])

            if price_max_recent > price_max_prev and rsi_max_recent < rsi_max_prev:
                return {"score": 0.7, "signal": "Bearish RSI divergence (overbought reversal)"}

            # Bullish divergence: price lower low, RSI higher low → reversal up
            price_min_recent = np.nanmin(prices[-10:])
            price_min_prev = np.nanmin(prices[:10])
            rsi_min_recent = np.nanmin(rsi_vals[-10:])
            rsi_min_prev = np.nanmin(rsi_vals[:10])

            if price_min_recent < price_min_prev and rsi_min_recent > rsi_min_prev:
                return {"score": 0.7, "signal": "Bullish RSI divergence (oversold reversal)"}

            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _stochastic_extremes(df) -> dict:
        """Stochastic %K/%D crossovers at extremes."""
        try:
            stoch_k = df.get("Stoch_K")
            stoch_d = df.get("Stoch_D")
            if stoch_k is None or stoch_d is None:
                return {"score": 0.0}

            k = stoch_k.iloc[-1]
            d = stoch_d.iloc[-1]
            k_prev = stoch_k.iloc[-2]
            d_prev = stoch_d.iloc[-2]

            if pd.isna(k) or pd.isna(d) or pd.isna(k_prev) or pd.isna(d_prev):
                return {"score": 0.0}

            # Oversold cross up
            if k < 20 and k_prev < d_prev and k > d:
                return {"score": 0.75, "signal": f"Stochastic oversold cross up (%K={k:.0f})"}

            # Overbought cross down
            if k > 80 and k_prev > d_prev and k < d:
                return {"score": 0.7, "signal": f"Stochastic overbought cross down (%K={k:.0f})"}

            # Just extreme
            if k < 15:
                return {"score": 0.5, "signal": f"Stochastic extreme oversold ({k:.0f})"}
            elif k > 85:
                return {"score": 0.45, "signal": f"Stochastic extreme overbought ({k:.0f})"}

            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _exhaustion_detection(df) -> dict:
        """Volume spike + extreme RSI + wide BB = capitulation (strong reversal signal)."""
        try:
            latest = df.iloc[-1]
            rsi = latest.get("RSI", 50)
            vol_ratio = latest.get("Volume_Ratio", 1.0)
            pctb = df.get("BB_PctB")

            if pd.isna(rsi) or pd.isna(vol_ratio):
                return {"score": 0.0}

            pctb_val = pctb.iloc[-1] if pctb is not None and not pd.isna(pctb.iloc[-1]) else 0.5

            # Selling exhaustion: RSI < 25, volume spike > 2x, price at/below lower BB
            if rsi < 25 and vol_ratio > 2.0 and pctb_val < 0.1:
                return {"score": 0.9, "signal": "Selling exhaustion (capitulation)"}

            # Buying exhaustion: RSI > 75, volume spike > 2x, price at/above upper BB
            if rsi > 75 and vol_ratio > 2.0 and pctb_val > 0.9:
                return {"score": 0.8, "signal": "Buying exhaustion (blow-off top)"}

            # Partial exhaustion signals
            if rsi < 30 and vol_ratio > 1.5:
                return {"score": 0.5, "signal": "Partial selling exhaustion"}
            if rsi > 70 and vol_ratio > 1.5:
                return {"score": 0.45, "signal": "Partial buying exhaustion"}

            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _volume_divergence(df) -> dict:
        try:
            price_down = df["Close"].iloc[-1] < df["Close"].iloc[-5]
            vol_declining = df["Volume"].tail(5).mean() < df["Volume_SMA_20"].iloc[-1] * 0.8
            if price_down and vol_declining:
                return {"score": 0.6, "signal": "Bullish volume divergence (selling exhaustion)"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _support_bounce(df) -> dict:
        try:
            price = df["Close"].iloc[-1]
            low_20 = df["Low"].rolling(20).min().iloc[-1]
            if price < low_20 * 1.02 and price > low_20:
                return {"score": 0.6, "signal": "Near 20-day support"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}
