"""Fundamental analysis scorer - adapted from FundamentalAnalysisScorer."""

import logging

from data.market_data import get_info
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")


class FundamentalEngine(BaseEngine):
    """Scores fundamentals: profitability, growth, financial health, valuation, efficiency."""

    @property
    def name(self) -> str:
        return "fundamental"

    def analyze(self, symbol: str) -> EngineResult:
        info = get_info(symbol)
        if not info:
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, ["No fundamental data"])

        try:
            reasons = []
            scores = {}

            # 1. Profitability (0.25)
            prof = self._profitability(info)
            scores["profitability"] = prof["score"]
            reasons.extend(prof["factors"])

            # 2. Growth (0.25)
            growth = self._growth(info)
            scores["growth"] = growth["score"]
            reasons.extend(growth["factors"])

            # 3. Financial health (0.2)
            health = self._health(info)
            scores["health"] = health["score"]
            reasons.extend(health["factors"])

            # 4. Valuation (0.15)
            val = self._valuation(info)
            scores["valuation"] = val["score"]
            reasons.extend(val["factors"])

            # 5. Efficiency (0.15)
            eff = self._efficiency(info)
            scores["efficiency"] = eff["score"]
            reasons.extend(eff["factors"])

            total = (
                scores["profitability"] * 0.25
                + scores["growth"] * 0.25
                + scores["health"] * 0.20
                + scores["valuation"] * 0.15
                + scores["efficiency"] * 0.15
            )
            total = min(1.0, total)

            if total >= 0.65:
                signal = "BUY"
            elif total >= 0.5:
                signal = "HOLD"
            elif total >= 0.35:
                signal = "HOLD"
            else:
                signal = "SELL"

            return EngineResult(self.name, symbol, signal, total, reasons[:6],
                                metadata={"sub_scores": scores})

        except Exception as e:
            logger.error(f"Fundamental analysis failed for {symbol}: {e}")
            return EngineResult(self.name, symbol, "NO_DATA", 0.0, [str(e)])

    @staticmethod
    def _profitability(info: dict) -> dict:
        score, factors = 0.0, []
        pm = info.get("profitMargins")
        if pm:
            if pm > 0.2:
                score += 0.3; factors.append(f"High profit margin {pm:.0%}")
            elif pm > 0.1:
                score += 0.2; factors.append(f"Good profit margin {pm:.0%}")
            elif pm > 0.05:
                score += 0.1
        roe = info.get("returnOnEquity")
        if roe:
            if roe > 0.2:
                score += 0.3; factors.append(f"Excellent ROE {roe:.0%}")
            elif roe > 0.15:
                score += 0.2
            elif roe > 0.1:
                score += 0.1
        roa = info.get("returnOnAssets")
        if roa and roa > 0.1:
            score += 0.2; factors.append(f"High ROA {roa:.0%}")
        elif roa and roa > 0.05:
            score += 0.1
        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _growth(info: dict) -> dict:
        score, factors = 0.0, []
        rg = info.get("revenueGrowth")
        if rg:
            if rg > 0.2:
                score += 0.4; factors.append(f"High revenue growth {rg:.0%}")
            elif rg > 0.1:
                score += 0.3
            elif rg > 0.05:
                score += 0.1
        eg = info.get("earningsGrowth")
        if eg:
            if eg > 0.25:
                score += 0.4; factors.append(f"Strong earnings growth {eg:.0%}")
            elif eg > 0.15:
                score += 0.3
        peg = info.get("pegRatio")
        if peg and 0 < peg < 1.0:
            score += 0.2; factors.append(f"Attractive PEG {peg:.1f}")
        elif peg and 0 < peg < 1.5:
            score += 0.1
        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _health(info: dict) -> dict:
        score, factors = 0.0, []
        de = info.get("debtToEquity")
        if de is not None:
            if de < 50:
                score += 0.4; factors.append(f"Low debt/equity {de:.0f}%")
            elif de < 100:
                score += 0.2
        cr = info.get("currentRatio")
        if cr:
            if cr > 2.0:
                score += 0.3; factors.append(f"Strong current ratio {cr:.1f}")
            elif cr > 1.5:
                score += 0.2
        fcf = info.get("freeCashflow")
        if fcf and fcf > 0:
            score += 0.3; factors.append("Positive FCF")
        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _valuation(info: dict) -> dict:
        score, factors = 0.0, []
        pe = info.get("trailingPE")
        if pe:
            if pe < 15:
                score += 0.4; factors.append(f"Low P/E {pe:.1f}")
            elif pe < 25:
                score += 0.2
        pb = info.get("priceToBook")
        if pb:
            if pb < 2:
                score += 0.3; factors.append(f"Low P/B {pb:.1f}")
            elif pb < 4:
                score += 0.15
        ps = info.get("priceToSalesTrailing12Months")
        if ps:
            if ps < 3:
                score += 0.3
            elif ps < 8:
                score += 0.1
        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _efficiency(info: dict) -> dict:
        score, factors = 0.0, []
        om = info.get("operatingMargins")
        if om:
            if om > 0.3:
                score += 0.5; factors.append(f"High operating margin {om:.0%}")
            elif om > 0.15:
                score += 0.3
        at = info.get("totalRevenue") and info.get("totalAssets")
        # Simple asset turnover proxy not in yfinance info, skip
        return {"score": min(1.0, score), "factors": factors}
