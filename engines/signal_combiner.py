"""Signal combiner: weighted combination of all engine results into actual trade decisions.

This is the critical piece that was MISSING from the original codebase.
Previously, engines ran and printed output but their results were never
combined into actionable buy/sell decisions.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from engines.base import BaseEngine, EngineResult
from engines.momentum import MomentumEngine
from engines.technical import TechnicalEngine
from engines.sector import SectorEngine
from engines.mean_reversion import MeanReversionEngine
from engines.fundamental import FundamentalEngine

logger = logging.getLogger("stock_agent")

# Default engine weights (sum to 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "momentum": 0.25,
    "fundamental": 0.25,
    "technical": 0.20,
    "sector": 0.15,
    "mean_reversion": 0.15,
}


@dataclass
class CombinedSignal:
    """The final trade decision produced by combining all engine results."""
    symbol: str
    action: str          # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    combined_score: float  # -1.0 to +1.0
    confidence: float      # 0.0 to 1.0 (agreement level)
    engine_results: Dict[str, EngineResult]
    reasons: List[str]
    agreement_pct: float   # What fraction of engines agree on direction

    @property
    def is_actionable(self) -> bool:
        """Only act on high-confidence signals with reasonable agreement."""
        return self.confidence >= 0.5 and self.agreement_pct >= 0.6


class SignalCombiner:
    """Runs all engines and combines their signals into a single trade decision."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.engines: Dict[str, BaseEngine] = {
            "momentum": MomentumEngine(),
            "technical": TechnicalEngine(),
            "sector": SectorEngine(),
            "mean_reversion": MeanReversionEngine(),
            "fundamental": FundamentalEngine(),
        }

    def analyze(self, symbol: str) -> CombinedSignal:
        """Run all engines and produce a combined signal."""
        results: Dict[str, EngineResult] = {}
        all_reasons = []

        for name, engine in self.engines.items():
            try:
                result = engine.analyze(symbol)
                results[name] = result
                if result.reasons:
                    prefix = name.replace("_", " ").title()
                    for r in result.reasons[:2]:
                        all_reasons.append(f"[{prefix}] {r}")
            except Exception as e:
                logger.error(f"Engine {name} failed for {symbol}: {e}")
                results[name] = EngineResult(name, symbol, "NO_DATA", 0.0, [str(e)])

        # Weighted combination of numeric signals (-1 to +1)
        weighted_sum = 0.0
        weight_sum = 0.0
        confidence_sum = 0.0

        for name, result in results.items():
            if result.signal == "NO_DATA":
                continue
            w = self.weights.get(name, 0.0)
            weighted_sum += result.numeric_signal * w * result.confidence
            weight_sum += w
            confidence_sum += result.confidence * w

        if weight_sum > 0:
            combined_score = weighted_sum / weight_sum
            avg_confidence = confidence_sum / weight_sum
        else:
            combined_score = 0.0
            avg_confidence = 0.0

        # Calculate agreement: what fraction of engines agree on direction?
        valid = [r for r in results.values() if r.signal != "NO_DATA"]
        if valid:
            bullish_count = sum(1 for r in valid if r.is_bullish)
            bearish_count = sum(1 for r in valid if r.is_bearish)
            majority = max(bullish_count, bearish_count)
            agreement_pct = majority / len(valid)
        else:
            agreement_pct = 0.0

        # Dampening: when engines disagree strongly, reduce confidence
        if agreement_pct < 0.5:
            avg_confidence *= 0.6
            combined_score *= 0.5

        # Map combined score to action
        if combined_score >= 0.6:
            action = "STRONG_BUY"
        elif combined_score >= 0.3:
            action = "BUY"
        elif combined_score > -0.3:
            action = "HOLD"
        elif combined_score > -0.6:
            action = "SELL"
        else:
            action = "STRONG_SELL"

        return CombinedSignal(
            symbol=symbol,
            action=action,
            combined_score=round(combined_score, 4),
            confidence=round(avg_confidence, 4),
            engine_results=results,
            reasons=all_reasons[:10],
            agreement_pct=round(agreement_pct, 2),
        )

    def analyze_multiple(self, symbols: List[str]) -> List[CombinedSignal]:
        """Analyze multiple symbols and return sorted by combined score."""
        signals = []
        for sym in symbols:
            try:
                sig = self.analyze(sym)
                signals.append(sig)
            except Exception as e:
                logger.error(f"Failed to analyze {sym}: {e}")
        signals.sort(key=lambda s: s.combined_score, reverse=True)
        return signals
