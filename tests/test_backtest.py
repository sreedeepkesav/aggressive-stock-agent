"""Tests for the backtesting framework."""

import pytest
import numpy as np
import pandas as pd

from portfolio.backtest import (
    BacktestResult, BacktestTrade, _quick_score, format_backtest_report,
)


def _make_test_df(n=100, start_price=100.0):
    """Generate synthetic OHLCV DataFrame with indicators for backtesting."""
    np.random.seed(42)
    close = start_price + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    volume = np.random.randint(1_000_000, 10_000_000, size=n).astype(float)

    df = pd.DataFrame({
        "Open": close + np.random.randn(n) * 0.5,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=pd.date_range("2024-01-01", periods=n))

    # Add indicator columns the scoring function expects
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["RSI"] = 50 + np.random.randn(n) * 15
    df["MACD_Histogram"] = np.random.randn(n) * 0.5
    df["Volume_Ratio"] = 1.0 + np.abs(np.random.randn(n) * 0.3)
    df["BB_PctB"] = 0.5 + np.random.randn(n) * 0.2
    df["Stoch_K"] = 50 + np.random.randn(n) * 20
    df["Stoch_D"] = 50 + np.random.randn(n) * 20

    return df


class TestQuickScore:
    def test_returns_float(self):
        df = _make_test_df()
        score = _quick_score(df, 80)
        assert isinstance(score, float)

    def test_score_in_range(self):
        df = _make_test_df()
        for idx in range(50, 90):
            score = _quick_score(df, idx)
            assert 0.0 <= score <= 1.0

    def test_empty_returns_zero(self):
        df = pd.DataFrame()
        score = _quick_score(df, 0)
        assert score == 0.0


class TestBacktestResult:
    def test_default_values(self):
        result = BacktestResult(period_months=12, symbols_tested=["AAPL", "MSFT"])
        assert result.total_trades == 0
        assert result.sharpe_ratio == 0.0
        assert result.win_rate == 0.0
        assert len(result.trades) == 0

    def test_summary_string(self):
        result = BacktestResult(
            period_months=12, symbols_tested=["AAPL"],
            total_trades=50, winning_trades=30, losing_trades=20,
            total_return_pct=0.15, spy_return_pct=0.10, excess_return_pct=0.05,
            sharpe_ratio=1.2, max_drawdown_pct=-0.08, win_rate=0.6,
            profit_factor=1.8,
            avg_win_pct=0.05, avg_loss_pct=-0.03,
        )
        summary = result.summary
        assert "12mo" in summary
        assert "50 trades" in summary
        assert "1.20" in summary


class TestBacktestTrade:
    def test_trade_creation(self):
        trade = BacktestTrade(
            symbol="NVDA", entry_date="2024-01-01",
            entry_price=500.0, exit_date="2024-02-01",
            exit_price=550.0, quantity=100,
            pnl=5000.0, pnl_pct=0.10,
        )
        assert trade.pnl == 5000.0
        assert trade.pnl_pct == 0.10


class TestFormatReport:
    def test_format_empty_result(self):
        result = BacktestResult(period_months=6, symbols_tested=["AAPL"])
        report = format_backtest_report(result)
        assert "BACKTEST RESULTS" in report
        assert "6 months" in report

    def test_format_with_trades(self):
        trades = [
            BacktestTrade("AAPL", "2024-01-01", 150.0, "2024-02-01", 165.0, 100, 1500, 0.10),
            BacktestTrade("MSFT", "2024-01-15", 300.0, "2024-02-15", 280.0, 50, -1000, -0.067),
        ]
        result = BacktestResult(
            period_months=12, symbols_tested=["AAPL", "MSFT"],
            total_trades=2, winning_trades=1, losing_trades=1,
            total_return_pct=0.05, spy_return_pct=0.03, excess_return_pct=0.02,
            sharpe_ratio=0.8, max_drawdown_pct=-0.05, win_rate=0.5,
            profit_factor=1.5, avg_win_pct=0.10, avg_loss_pct=-0.067,
            trades=trades,
        )
        report = format_backtest_report(result)
        assert "AAPL" in report
        assert "Top 5 Trades" in report
