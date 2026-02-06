"""Tests for market regime detection."""

import pytest
import numpy as np
import pandas as pd

from engines.regime import (
    MarketRegime, RegimeInfo, REGIME_WEIGHTS,
    _classify_regime, _default_regime,
)


class TestRegimeClassification:
    def test_trending_up(self):
        regime = _classify_regime(
            spy_price=450, sma50=440, sma200=420,
            sma50_slope=0.005, vix=18, breadth=0.72,
            vol_20d=0.12, vol_60d=0.13,
        )
        assert regime == MarketRegime.TRENDING_UP

    def test_trending_down(self):
        regime = _classify_regime(
            spy_price=400, sma50=420, sma200=440,
            sma50_slope=-0.003, vix=28, breadth=0.35,
            vol_20d=0.18, vol_60d=0.15,
        )
        assert regime == MarketRegime.TRENDING_DOWN

    def test_high_volatility_vix(self):
        regime = _classify_regime(
            spy_price=430, sma50=440, sma200=445,
            sma50_slope=-0.002, vix=35, breadth=0.45,
            vol_20d=0.30, vol_60d=0.15,
        )
        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_high_volatility_realized(self):
        regime = _classify_regime(
            spy_price=430, sma50=440, sma200=445,
            sma50_slope=-0.002, vix=25, breadth=0.45,
            vol_20d=0.35, vol_60d=0.14,
        )
        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_range_bound_low_slope(self):
        regime = _classify_regime(
            spy_price=440, sma50=441, sma200=435,
            sma50_slope=0.0005, vix=18, breadth=0.50,
            vol_20d=0.12, vol_60d=0.12,
        )
        assert regime == MarketRegime.RANGE_BOUND


class TestRegimeWeights:
    def test_all_regimes_have_weights(self):
        for regime in MarketRegime:
            assert regime in REGIME_WEIGHTS

    def test_weights_sum_to_one(self):
        for regime, weights in REGIME_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"{regime}: weights sum to {total}"

    def test_trending_up_favors_momentum(self):
        w = REGIME_WEIGHTS[MarketRegime.TRENDING_UP]
        assert w["momentum"] >= w["mean_reversion"]

    def test_range_bound_favors_mean_reversion(self):
        w = REGIME_WEIGHTS[MarketRegime.RANGE_BOUND]
        assert w["mean_reversion"] >= w["momentum"]

    def test_high_vol_favors_fundamentals(self):
        w = REGIME_WEIGHTS[MarketRegime.HIGH_VOLATILITY]
        assert w["fundamental"] >= w["momentum"]
        assert w["fundamental"] >= w["technical"]


class TestRegimeInfo:
    def test_default_regime(self):
        regime = _default_regime()
        assert regime.regime == MarketRegime.UNKNOWN
        assert regime.vix_level == 20.0
        assert not regime.block_buys
        assert regime.confidence_multiplier == 1.0

    def test_summary_string(self):
        regime = _default_regime()
        summary = regime.summary
        assert "UNKNOWN" in summary
        assert "VIX" in summary

    def test_block_buys(self):
        regime = RegimeInfo(
            regime=MarketRegime.HIGH_VOLATILITY, vix_level=40,
            spy_trend="BEARISH", breadth_pct=0.3,
            spy_daily_return=-0.02, realized_vol_20d=0.3, realized_vol_60d=0.15,
            weights=REGIME_WEIGHTS[MarketRegime.HIGH_VOLATILITY],
            confidence_multiplier=0.5, block_buys=True,
        )
        assert regime.block_buys
        assert regime.confidence_multiplier < 1.0
