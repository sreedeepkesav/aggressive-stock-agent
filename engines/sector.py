"""Sector rotation strategy - adapted from SectorRotationStrategy."""

import logging

from data.market_data import get_history, get_info, clean_symbol
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")

SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

_YFINANCE_SECTOR_MAP = {
    "Technology": "Technology",
    "Healthcare": "Healthcare",
    "Financial Services": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Basic Materials": "Materials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Communication Services": "Communication Services",
}


class SectorEngine(BaseEngine):
    """Evaluates sector rotation, relative strength, and economic cycle positioning."""

    @property
    def name(self) -> str:
        return "sector"

    def analyze(self, symbol: str) -> EngineResult:
        try:
            sector = self._identify_sector(symbol)
            if not sector:
                return EngineResult(self.name, symbol, "HOLD", 0.3, ["Sector not identified"])

            reasons = []
            score = 0.0

            # 1. Sector momentum (0.4 weight)
            etf = SECTOR_ETFS.get(sector)
            if etf:
                mom = self._sector_momentum(etf)
                score += mom["score"] * 0.4
                if mom["score"] > 0.5:
                    reasons.append(f"Sector momentum {mom['trend']}")

            # 2. Relative strength vs SPY (0.35 weight)
            rs = self._relative_strength(symbol, sector)
            score += rs["score"] * 0.35
            if rs["score"] > 0.5:
                reasons.append(f"Relative strength {rs['trend']}")

            # 3. Sector flow proxy via volume (0.25 weight)
            flow = self._sector_flow(etf) if etf else {"score": 0.5}
            score += flow["score"] * 0.25
            if flow["score"] > 0.6:
                reasons.append("Strong sector inflow")

            score = min(1.0, score)

            if score >= 0.7:
                signal = "BUY"
            elif score >= 0.5:
                signal = "HOLD"
            elif score >= 0.3:
                signal = "HOLD"
            else:
                signal = "SELL"

            return EngineResult(self.name, symbol, signal, score, reasons,
                                metadata={"sector": sector})

        except Exception as e:
            logger.error(f"Sector analysis failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "HOLD", 0.3, [str(e)])

    @staticmethod
    def _identify_sector(symbol: str) -> str:
        info = get_info(symbol)
        raw_sector = info.get("sector", "")
        return _YFINANCE_SECTOR_MAP.get(raw_sector, raw_sector)

    @staticmethod
    def _sector_momentum(etf: str) -> dict:
        df = get_history(etf, period="6mo")
        if df.empty or len(df) < 50:
            return {"score": 0.5, "trend": "NEUTRAL"}
        price = df["Close"].iloc[-1]
        sma20 = df["Close"].rolling(20).mean().iloc[-1]
        sma50 = df["Close"].rolling(50).mean().iloc[-1]
        ret_1m = (price / df["Close"].iloc[-21] - 1) if len(df) >= 21 else 0

        if price > sma20 > sma50 and ret_1m > 0.03:
            return {"score": 0.8, "trend": "BULLISH"}
        elif price > sma20:
            return {"score": 0.6, "trend": "MILDLY_BULLISH"}
        elif price < sma20 < sma50:
            return {"score": 0.2, "trend": "BEARISH"}
        return {"score": 0.5, "trend": "NEUTRAL"}

    @staticmethod
    def _relative_strength(symbol: str, sector: str) -> dict:
        sym_df = get_history(symbol, period="3mo")
        spy_df = get_history("SPY", period="3mo")
        if sym_df.empty or spy_df.empty or len(sym_df) < 20:
            return {"score": 0.5, "trend": "NEUTRAL"}
        sym_ret = sym_df["Close"].iloc[-1] / sym_df["Close"].iloc[-21] - 1
        spy_ret = spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-21] - 1
        excess = sym_ret - spy_ret
        if excess > 0.05:
            return {"score": 0.85, "trend": "OUTPERFORMING"}
        elif excess > 0.02:
            return {"score": 0.65, "trend": "MILDLY_OUTPERFORMING"}
        elif excess < -0.05:
            return {"score": 0.2, "trend": "UNDERPERFORMING"}
        return {"score": 0.5, "trend": "INLINE"}

    @staticmethod
    def _sector_flow(etf: str) -> dict:
        df = get_history(etf, period="1mo")
        if df.empty or len(df) < 10:
            return {"score": 0.5}
        vol_ratio = df["Volume"].tail(5).mean() / df["Volume"].rolling(20).mean().iloc[-1]
        price_up = df["Close"].iloc[-1] > df["Close"].iloc[-5]
        if vol_ratio > 1.5 and price_up:
            return {"score": 0.8}
        elif vol_ratio > 1.2:
            return {"score": 0.6}
        return {"score": 0.4}
