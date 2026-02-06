"""Learning system: save predictions, compare to outcomes, adjust engine weights.

Core loop:
1. save_analysis() - called after every analysis run
2. check_outcomes() - called at startup, fills in actual returns for old analyses
3. compute_engine_accuracy() - rolling accuracy per engine per regime
4. get_adaptive_weights() - returns weights adjusted by engine performance
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from portfolio.state import _get_db, init_db

logger = logging.getLogger("stock_agent")

# Outcome check intervals (trading days after analysis)
OUTCOME_DAYS = [1, 3, 5, 10, 20]
MIN_SAMPLES_FOR_ADAPTIVE = 30
ADAPTIVE_BLEND = 0.7  # 70% adaptive + 30% default

DEFAULT_WEIGHTS = {
    "momentum": 0.25,
    "fundamental": 0.25,
    "technical": 0.20,
    "sector": 0.15,
    "mean_reversion": 0.15,
}


def save_analysis(symbol: str, combined_score: float, action: str, confidence: float,
                  agreement_pct: float, close_price: float, regime: str,
                  engine_results: dict, db_path: str = None) -> Optional[int]:
    """Save an analysis run and its per-engine signals to the database.

    Args:
        engine_results: Dict[str, EngineResult] from SignalCombiner
    Returns:
        analysis_id or None on failure
    """
    try:
        conn = _get_db(db_path)
        cur = conn.execute(
            """INSERT INTO analysis_history
               (symbol, analysis_date, combined_score, action, confidence, agreement_pct, close_price, regime)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, datetime.now().isoformat(), combined_score, action, confidence,
             agreement_pct, close_price, regime),
        )
        analysis_id = cur.lastrowid

        for eng_name, result in engine_results.items():
            conn.execute(
                """INSERT INTO engine_signals
                   (analysis_id, engine_name, signal, confidence, numeric_signal)
                   VALUES (?, ?, ?, ?, ?)""",
                (analysis_id, eng_name, result.signal, result.confidence, result.numeric_signal),
            )

        conn.commit()
        conn.close()
        return analysis_id
    except Exception as e:
        logger.error(f"Failed to save analysis for {symbol}: {e}")
        return None


def check_outcomes(db_path: str = None) -> int:
    """Check actual outcomes for analyses that are old enough.

    For each analysis without outcomes at N days, fetch the actual price
    N trading days later and record whether the signal was correct.

    Returns number of outcomes filled.
    """
    try:
        conn = _get_db(db_path)
        # Find analyses without outcomes that are old enough
        rows = conn.execute(
            """SELECT ah.id, ah.symbol, ah.analysis_date, ah.combined_score, ah.action, ah.close_price
               FROM analysis_history ah
               WHERE ah.id NOT IN (
                   SELECT DISTINCT analysis_id FROM analysis_outcomes WHERE days_after = 5
               )
               AND ah.analysis_date < ?
               ORDER BY ah.analysis_date""",
            ((datetime.now() - timedelta(days=7)).isoformat(),)
        ).fetchall()

        filled = 0
        for row in rows:
            analysis_id = row["id"]
            symbol = row["symbol"]
            analysis_date_str = row["analysis_date"]
            entry_price = row["close_price"]
            action = row["action"]

            if not entry_price or entry_price <= 0:
                continue

            try:
                analysis_date = datetime.fromisoformat(analysis_date_str)
            except (ValueError, TypeError):
                continue

            # Fetch historical data covering the outcome period
            from data.market_data import get_history
            df = get_history(symbol, period="3mo")
            if df.empty:
                continue

            for days in OUTCOME_DAYS:
                # Check if already recorded
                existing = conn.execute(
                    "SELECT id FROM analysis_outcomes WHERE analysis_id=? AND days_after=?",
                    (analysis_id, days)
                ).fetchone()
                if existing:
                    continue

                target_date = analysis_date + timedelta(days=int(days * 1.5))  # Approximate trading days
                if target_date > datetime.now():
                    continue

                # Find the closest price to target date
                target_str = target_date.strftime("%Y-%m-%d")
                future_prices = df[df.index >= target_str]
                if future_prices.empty:
                    continue

                actual_price = future_prices["Close"].iloc[0]
                actual_return = (actual_price - entry_price) / entry_price

                # Determine if signal was correct
                bullish = action in ("STRONG_BUY", "BUY")
                bearish = action in ("STRONG_SELL", "SELL")
                correct = 0
                if bullish and actual_return > 0:
                    correct = 1
                elif bearish and actual_return < 0:
                    correct = 1
                elif not bullish and not bearish:
                    correct = 1 if abs(actual_return) < 0.03 else 0

                conn.execute(
                    """INSERT INTO analysis_outcomes
                       (analysis_id, days_after, actual_price, actual_return_pct, signal_correct)
                       VALUES (?, ?, ?, ?, ?)""",
                    (analysis_id, days, actual_price, actual_return, correct),
                )
                filled += 1

        conn.commit()
        conn.close()
        return filled
    except Exception as e:
        logger.error(f"Failed to check outcomes: {e}")
        return 0


def compute_engine_accuracy(lookback_days: int = 90, db_path: str = None) -> Dict[str, Dict]:
    """Compute rolling accuracy for each engine.

    Groups by regime. Returns dict like:
    {"momentum": {"accuracy": 0.62, "total": 45, "correct": 28, "avg_ret_correct": 0.03, "avg_ret_wrong": -0.02}}
    """
    try:
        conn = _get_db(db_path)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        results = {}
        engine_names = ["momentum", "fundamental", "technical", "sector", "mean_reversion"]

        for eng in engine_names:
            rows = conn.execute(
                """SELECT es.signal, es.numeric_signal, ao.actual_return_pct, ao.signal_correct,
                          ah.regime
                   FROM engine_signals es
                   JOIN analysis_history ah ON es.analysis_id = ah.id
                   JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
                   WHERE es.engine_name = ?
                   AND ah.analysis_date >= ?
                   AND es.signal != 'NO_DATA'""",
                (eng, cutoff)
            ).fetchall()

            if not rows:
                results[eng] = {"accuracy": 0.5, "total": 0, "correct": 0}
                continue

            total = len(rows)
            correct = sum(1 for r in rows if r["signal_correct"])
            accuracy = correct / total if total > 0 else 0.5

            correct_returns = [r["actual_return_pct"] for r in rows if r["signal_correct"] and r["actual_return_pct"] is not None]
            wrong_returns = [r["actual_return_pct"] for r in rows if not r["signal_correct"] and r["actual_return_pct"] is not None]

            results[eng] = {
                "accuracy": round(accuracy, 3),
                "total": total,
                "correct": correct,
                "avg_ret_correct": round(sum(correct_returns) / len(correct_returns), 4) if correct_returns else 0,
                "avg_ret_wrong": round(sum(wrong_returns) / len(wrong_returns), 4) if wrong_returns else 0,
            }

            # Save to engine_accuracy table
            conn.execute(
                """INSERT INTO engine_accuracy
                   (engine_name, window_start, window_end, total_signals, correct_signals,
                    accuracy, avg_return_when_correct, avg_return_when_wrong, regime)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eng, cutoff, datetime.now().isoformat(), total, correct,
                 results[eng]["accuracy"],
                 results[eng]["avg_ret_correct"], results[eng]["avg_ret_wrong"], "ALL"),
            )

        conn.commit()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Failed to compute engine accuracy: {e}")
        return {}


def get_adaptive_weights(regime: str = "UNKNOWN", db_path: str = None) -> Optional[Dict[str, float]]:
    """Get weights adjusted by engine performance.

    1. Get accuracy for each engine (last 90 days)
    2. If < MIN_SAMPLES_FOR_ADAPTIVE samples, return None (use defaults)
    3. Weight = base_weight * (accuracy / 0.5) — above 50% boosted, below reduced
    4. Normalize to sum to 1.0
    """
    try:
        accuracy_data = compute_engine_accuracy(lookback_days=90, db_path=db_path)

        if not accuracy_data:
            return None

        # Check if we have enough samples
        total_samples = sum(d.get("total", 0) for d in accuracy_data.values())
        if total_samples < MIN_SAMPLES_FOR_ADAPTIVE:
            logger.info(f"Adaptive weights: only {total_samples} samples, need {MIN_SAMPLES_FOR_ADAPTIVE}")
            return None

        adaptive = {}
        for eng, base_w in DEFAULT_WEIGHTS.items():
            acc = accuracy_data.get(eng, {}).get("accuracy", 0.5)
            samples = accuracy_data.get(eng, {}).get("total", 0)

            if samples < 10:
                # Not enough data for this engine, use default
                adaptive[eng] = base_w
            else:
                # Scale weight by accuracy relative to 50% baseline
                multiplier = acc / 0.5
                # Clamp multiplier to [0.3, 2.0] to prevent extreme weights
                multiplier = max(0.3, min(2.0, multiplier))
                adaptive[eng] = base_w * multiplier

        # Normalize to sum to 1.0
        total = sum(adaptive.values())
        if total > 0:
            adaptive = {k: round(v / total, 4) for k, v in adaptive.items()}

        return adaptive

    except Exception as e:
        logger.error(f"Failed to get adaptive weights: {e}")
        return None


def get_engine_performance_summary(db_path: str = None) -> List[Dict]:
    """Get latest engine accuracy data for display."""
    try:
        conn = _get_db(db_path)
        rows = conn.execute(
            """SELECT engine_name, accuracy, total_signals, correct_signals,
                      avg_return_when_correct, avg_return_when_wrong, window_end
               FROM engine_accuracy
               WHERE regime = 'ALL'
               ORDER BY window_end DESC
               LIMIT 5"""
        ).fetchall()
        conn.close()

        return [dict(r) for r in rows]
    except Exception:
        return []


def get_analysis_history(symbol: str = None, limit: int = 50, db_path: str = None) -> List[Dict]:
    """Get recent analysis history, optionally filtered by symbol."""
    try:
        conn = _get_db(db_path)
        if symbol:
            rows = conn.execute(
                """SELECT ah.*, ao.actual_return_pct, ao.signal_correct
                   FROM analysis_history ah
                   LEFT JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
                   WHERE ah.symbol = ?
                   ORDER BY ah.analysis_date DESC LIMIT ?""",
                (symbol, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT ah.*, ao.actual_return_pct, ao.signal_correct
                   FROM analysis_history ah
                   LEFT JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
                   ORDER BY ah.analysis_date DESC LIMIT ?""",
                (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
