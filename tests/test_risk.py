"""Tests for risk management."""

import os
import tempfile
import pytest

from config.settings import RiskParams
from portfolio.models import Position
from portfolio import state
from portfolio.risk import RiskManager


@pytest.fixture
def db_path():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    state.init_db(path)
    state.set_cash_balance(100000.0, path)
    state.set_peak_value(100000.0, path)
    yield path
    os.unlink(path)


class TestRiskManager:
    def test_default_params(self):
        rm = RiskManager()
        assert rm.params.max_position_pct == 0.10
        assert rm.params.max_simultaneous_positions == 5
        assert rm.params.drawdown_circuit_breaker == -0.10

    def test_custom_params(self):
        params = RiskParams(max_position_pct=0.05, max_simultaneous_positions=3)
        rm = RiskManager(params)
        assert rm.params.max_position_pct == 0.05


class TestRiskParams:
    def test_from_env_defaults(self):
        params = RiskParams.from_env()
        assert params.max_position_pct == 0.10
        assert params.cash_reserve_pct == 0.20
        assert params.stop_loss_atr_swing == 2.0

    def test_from_env_override(self, monkeypatch):
        monkeypatch.setenv("MAX_POSITION_PCT", "0.15")
        monkeypatch.setenv("MAX_SIMULTANEOUS_POSITIONS", "3")
        params = RiskParams.from_env()
        assert params.max_position_pct == 0.15
        assert params.max_simultaneous_positions == 3
