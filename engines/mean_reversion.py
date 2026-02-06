"""Mean reversion detector - adapted from MeanReversionDetector."""

import logging

from data.indicators import calculate_rsi, calculate_bollinger_bands
from data.market_data import get_history_with_indicators
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class MeanReversionEngine(BaseEngine):
    """Detects mean reversion setups from oversold/overbought extremes."""

    @property
    def name(self) -> str:
        return "mean_reversion"

    def analyze(self, symbol: str) -> EngineResult:
        df = get_history_with_indicators(symbol, period="1y")
        if df.empty:
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, ["Insufficient data"])

        try:
            # Add extra indicators
            df["Price_Percentile"] = df["Close"].rolling(252, min_periods=50).rank(pct=True)

            reasons = []
            score = 0.0

            # 1. Price deviation from 200-day SMA (0.3 weight)
            pd_result = self._price_deviation(df)
            score += pd_result["score"] * 0.3
            if pd_result.get("signal"):
                reasons.append(pd_result["signal"])

            # 2. RSI extremes (0.25 weight)
            rsi_result = self._rsi_extremes(df)
            score += rsi_result["score"] * 0.25
            if rsi_result.get("signal"):
                reasons.append(rsi_result["signal"])

            # 3. Bollinger band extremes (0.2 weight)
            bb_result = self._bb_extremes(df)
            score += bb_result["score"] * 0.2
            if bb_result.get("signal"):
                reasons.append(bb_result["signal"])

            # 4. Volume divergence (0.15 weight)
            vol_result = self._volume_divergence(df)
            score += vol_result["score"] * 0.15
            if vol_result.get("signal"):
                reasons.append(vol_result["signal"])

            # 5. Support bounce (0.1 weight)
            sr_result = self._support_bounce(df)
            score += sr_result["score"] * 0.1
            if sr_result.get("signal"):
                reasons.append(sr_result["signal"])

            score = min(1.0, score)

            # Determine direction: is this a bullish or bearish reversion?
            bullish = any("oversold" in r.lower() or "bullish" in r.lower() for r in reasons)
            bearish = any("overbought" in r.lower() or "bearish" in r.lower() for r in reasons)

            if score >= 0.6:
                signal = "BUY" if bullish else ("SELL" if bearish else "HOLD")
            elif score >= 0.4:
                signal = "HOLD"
            else:
                signal = "HOLD"

            return EngineResult(self.name, symbol, signal, score, reasons)

        except Exception as e:
            logger.error(f"Mean reversion failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])

    @staticmethod
    def _price_deviation(df) -> dict:
        try:
            price = df["Close"].iloc[-1]
            sma200 = df["SMA_200"].iloc[-1]
            pctile = df["Price_Percentile"].iloc[-1]
            deviation = (price - sma200) / sma200

            if pctile < 0.1 and deviation < -0.15:
                return {"score": 0.9, "signal": f"Extreme oversold ({deviation:.0%} from SMA200)"}
            elif pctile > 0.9 and deviation > 0.15:
                return {"score": 0.8, "signal": f"Extreme overbought (+{deviation:.0%} from SMA200)"}
            elif pctile < 0.2:
                return {"score": 0.6, "signal": f"Oversold ({deviation:.0%} from SMA200)"}
            elif pctile > 0.8:
                return {"score": 0.5, "signal": f"Overbought (+{deviation:.0%} from SMA200)"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _rsi_extremes(df) -> dict:
        try:
            rsi = df["RSI"].iloc[-1]
            if rsi < 20:
                return {"score": 0.8, "signal": f"RSI extreme oversold ({rsi:.0f})"}
            elif rsi > 80:
                return {"score": 0.7, "signal": f"RSI extreme overbought ({rsi:.0f})"}
            elif rsi < 30:
                return {"score": 0.5, "signal": f"RSI oversold ({rsi:.0f})"}
            elif rsi > 70:
                return {"score": 0.4, "signal": f"RSI overbought ({rsi:.0f})"}
            return {"score": 0.0}
        except Exception:
            return {"score": 0.0}

    @staticmethod
    def _bb_extremes(df) -> dict:
        try:
            price = df["Close"].iloc[-1]
            if price < df["BB_Lower"].iloc[-1]:
                return {"score": 0.7, "signal": "Below lower Bollinger band (bullish reversion)"}
            elif price > df["BB_Upper"].iloc[-1]:
                return {"score": 0.6, "signal": "Above upper Bollinger band (bearish reversion)"}
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
