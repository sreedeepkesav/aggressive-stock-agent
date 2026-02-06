"""Tests for engine base and signal combiner."""

import pytest
from engines.base import EngineResult, BaseEngine


class TestEngineResult:
    def test_numeric_signal_mapping(self):
        r = EngineResult("test", "AAPL", "STRONG_BUY", 0.9)
        assert r.numeric_signal == 1.0

        r2 = EngineResult("test", "AAPL", "SELL", 0.7)
        assert r2.numeric_signal == -0.5

        r3 = EngineResult("test", "AAPL", "HOLD", 0.5)
        assert r3.numeric_signal == 0.0

    def test_is_bullish_bearish(self):
        assert EngineResult("t", "X", "BUY", 0.5).is_bullish
        assert EngineResult("t", "X", "STRONG_BUY", 0.5).is_bullish
        assert not EngineResult("t", "X", "HOLD", 0.5).is_bullish

        assert EngineResult("t", "X", "SELL", 0.5).is_bearish
        assert EngineResult("t", "X", "STRONG_SELL", 0.5).is_bearish
        assert not EngineResult("t", "X", "HOLD", 0.5).is_bearish

    def test_no_data_is_neutral(self):
        r = EngineResult("t", "X", "NO_DATA", 0.0)
        assert r.numeric_signal == 0.0
        assert not r.is_bullish
        assert not r.is_bearish
