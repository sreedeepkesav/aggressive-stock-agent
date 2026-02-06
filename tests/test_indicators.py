"""Tests for canonical indicator implementations."""

import numpy as np
import pandas as pd
import pytest

from data.indicators import (
    calculate_rsi, rsi_latest, calculate_sma, calculate_ema,
    calculate_atr, calculate_macd, calculate_bollinger_bands,
    calculate_obv, add_all_indicators,
    calculate_stochastic, calculate_vwap, calculate_roc,
    calculate_bb_pctb, calculate_keltner_channels, calculate_adl,
)


def _make_ohlcv(n=100, start_price=100.0):
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    close = start_price + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    volume = np.random.randint(1_000_000, 10_000_000, size=n).astype(float)
    return pd.DataFrame({
        "Open": close + np.random.randn(n) * 0.5,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=pd.date_range("2024-01-01", periods=n))


class TestRSI:
    def test_rsi_range(self):
        df = _make_ohlcv(200)
        rsi = calculate_rsi(df["Close"])
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_latest_short_data(self):
        assert rsi_latest(pd.Series([1, 2, 3]), period=14) == 50.0

    def test_rsi_latest_normal(self):
        df = _make_ohlcv(100)
        val = rsi_latest(df["Close"])
        assert 0 <= val <= 100


class TestSMA:
    def test_sma_length(self):
        s = pd.Series(range(50))
        sma = calculate_sma(s, 20)
        assert len(sma) == 50
        assert pd.isna(sma.iloc[18])
        assert not pd.isna(sma.iloc[19])

    def test_sma_value(self):
        s = pd.Series([1.0] * 20)
        assert calculate_sma(s, 20).iloc[-1] == 1.0


class TestEMA:
    def test_ema_length(self):
        s = pd.Series(range(50))
        ema = calculate_ema(s, 12)
        assert len(ema) == 50

    def test_ema_follows_trend(self):
        s = pd.Series(range(50), dtype=float)
        ema = calculate_ema(s, 12)
        # EMA of uptrend should be below last value (lagging)
        assert ema.iloc[-1] < 49


class TestATR:
    def test_atr_positive(self):
        df = _make_ohlcv(100)
        atr = calculate_atr(df)
        valid = atr.dropna()
        assert (valid > 0).all()


class TestMACD:
    def test_macd_components(self):
        df = _make_ohlcv(100)
        line, signal, hist = calculate_macd(df["Close"])
        assert len(line) == 100
        assert len(signal) == 100
        # Histogram = line - signal
        diff = (line - signal - hist).dropna().abs()
        assert (diff < 1e-10).all()


class TestBollingerBands:
    def test_upper_above_lower(self):
        df = _make_ohlcv(100)
        upper, middle, lower = calculate_bollinger_bands(df["Close"])
        valid_idx = upper.dropna().index
        assert (upper[valid_idx] >= lower[valid_idx]).all()


class TestOBV:
    def test_obv_length(self):
        df = _make_ohlcv(100)
        obv = calculate_obv(df["Close"], df["Volume"])
        assert len(obv) == 100


class TestStochastic:
    def test_stochastic_range(self):
        df = _make_ohlcv(100)
        pct_k, pct_d = calculate_stochastic(df)
        valid_k = pct_k.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()

    def test_stochastic_length(self):
        df = _make_ohlcv(100)
        pct_k, pct_d = calculate_stochastic(df)
        assert len(pct_k) == 100


class TestVWAP:
    def test_vwap_positive(self):
        df = _make_ohlcv(100)
        vwap = calculate_vwap(df)
        valid = vwap.dropna()
        assert (valid > 0).all()


class TestROC:
    def test_roc_length(self):
        s = pd.Series(range(50), dtype=float)
        roc = calculate_roc(s, 12)
        assert len(roc) == 50


class TestBBPctB:
    def test_pctb_basic(self):
        df = _make_ohlcv(100)
        pctb = calculate_bb_pctb(df["Close"])
        valid = pctb.dropna()
        # Most values should be between -0.5 and 1.5
        assert len(valid) > 0


class TestKeltnerChannels:
    def test_keltner_order(self):
        df = _make_ohlcv(100)
        upper, middle, lower = calculate_keltner_channels(df)
        valid_idx = upper.dropna().index.intersection(lower.dropna().index)
        assert (upper[valid_idx] >= lower[valid_idx]).all()


class TestADL:
    def test_adl_length(self):
        df = _make_ohlcv(100)
        adl = calculate_adl(df)
        assert len(adl) == 100


class TestAddAllIndicators:
    def test_adds_columns(self):
        df = _make_ohlcv(100)
        result = add_all_indicators(df)
        expected = [
            "SMA_20", "SMA_50", "RSI", "MACD", "ATR", "BB_Upper", "BB_Lower", "OBV",
            "Stoch_K", "Stoch_D", "ROC_12", "VWAP", "BB_PctB",
            "Keltner_Upper", "Keltner_Lower", "ADL",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column: {col}"

    def test_short_data_returns_same(self):
        df = _make_ohlcv(10)
        result = add_all_indicators(df)
        # Should return unchanged since len < 50
        assert "RSI" not in result.columns
