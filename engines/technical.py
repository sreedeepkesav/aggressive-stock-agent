"""Technical breakout detector - adapted from TechnicalBreakoutDetector."""

import logging

import numpy as np

from data.market_data import get_history_with_indicators
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class TechnicalEngine(BaseEngine):
    """Detects chart pattern breakouts, S/R levels, volume confirmation, MA crossovers, BB squeezes."""

    @property
    def name(self) -> str:
        return "technical"

    def analyze(self, symbol: str) -> EngineResult:
        df = get_history_with_indicators(symbol, period="6mo")
        if df.empty:
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, ["Insufficient data"])

        try:
            # Add extra indicators needed
            df["High_20"] = df["High"].rolling(20).max()
            df["Low_20"] = df["Low"].rolling(20).min()
            df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]
            df["EMA_20"] = df["Close"].ewm(span=20).mean()

            reasons = []
            score = 0.0
            price = df["Close"].iloc[-1]

            # 1. Support/resistance breakout (0.3 weight)
            sr = self._sr_breakout(df)
            score += sr["score"] * 0.3
            if sr.get("signal"):
                reasons.append(sr["signal"])

            # 2. Chart pattern (0.25 weight) - use pct-based slope for scale invariance
            cp = self._chart_pattern(df)
            score += cp["score"] * 0.25
            if cp.get("signal"):
                reasons.append(cp["signal"])

            # 3. Volume breakout (0.2)
            vb = self._volume_breakout(df)
            score += vb["score"] * 0.2
            if vb.get("signal"):
                reasons.append(vb["signal"])

            # 4. MA crossover (0.15)
            ma = self._ma_breakout(df)
            score += ma["score"] * 0.15
            if ma.get("signal"):
                reasons.append(ma["signal"])

            # 5. BB squeeze (0.1)
            bb = self._bb_squeeze(df)
            score += bb["score"] * 0.1
            if bb.get("signal"):
                reasons.append(bb["signal"])

            score = min(1.0, score)

            if score >= 0.65:
                signal = "STRONG_BUY" if score >= 0.8 else "BUY"
            elif score >= 0.4:
                signal = "HOLD"
            else:
                signal = "HOLD"

            return EngineResult(self.name, symbol, signal, score, reasons,
                                metadata={"price": round(price, 2)})

        except Exception as e:
            logger.error(f"Technical breakout failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])

    # ---- sub-detectors ----

    @staticmethod
    def _sr_breakout(df) -> dict:
        try:
            price = df["Close"].iloc[-1]
            resistance = df["High"].rolling(20).max().iloc[-5:].max()
            support = df["Low"].rolling(20).min().iloc[-5:].min()
            if price > resistance * 1.02:
                return {"score": 0.8, "signal": f"Resistance breakout {resistance:.2f}"}
            elif price < support * 0.98:
                return {"score": 0.7, "signal": f"Support breakdown {support:.2f}"}
            elif price > resistance * 0.99:
                return {"score": 0.4, "signal": "Approaching resistance"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _chart_pattern(df) -> dict:
        """Scale-invariant triangle detection using percentage slopes."""
        try:
            if len(df) < 50:
                return {"score": 0.0}
            recent = df.tail(50)
            highs = recent["High"].values
            lows = recent["Low"].values
            avg_price = recent["Close"].mean()
            # Normalize to percentage
            high_slope = np.polyfit(range(len(highs)), highs / avg_price, 1)[0]
            low_slope = np.polyfit(range(len(lows)), lows / avg_price, 1)[0]
            price = df["Close"].iloc[-1]
            resistance = highs.max()

            if abs(high_slope) < 0.001 and low_slope > 0.001:
                if price > resistance * 1.01:
                    return {"score": 0.75, "signal": "Ascending triangle breakout"}
            elif high_slope < -0.001 and abs(low_slope) < 0.001:
                support = lows.min()
                if price < support * 0.99:
                    return {"score": 0.7, "signal": "Descending triangle breakdown"}
            elif high_slope < -0.0005 and low_slope > 0.0005:
                return {"score": 0.5, "signal": "Symmetrical triangle compression"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _volume_breakout(df) -> dict:
        try:
            vol_ratio = df["Volume"].tail(5).mean() / df["Volume_SMA_20"].iloc[-1]
            if vol_ratio > 2.0:
                return {"score": min(1.0, vol_ratio / 3.0), "signal": f"Volume {vol_ratio:.1f}x"}
            elif vol_ratio > 1.5:
                return {"score": 0.4, "signal": f"Volume +{vol_ratio:.1f}x"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _ma_breakout(df) -> dict:
        try:
            price = df["Close"].iloc[-1]
            sma20, sma50 = df["SMA_20"].iloc[-1], df["SMA_50"].iloc[-1]
            sma20_prev, sma50_prev = df["SMA_20"].iloc[-2], df["SMA_50"].iloc[-2]
            if sma20 > sma50 and sma20_prev <= sma50_prev:
                return {"score": 0.7, "signal": "Golden cross"}
            elif sma20 < sma50 and sma20_prev >= sma50_prev:
                return {"score": 0.6, "signal": "Death cross"}
            elif price > max(sma20, sma50) * 1.02:
                return {"score": 0.6, "signal": "Price above key MAs"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _bb_squeeze(df) -> dict:
        try:
            bb_width = df["BB_Width"].iloc[-1]
            avg_width = df["BB_Width"].rolling(50).mean().iloc[-1]
            price = df["Close"].iloc[-1]
            if bb_width < avg_width * 0.7:
                if price > df["BB_Upper"].iloc[-1]:
                    return {"score": 0.8, "signal": "BB squeeze breakout (bullish)"}
                elif price < df["BB_Lower"].iloc[-1]:
                    return {"score": 0.7, "signal": "BB squeeze breakdown (bearish)"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}
