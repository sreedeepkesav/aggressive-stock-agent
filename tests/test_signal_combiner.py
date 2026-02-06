"""Tests for the signal combiner logic."""

import pytest

from engines.base import EngineResult
from engines.signal_combiner import SignalCombiner, CombinedSignal


class MockEngine:
    """A fake engine that returns a pre-set result."""
    def __init__(self, name, signal, confidence):
        self._name = name
        self._signal = signal
        self._confidence = confidence

    @property
    def name(self):
        return self._name

    def analyze(self, symbol):
        return EngineResult(self._name, symbol, self._signal, self._confidence, ["mock reason"])


class TestSignalCombiner:
    def _make_combiner(self, engine_configs):
        """Create a combiner with mock engines."""
        combiner = SignalCombiner()
        combiner.engines = {}
        weights = {}
        for name, signal, conf, weight in engine_configs:
            combiner.engines[name] = MockEngine(name, signal, conf)
            weights[name] = weight
        combiner.weights = weights
        return combiner

    def test_unanimous_buy(self):
        combiner = self._make_combiner([
            ("a", "BUY", 0.8, 0.5),
            ("b", "BUY", 0.7, 0.5),
        ])
        sig = combiner.analyze("TEST")
        assert sig.action in ("BUY", "STRONG_BUY")
        assert sig.combined_score > 0
        assert sig.agreement_pct == 1.0

    def test_unanimous_sell(self):
        combiner = self._make_combiner([
            ("a", "SELL", 0.8, 0.5),
            ("b", "SELL", 0.7, 0.5),
        ])
        sig = combiner.analyze("TEST")
        assert sig.action in ("SELL", "STRONG_SELL")
        assert sig.combined_score < 0

    def test_mixed_signals_dampen(self):
        combiner = self._make_combiner([
            ("a", "BUY", 0.8, 0.34),
            ("b", "SELL", 0.8, 0.33),
            ("c", "HOLD", 0.5, 0.33),
        ])
        sig = combiner.analyze("TEST")
        # When engines disagree (agreement < 50%), result should be HOLD with reduced confidence
        assert sig.action == "HOLD"
        assert sig.confidence < 0.5

    def test_no_data_engines_ignored(self):
        combiner = self._make_combiner([
            ("a", "BUY", 0.8, 0.5),
            ("b", "NO_DATA", 0.0, 0.5),
        ])
        sig = combiner.analyze("TEST")
        assert sig.action in ("BUY", "STRONG_BUY")
        assert sig.agreement_pct == 1.0

    def test_is_actionable(self):
        sig = CombinedSignal(
            symbol="TEST", action="BUY", combined_score=0.5,
            confidence=0.6, engine_results={}, reasons=[], agreement_pct=0.8,
        )
        assert sig.is_actionable

        sig2 = CombinedSignal(
            symbol="TEST", action="HOLD", combined_score=0.1,
            confidence=0.3, engine_results={}, reasons=[], agreement_pct=0.4,
        )
        assert not sig2.is_actionable
