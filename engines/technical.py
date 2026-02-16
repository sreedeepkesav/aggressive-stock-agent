"""Technical breakout detector - with market structure, false breakout detection, VWAP, ATR-scaled thresholds."""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from data.market_data import get_history_with_indicators
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class TechnicalEngine(BaseEngine):
    """Detects chart pattern breakouts, S/R levels, market structure,
    false breakout traps, VWAP bias, Keltner squeezes."""

    @property
    def name(self) -> str:
        return "technical"

    def analyze(self, symbol: str, df: Optional[pd.DataFrame] = None,
                backtest_date: Optional[str] = None, **kwargs) -> EngineResult:
        if df is None:
            df = get_history_with_indicators(symbol, period="6mo")
        if df.empty:
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, ["Insufficient data"])

        try:
            df["High_20"] = df["High"].rolling(20).max()
            df["Low_20"] = df["Low"].rolling(20).min()
            df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]
            df["EMA_20"] = df["Close"].ewm(span=20).mean()

            reasons = []
            score = 0.0
            price = df["Close"].iloc[-1]
            atr = df["ATR"].iloc[-1] if not pd.isna(df["ATR"].iloc[-1]) else price * 0.02

            # 1. S/R breakout with ATR-scaled thresholds (0.25 weight)
            sr = self._sr_breakout_atr(df, atr)
            score += sr["score"] * 0.25
            if sr.get("signal"):
                reasons.append(sr["signal"])

            # 2. Market structure: higher-highs/higher-lows tracking (0.2 weight)
            ms = self._market_structure(df)
            score += ms["score"] * 0.2
            if ms.get("signal"):
                reasons.append(ms["signal"])

            # 3. False breakout detection (0.15 weight) - can flip to SELL
            fb = self._false_breakout(df, atr)
            score += fb["score"] * 0.15
            if fb.get("signal"):
                reasons.append(fb["signal"])

            # 4. VWAP as dynamic S/R (0.1 weight)
            vwap = self._vwap_bias(df)
            score += vwap["score"] * 0.1
            if vwap.get("signal"):
                reasons.append(vwap["signal"])

            # 5. MA crossover (0.1 weight)
            ma = self._ma_breakout(df)
            score += ma["score"] * 0.1
            if ma.get("signal"):
                reasons.append(ma["signal"])

            # 6. Keltner squeeze (0.1 weight) - BB inside Keltner
            ks = self._keltner_squeeze(df)
            score += ks["score"] * 0.1
            if ks.get("signal"):
                reasons.append(ks["signal"])

            # 7. BB %B integration (0.1 weight)
            bb = self._bb_pctb(df)
            score += bb["score"] * 0.1
            if bb.get("signal"):
                reasons.append(bb["signal"])

            score = max(0.0, min(1.0, score))

            if score >= 0.7:
                signal = "STRONG_BUY" if score >= 0.85 else "BUY"
            elif score >= 0.4:
                signal = "HOLD"
            elif score < 0.2:
                signal = "SELL"
            else:
                signal = "HOLD"

            return EngineResult(self.name, symbol, signal, score, reasons,
                                metadata={"price": round(price, 2)})

        except Exception as e:
            logger.error(f"Technical breakout failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])

    # ---- sub-detectors ----

    @staticmethod
    def _sr_breakout_atr(df, atr: float) -> dict:
        """S/R breakout using ATR-scaled thresholds instead of hardcoded percentages."""
        try:
            price = df["Close"].iloc[-1]
            resistance = df["High"].rolling(20).max().iloc[-5:].max()
            support = df["Low"].rolling(20).min().iloc[-5:].min()

            # ATR-scaled breakout threshold (0.5-1.0 ATR)
            breakout_threshold = atr * 0.75

            if price > resistance + breakout_threshold:
                return {"score": 0.85, "signal": f"ATR-confirmed breakout above {resistance:.2f}"}
            elif price > resistance:
                return {"score": 0.5, "signal": f"Testing resistance {resistance:.2f}"}
            elif price < support - breakout_threshold:
                return {"score": 0.7, "signal": f"ATR-confirmed breakdown below {support:.2f}"}
            elif price < support + breakout_threshold * 0.5:
                return {"score": 0.3, "signal": "Near support"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _market_structure(df) -> dict:
        """Track higher-highs/higher-lows vs lower-highs/lower-lows."""
        try:
            if len(df) < 30:
                return {"score": 0.0}

            # Use 5-bar swing points
            highs = df["High"].iloc[-30:]
            lows = df["Low"].iloc[-30:]

            # Find swing highs and lows (local extremes over 5 bars)
            swing_highs = []
            swing_lows = []
            for i in range(2, len(highs) - 2):
                if highs.iloc[i] >= highs.iloc[i-2:i+3].max():
                    swing_highs.append(highs.iloc[i])
                if lows.iloc[i] <= lows.iloc[i-2:i+3].min():
                    swing_lows.append(lows.iloc[i])

            if len(swing_highs) >= 2 and len(swing_lows) >= 2:
                hh = swing_highs[-1] > swing_highs[-2]
                hl = swing_lows[-1] > swing_lows[-2]
                lh = swing_highs[-1] < swing_highs[-2]
                ll = swing_lows[-1] < swing_lows[-2]

                if hh and hl:
                    return {"score": 0.8, "signal": "Uptrend structure (HH+HL)"}
                elif lh and ll:
                    return {"score": 0.7, "signal": "Downtrend structure (LH+LL)"}
                elif hh and ll:
                    return {"score": 0.4, "signal": "Expanding range"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _false_breakout(df, atr: float) -> dict:
        """Detect false breakouts: price breaks level but closes back within 2 bars."""
        try:
            if len(df) < 25:
                return {"score": 0.0}

            # Check if price broke above 20-day high 2-3 bars ago but closed back below
            high_20 = df["High"].rolling(20).max()
            for lookback in [2, 3]:
                if len(df) < lookback + 21:
                    continue
                past_high = high_20.iloc[-lookback - 1]
                past_close = df["Close"].iloc[-lookback]
                curr_close = df["Close"].iloc[-1]

                if not pd.isna(past_high):
                    # Bull trap: broke above resistance but fell back
                    if past_close > past_high and curr_close < past_high - atr * 0.3:
                        return {"score": -0.5, "signal": "Bull trap: false breakout above resistance"}

            # Check false breakdown
            low_20 = df["Low"].rolling(20).min()
            for lookback in [2, 3]:
                if len(df) < lookback + 21:
                    continue
                past_low = low_20.iloc[-lookback - 1]
                past_close = df["Close"].iloc[-lookback]
                curr_close = df["Close"].iloc[-1]

                if not pd.isna(past_low):
                    if past_close < past_low and curr_close > past_low + atr * 0.3:
                        return {"score": 0.7, "signal": "Bear trap: false breakdown (bullish)"}

            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _vwap_bias(df) -> dict:
        """VWAP as dynamic support/resistance."""
        try:
            price = df["Close"].iloc[-1]
            vwap = df.get("VWAP")
            if vwap is None:
                return {"score": 0.0}
            vwap_val = vwap.iloc[-1]
            if pd.isna(vwap_val) or vwap_val <= 0:
                return {"score": 0.0}

            pct_diff = (price - vwap_val) / vwap_val
            if pct_diff > 0.02:
                return {"score": 0.6, "signal": f"Above VWAP (+{pct_diff:.1%})"}
            elif pct_diff < -0.02:
                return {"score": 0.3, "signal": f"Below VWAP ({pct_diff:.1%})"}
            return {"score": 0.45, "signal": "At VWAP"}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _ma_breakout(df) -> dict:
        try:
            price = df["Close"].iloc[-1]
            sma20, sma50 = df["SMA_20"].iloc[-1], df["SMA_50"].iloc[-1]
            sma20_prev, sma50_prev = df["SMA_20"].iloc[-2], df["SMA_50"].iloc[-2]
            if sma20 > sma50 and sma20_prev <= sma50_prev:
                return {"score": 0.75, "signal": "Golden cross (SMA20/50)"}
            elif sma20 < sma50 and sma20_prev >= sma50_prev:
                return {"score": 0.6, "signal": "Death cross (SMA20/50)"}
            elif price > max(sma20, sma50) * 1.02:
                return {"score": 0.55, "signal": "Price above key MAs"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _keltner_squeeze(df) -> dict:
        """BB inside Keltner = volatility squeeze (more reliable than BB alone)."""
        try:
            bb_upper = df["BB_Upper"].iloc[-1]
            bb_lower = df["BB_Lower"].iloc[-1]
            kelt_upper = df.get("Keltner_Upper")
            kelt_lower = df.get("Keltner_Lower")

            if kelt_upper is None or kelt_lower is None:
                return {"score": 0.0}

            ku = kelt_upper.iloc[-1]
            kl = kelt_lower.iloc[-1]

            if pd.isna(ku) or pd.isna(kl) or pd.isna(bb_upper) or pd.isna(bb_lower):
                return {"score": 0.0}

            # Squeeze: BB inside Keltner
            in_squeeze = bb_upper < ku and bb_lower > kl
            price = df["Close"].iloc[-1]

            if in_squeeze:
                # Check if squeeze is releasing (BB expanding)
                bb_width_now = bb_upper - bb_lower
                bb_width_prev = df["BB_Upper"].iloc[-3] - df["BB_Lower"].iloc[-3]
                if not pd.isna(bb_width_prev) and bb_width_now > bb_width_prev:
                    if price > df["BB_Upper"].iloc[-1]:
                        return {"score": 0.85, "signal": "Keltner squeeze breakout (bullish)"}
                    elif price < df["BB_Lower"].iloc[-1]:
                        return {"score": 0.7, "signal": "Keltner squeeze breakdown"}
                return {"score": 0.5, "signal": "Keltner squeeze forming"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _bb_pctb(df) -> dict:
        """Bollinger %B integration."""
        try:
            pctb = df.get("BB_PctB")
            if pctb is None:
                return {"score": 0.0}
            val = pctb.iloc[-1]
            if pd.isna(val):
                return {"score": 0.0}

            if val > 0.9:
                return {"score": 0.7, "signal": f"BB %B extreme high ({val:.2f})"}
            elif val > 0.8:
                return {"score": 0.6, "signal": f"BB %B bullish ({val:.2f})"}
            elif val < 0.1:
                return {"score": 0.6, "signal": f"BB %B extreme low ({val:.2f})"}
            elif val < 0.2:
                return {"score": 0.5, "signal": f"BB %B oversold ({val:.2f})"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}
