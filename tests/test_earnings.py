"""Tests for earnings calendar awareness."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from data.earnings import (
    get_next_earnings_date,
    get_earnings_surprise_history,
    days_until_earnings,
    is_earnings_blackout,
    _parse_date,
    _earnings_cache,
    _surprise_cache,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear earnings caches before each test."""
    _earnings_cache.clear()
    _surprise_cache.clear()
    yield
    _earnings_cache.clear()
    _surprise_cache.clear()


class TestParseDate:
    def test_date_object(self):
        d = date(2025, 3, 15)
        assert _parse_date(d) == d

    def test_string_date(self):
        assert _parse_date("2025-03-15") == date(2025, 3, 15)

    def test_none(self):
        assert _parse_date(None) is None

    def test_invalid(self):
        assert _parse_date("not-a-date") is None


class TestDaysUntilEarnings:
    @patch("data.earnings.get_next_earnings_date")
    def test_future_earnings(self, mock_next):
        mock_next.return_value = date.today() + timedelta(days=5)
        result = days_until_earnings("AAPL")
        assert result == 5

    @patch("data.earnings.get_next_earnings_date")
    def test_no_data(self, mock_next):
        mock_next.return_value = None
        assert days_until_earnings("UNKNOWN") is None

    @patch("data.earnings.get_next_earnings_date")
    def test_earnings_today(self, mock_next):
        mock_next.return_value = date.today()
        assert days_until_earnings("AAPL") == 0


class TestIsEarningsBlackout:
    @patch("data.earnings.days_until_earnings")
    def test_within_blackout(self, mock_days):
        mock_days.return_value = 2
        assert is_earnings_blackout("AAPL", days_before=3) is True

    @patch("data.earnings.days_until_earnings")
    def test_earnings_day(self, mock_days):
        mock_days.return_value = 0
        assert is_earnings_blackout("AAPL") is True

    @patch("data.earnings.days_until_earnings")
    def test_outside_blackout(self, mock_days):
        mock_days.return_value = 10
        assert is_earnings_blackout("AAPL", days_before=3) is False

    @patch("data.earnings.days_until_earnings")
    def test_no_data(self, mock_days):
        mock_days.return_value = None
        assert is_earnings_blackout("UNKNOWN") is False

    @patch("data.earnings.days_until_earnings")
    def test_custom_window(self, mock_days):
        mock_days.return_value = 5
        assert is_earnings_blackout("AAPL", days_before=5) is True
        assert is_earnings_blackout("AAPL", days_before=4) is False


class TestEarningsSurpriseHistory:
    @patch("data.earnings.yf.Ticker")
    def test_no_data(self, mock_ticker):
        mock_ticker.return_value.earnings_dates = None
        result = get_earnings_surprise_history("FAKE")
        assert result["beat_rate"] == 0.0
        assert result["avg_surprise_pct"] == 0.0
        assert result["consecutive_beats"] == 0

    def test_caching(self):
        _surprise_cache["TEST"] = {"avg_surprise_pct": 5.0, "beat_rate": 0.8, "consecutive_beats": 3}
        result = get_earnings_surprise_history("TEST")
        assert result["beat_rate"] == 0.8
