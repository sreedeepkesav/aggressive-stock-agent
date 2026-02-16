"""Sector rotation strategy - with relative strength ranking and correlation check."""

import logging
from typing import Optional

import numpy as np
import pandas as pd

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
    """Evaluates sector rotation, relative strength ranking, and correlation."""

    @property
    def name(self) -> str:
        return "sector"

    def analyze(self, symbol: str, df: Optional[pd.DataFrame] = None,
                backtest_date: Optional[str] = None, **kwargs) -> EngineResult:
        # Sector analysis requires live ETF data and current sector rankings.
        # During backtesting, historical sector rankings can't be reconstructed,
        # so we return a neutral signal to avoid lookahead bias.
        if backtest_date is not None:
            return EngineResult(
                self.name, symbol, "HOLD", 0.0,
                ["Sector engine neutral during backtest (historical sector rankings unavailable)"]
            )

        try:
            sector = self._identify_sector(symbol)
            if not sector:
                return EngineResult(self.name, symbol, "HOLD", 0.3, ["Sector not identified"])

            reasons = []
            score = 0.0

            # 1. Sector rank among all 11 sectors (0.3 weight)
            rank_result = self._sector_rank(sector)
            score += rank_result["score"] * 0.3
            if rank_result.get("signal"):
                reasons.append(rank_result["signal"])

            # 2. Sector momentum (0.25 weight)
            etf = SECTOR_ETFS.get(sector)
            if etf:
                mom = self._sector_momentum(etf)
                score += mom["score"] * 0.25
                if mom["score"] > 0.5:
                    reasons.append(f"Sector momentum {mom['trend']}")

            # 3. True relative strength: stock return / sector ETF return (0.25 weight)
            rs = self._true_relative_strength(symbol, sector)
            score += rs["score"] * 0.25
            if rs.get("signal"):
                reasons.append(rs["signal"])

            # 4. Correlation check: if too correlated to SPY, sector provides no edge (0.1 weight)
            corr = self._correlation_check(symbol)
            score += corr["score"] * 0.1
            if corr.get("signal"):
                reasons.append(corr["signal"])

            # 5. Sector flow proxy via volume (0.1 weight)
            flow = self._sector_flow(etf) if etf else {"score": 0.5}
            score += flow["score"] * 0.1
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
    def _sector_rank(sector: str) -> dict:
        """Rank all 11 sectors by 20-day momentum. Only go long sectors in top 4."""
        try:
            sector_returns = {}
            for sec_name, etf in SECTOR_ETFS.items():
                df = get_history(etf, period="3mo")
                if df.empty or len(df) < 21:
                    continue
                ret = df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1
                sector_returns[sec_name] = ret

            if not sector_returns or sector not in sector_returns:
                return {"score": 0.5, "trend": "UNKNOWN"}

            # Rank sectors
            ranked = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
            rank = next((i + 1 for i, (s, _) in enumerate(ranked) if s == sector), 6)

            if rank <= 3:
                return {"score": 0.8, "signal": f"Sector rank #{rank}/11 (top quartile)"}
            elif rank <= 5:
                return {"score": 0.6, "signal": f"Sector rank #{rank}/11"}
            elif rank >= 9:
                return {"score": 0.15, "signal": f"Sector rank #{rank}/11 (bottom quartile)"}
            return {"score": 0.4}
        except Exception:
            return {"score": 0.5}

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
    def _true_relative_strength(symbol: str, sector: str) -> dict:
        """Stock return / sector ETF return = true alpha."""
        try:
            sym_df = get_history(symbol, period="3mo")
            etf = SECTOR_ETFS.get(sector)
            if not etf:
                return {"score": 0.5}

            etf_df = get_history(etf, period="3mo")
            if sym_df.empty or etf_df.empty or len(sym_df) < 21 or len(etf_df) < 21:
                return {"score": 0.5}

            sym_ret = sym_df["Close"].iloc[-1] / sym_df["Close"].iloc[-21] - 1
            etf_ret = etf_df["Close"].iloc[-1] / etf_df["Close"].iloc[-21] - 1

            excess = sym_ret - etf_ret
            if excess > 0.08:
                return {"score": 0.9, "signal": f"Strong alpha vs sector (+{excess:.0%})"}
            elif excess > 0.03:
                return {"score": 0.7, "signal": f"Outperforming sector (+{excess:.0%})"}
            elif excess < -0.08:
                return {"score": 0.15, "signal": f"Lagging sector ({excess:.0%})"}
            elif excess < -0.03:
                return {"score": 0.3, "signal": f"Underperforming sector ({excess:.0%})"}
            return {"score": 0.5}
        except Exception:
            return {"score": 0.5}

    @staticmethod
    def _correlation_check(symbol: str) -> dict:
        """If stock correlation to SPY > 0.95, sector engine provides no edge."""
        try:
            sym_df = get_history(symbol, period="3mo")
            spy_df = get_history("SPY", period="3mo")
            if sym_df.empty or spy_df.empty or len(sym_df) < 30:
                return {"score": 0.5}

            # Align on common dates
            common = sym_df.index.intersection(spy_df.index)
            if len(common) < 20:
                return {"score": 0.5}

            sym_ret = sym_df.loc[common, "Close"].pct_change().dropna()
            spy_ret = spy_df.loc[common, "Close"].pct_change().dropna()

            if len(sym_ret) < 20:
                return {"score": 0.5}

            corr = sym_ret.corr(spy_ret)
            if pd.isna(corr):
                return {"score": 0.5}

            if corr > 0.95:
                return {"score": 0.0, "signal": f"High SPY correlation ({corr:.2f}), no sector edge"}
            elif corr < 0.5:
                return {"score": 0.7, "signal": f"Low SPY correlation ({corr:.2f}), sector differentiation"}
            return {"score": 0.5}
        except Exception:
            return {"score": 0.5}

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
