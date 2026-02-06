"""Tests for the learning/memory system."""

import os
import tempfile
import pytest

from engines.base import EngineResult
from portfolio import state
from portfolio.memory import (
    save_analysis, check_outcomes, compute_engine_accuracy,
    get_adaptive_weights, get_engine_performance_summary,
    get_analysis_history, DEFAULT_WEIGHTS, MIN_SAMPLES_FOR_ADAPTIVE,
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    state.init_db(path)
    state.set_cash_balance(100000.0, path)
    yield path
    os.unlink(path)


def _mock_engine_results():
    """Create mock engine results dict."""
    return {
        "momentum": EngineResult("momentum", "TEST", "BUY", 0.7, ["reason1"]),
        "fundamental": EngineResult("fundamental", "TEST", "BUY", 0.6, ["reason2"]),
        "technical": EngineResult("technical", "TEST", "HOLD", 0.4, ["reason3"]),
        "sector": EngineResult("sector", "TEST", "BUY", 0.5, ["reason4"]),
        "mean_reversion": EngineResult("mean_reversion", "TEST", "HOLD", 0.3, ["reason5"]),
    }


class TestSaveAnalysis:
    def test_save_returns_id(self, db_path):
        results = _mock_engine_results()
        analysis_id = save_analysis(
            symbol="NVDA", combined_score=0.45, action="BUY",
            confidence=0.6, agreement_pct=0.75, close_price=800.0,
            regime="TRENDING_UP", engine_results=results, db_path=db_path,
        )
        assert analysis_id is not None
        assert analysis_id > 0

    def test_save_multiple(self, db_path):
        results = _mock_engine_results()
        id1 = save_analysis("AAPL", 0.3, "BUY", 0.5, 0.6, 180.0, "TRENDING_UP", results, db_path)
        id2 = save_analysis("MSFT", -0.1, "HOLD", 0.4, 0.5, 400.0, "RANGE_BOUND", results, db_path)
        assert id1 != id2

    def test_analysis_history_retrieval(self, db_path):
        results = _mock_engine_results()
        save_analysis("NVDA", 0.5, "BUY", 0.7, 0.8, 800.0, "TRENDING_UP", results, db_path)

        history = get_analysis_history(symbol="NVDA", db_path=db_path)
        assert len(history) == 1
        assert history[0]["symbol"] == "NVDA"
        assert history[0]["action"] == "BUY"


class TestAdaptiveWeights:
    def test_returns_none_with_no_data(self, db_path):
        weights = get_adaptive_weights(db_path=db_path)
        assert weights is None

    def test_default_weights_structure(self):
        assert len(DEFAULT_WEIGHTS) == 5
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 0.01

    def test_min_samples_threshold(self):
        assert MIN_SAMPLES_FOR_ADAPTIVE == 30


class TestEnginePerformance:
    def test_empty_performance(self, db_path):
        perf = get_engine_performance_summary(db_path=db_path)
        assert isinstance(perf, list)

    def test_compute_accuracy_empty(self, db_path):
        result = compute_engine_accuracy(db_path=db_path)
        # Should return empty dict or dict with 0 totals
        assert isinstance(result, dict)
