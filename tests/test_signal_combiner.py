"""Tests for the signal combiner logic."""

import pytest

from engines.base import EngineResult
from engines.signal_combiner import SignalCombiner, CombinedSignal, DEFAULT_WEIGHTS
from engines.regime import RegimeInfo, MarketRegime, REGIME_WEIGHTS


class MockEngine:
    """A fake engine that returns a pre-set result."""
    def __init__(self, name, signal, confidence):
        self._name = name
        self._signal = signal
        self._confidence = confidence

    @property
    def name(self):
        return self._name

    def analyze(self, symbol, **kwargs):
        return EngineResult(self._name, symbol, self._signal, self._confidence, ["mock reason"])


def _mock_regime(regime=MarketRegime.UNKNOWN):
    """Create a mock RegimeInfo for testing."""
    return RegimeInfo(
        regime=regime, vix_level=20.0, spy_trend="NEUTRAL",
        breadth_pct=0.5, spy_daily_return=0.0,
        realized_vol_20d=0.15, realized_vol_60d=0.15,
        weights=REGIME_WEIGHTS[regime].copy(),
        confidence_multiplier=1.0, block_buys=False,
    )


class TestSignalCombiner:
    def _make_combiner(self, engine_configs, regime=None):
        """Create a combiner with mock engines."""
        combiner = SignalCombiner(regime_info=regime or _mock_regime())
        combiner.engines = {}
        weights = {}
        for name, signal, conf, weight in engine_configs:
            combiner.engines[name] = MockEngine(name, signal, conf)
            weights[name] = weight
        combiner.default_weights = weights
        # Override regime weights to match our test weights
        combiner._regime_info.weights = weights
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

    def test_regime_present_in_signal(self):
        regime = _mock_regime(MarketRegime.TRENDING_UP)
        combiner = self._make_combiner([
            ("a", "BUY", 0.8, 1.0),
        ], regime=regime)
        sig = combiner.analyze("TEST")
        assert sig.regime is not None
        assert sig.regime.regime == MarketRegime.TRENDING_UP

    def test_block_buys_when_vix_high(self):
        regime = _mock_regime(MarketRegime.HIGH_VOLATILITY)
        regime.block_buys = True
        regime.vix_level = 40.0
        combiner = self._make_combiner([
            ("a", "BUY", 0.9, 0.5),
            ("b", "BUY", 0.8, 0.5),
        ], regime=regime)
        sig = combiner.analyze("TEST")
        # Score should be heavily dampened
        assert sig.combined_score < 0.2
        assert sig.confidence < 0.4

    def test_adaptive_weights_blended(self):
        regime = _mock_regime()
        combiner = SignalCombiner(regime_info=regime)
        adaptive = {"momentum": 0.40, "fundamental": 0.10, "technical": 0.20,
                     "sector": 0.15, "mean_reversion": 0.15}
        weights = combiner.get_active_weights(adaptive)
        # Weights should be blended (70% adaptive + 30% regime) and sum to ~1.0
        assert abs(sum(weights.values()) - 1.0) < 0.01
        # Momentum should be higher than default due to adaptive boost
        assert weights["momentum"] > DEFAULT_WEIGHTS["momentum"]
