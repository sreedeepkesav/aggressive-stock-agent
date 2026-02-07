"""Fundamental analysis scorer - with sector-relative valuation, earnings quality, ROIC, PEG weighting."""

import logging

from data.market_data import get_info
from data.earnings import get_earnings_surprise_history
from engines.base import BaseEngine, EngineResult

logger = logging.getLogger("stock_agent")

# Sector median P/E approximations (updated periodically)
SECTOR_MEDIAN_PE = {
    "Technology": 30, "Healthcare": 22, "Financials": 14, "Consumer Discretionary": 25,
    "Consumer Staples": 22, "Energy": 12, "Industrials": 20, "Materials": 16,
    "Utilities": 18, "Real Estate": 35, "Communication Services": 20,
}

_YFINANCE_SECTOR_MAP = {
    "Financial Services": "Financials", "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples", "Basic Materials": "Materials",
}


class FundamentalEngine(BaseEngine):
    """Scores fundamentals: profitability, growth, financial health, valuation (sector-relative), efficiency."""

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

            # Map sector
            raw_sector = info.get("sector", "")
            sector = _YFINANCE_SECTOR_MAP.get(raw_sector, raw_sector)

            # 1. Profitability (0.20)
            prof = self._profitability(info)
            scores["profitability"] = prof["score"]
            reasons.extend(prof["factors"])

            # 2. Growth + PEG + Earnings Surprise (0.25)
            growth = self._growth(info)
            # Add earnings surprise quality from actual quarterly data
            try:
                surprise = get_earnings_surprise_history(symbol)
                if surprise["beat_rate"] > 0.75:
                    growth["score"] = min(1.0, growth["score"] + 0.15)
                    growth["factors"].append(f"Earnings beat rate {surprise['beat_rate']:.0%}")
                if surprise["avg_surprise_pct"] > 5.0:
                    growth["score"] = min(1.0, growth["score"] + 0.10)
                    growth["factors"].append(f"Avg surprise +{surprise['avg_surprise_pct']:.1f}%")
                elif surprise["avg_surprise_pct"] < -2.0:
                    growth["score"] = max(0.0, growth["score"] - 0.10)
                    growth["factors"].append(f"Negative surprise trend {surprise['avg_surprise_pct']:.1f}%")
            except Exception:
                pass
            scores["growth"] = growth["score"]
            reasons.extend(growth["factors"])

            # 3. Financial health + earnings quality (0.20)
            health = self._health(info)
            scores["health"] = health["score"]
            reasons.extend(health["factors"])

            # 4. Sector-relative valuation (0.20)
            val = self._valuation_relative(info, sector)
            scores["valuation"] = val["score"]
            reasons.extend(val["factors"])

            # 5. Efficiency + ROIC (0.15)
            eff = self._efficiency(info)
            scores["efficiency"] = eff["score"]
            reasons.extend(eff["factors"])

            total = (
                scores["profitability"] * 0.20
                + scores["growth"] * 0.25
                + scores["health"] * 0.20
                + scores["valuation"] * 0.20
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
                                metadata={"sub_scores": scores, "sector": sector})

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
                score += 0.3; factors.append(f"High revenue growth {rg:.0%}")
            elif rg > 0.1:
                score += 0.2
            elif rg > 0.05:
                score += 0.1

        eg = info.get("earningsGrowth")
        if eg:
            if eg > 0.25:
                score += 0.3; factors.append(f"Strong earnings growth {eg:.0%}")
            elif eg > 0.15:
                score += 0.2

        # PEG ratio - weighted higher than raw P/E
        peg = info.get("pegRatio")
        if peg and 0 < peg < 1.0:
            score += 0.3; factors.append(f"Attractive PEG {peg:.1f}")
        elif peg and 0 < peg < 1.5:
            score += 0.2; factors.append(f"Fair PEG {peg:.1f}")
        elif peg and 0 < peg < 2.0:
            score += 0.1

        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _health(info: dict) -> dict:
        score, factors = 0.0, []
        de = info.get("debtToEquity")
        if de is not None:
            if de < 50:
                score += 0.3; factors.append(f"Low debt/equity {de:.0f}%")
            elif de < 100:
                score += 0.15

        cr = info.get("currentRatio")
        if cr:
            if cr > 2.0:
                score += 0.25; factors.append(f"Strong current ratio {cr:.1f}")
            elif cr > 1.5:
                score += 0.15

        fcf = info.get("freeCashflow")
        if fcf and fcf > 0:
            score += 0.2; factors.append("Positive FCF")

        # Earnings quality: operating cash flow > net income
        ocf = info.get("operatingCashflow")
        net_income = info.get("netIncomeToCommon")
        if ocf and net_income and ocf > 0 and net_income > 0:
            if ocf > net_income:
                score += 0.15; factors.append("Quality earnings (OCF > NI)")
            else:
                factors.append("Earnings quality concern (OCF < NI)")

        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _valuation_relative(info: dict, sector: str) -> dict:
        """Sector-relative valuation instead of global thresholds."""
        score, factors = 0.0, []
        sector_pe = SECTOR_MEDIAN_PE.get(sector, 20)

        # Forward P/E (preferred over trailing)
        fwd_pe = info.get("forwardPE")
        trail_pe = info.get("trailingPE")
        pe = fwd_pe or trail_pe
        pe_label = "Fwd P/E" if fwd_pe else "P/E"

        if pe and pe > 0:
            relative = pe / sector_pe
            if relative < 0.7:
                score += 0.4; factors.append(f"Cheap vs sector ({pe_label} {pe:.1f} vs median {sector_pe})")
            elif relative < 1.0:
                score += 0.25; factors.append(f"Below sector median ({pe_label} {pe:.1f})")
            elif relative < 1.3:
                score += 0.1
            elif relative > 2.0:
                factors.append(f"Expensive vs sector ({pe_label} {pe:.1f} vs median {sector_pe})")

        pb = info.get("priceToBook")
        if pb:
            if pb < 2:
                score += 0.2; factors.append(f"Low P/B {pb:.1f}")
            elif pb < 4:
                score += 0.1

        ps = info.get("priceToSalesTrailing12Months")
        if ps:
            if ps < 3:
                score += 0.2
            elif ps < 8:
                score += 0.1

        # Earnings surprise momentum
        surprise = info.get("earningsQuarterlyGrowth")
        if surprise and surprise > 0.1:
            score += 0.1; factors.append(f"Earnings beat momentum {surprise:.0%}")

        return {"score": min(1.0, score), "factors": factors}

    @staticmethod
    def _efficiency(info: dict) -> dict:
        score, factors = 0.0, []
        om = info.get("operatingMargins")
        if om:
            if om > 0.3:
                score += 0.4; factors.append(f"High operating margin {om:.0%}")
            elif om > 0.15:
                score += 0.25

        # ROIC approximation (better than ROE which is leverage-inflated)
        ebit = info.get("ebitda")
        total_assets = info.get("totalAssets")
        total_debt = info.get("totalDebt", 0) or 0
        cash = info.get("totalCash", 0) or 0

        if ebit and total_assets and total_assets > 0:
            invested_capital = total_assets - cash
            if invested_capital > 0:
                roic = ebit / invested_capital
                if roic > 0.2:
                    score += 0.4; factors.append(f"High ROIC ~{roic:.0%}")
                elif roic > 0.1:
                    score += 0.2

        return {"score": min(1.0, score), "factors": factors}
