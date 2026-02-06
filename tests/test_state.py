"""Tests for SQLite portfolio state."""

import os
import tempfile
import pytest

from portfolio.models import Position, Trade, Order
from portfolio import state


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    state.init_db(path)
    yield path
    os.unlink(path)


class TestPortfolioState:
    def test_init_db(self, db_path):
        # Should not raise
        state.init_db(db_path)

    def test_cash_balance(self, db_path):
        assert state.get_cash_balance(db_path) == 100000.0
        state.set_cash_balance(50000.0, db_path)
        assert state.get_cash_balance(db_path) == 50000.0

    def test_peak_value(self, db_path):
        assert state.get_peak_value(db_path) == 100000.0
        state.set_peak_value(120000.0, db_path)
        assert state.get_peak_value(db_path) == 120000.0

    def test_add_get_position(self, db_path):
        pos = Position(
            symbol="AAPL", quantity=10, entry_price=150.0,
            entry_date="2024-01-01", stop_loss=140.0, target_price=170.0,
        )
        pos_id = state.add_position(pos, db_path)
        assert pos_id > 0

        positions = state.get_positions(db_path)
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 10

    def test_remove_position(self, db_path):
        pos = Position(
            symbol="MSFT", quantity=5, entry_price=300.0,
            entry_date="2024-01-01", stop_loss=280.0, target_price=350.0,
        )
        pos_id = state.add_position(pos, db_path)
        state.remove_position(pos_id, db_path)
        assert len(state.get_positions(db_path)) == 0

    def test_add_get_trade(self, db_path):
        trade = Trade(
            symbol="NVDA", side="SELL", quantity=10,
            entry_price=500.0, exit_price=600.0,
            entry_date="2024-01-01", exit_date="2024-02-01",
            pnl=1000.0, pnl_pct=0.20, reason="Target reached",
        )
        trade_id = state.add_trade(trade, db_path)
        assert trade_id > 0

        trades = state.get_trades(path=db_path)
        assert len(trades) == 1
        assert trades[0].pnl == 1000.0

    def test_position_properties(self):
        pos = Position(
            symbol="AAPL", quantity=10, entry_price=100.0,
            entry_date="2024-01-01", stop_loss=90.0, target_price=120.0,
            current_price=110.0,
        )
        assert pos.cost_basis == 1000.0
        assert pos.market_value == 1100.0
        assert pos.unrealized_pnl == 100.0
        assert pos.unrealized_pnl_pct == pytest.approx(0.10)
