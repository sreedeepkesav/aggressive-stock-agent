"""Performance attribution: identify which engines actually drive alpha.

For each completed trade in the learning system, determines which engines
were bullish/bearish at the time and correlates their signals with outcomes.

This answers the key question: "Which engine actually makes money?"

Usage:
    from portfolio.attribution import get_engine_attribution

    attr = get_engine_attribution()
    # Returns per-engine stats: contribution to wins, contribution to losses,
    # signal accuracy by direction, and overall alpha attribution
"""

import logging
from typing import Dict, List, Optional

import numpy as np

from portfolio.state import _get_db

logger = logging.getLogger("stock_agent")


def get_engine_attribution(lookback_days: int = 90, db_path: str = None) -> Dict[str, Dict]:
    """Compute attribution stats for each engine.

    For each completed analysis with a 5-day outcome, we check what each engine
    signaled and whether the outcome matched. This tells us which engines
    actually contribute to profitable signals.

    Returns dict per engine:
        bullish_count: times engine gave BUY/STRONG_BUY
        bearish_count: times engine gave SELL/STRONG_SELL
        bullish_win_rate: when engine was bullish, how often did price go up?
        bearish_win_rate: when engine was bearish, how often did price go down?
        avg_return_when_bullish: average 5-day return when engine was bullish
        avg_return_when_bearish: average 5-day return when engine was bearish
        contribution_score: overall alpha contribution (higher = more useful)
    """
    try:
        from datetime import datetime, timedelta

        conn = _get_db(db_path)
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        engine_names = ["momentum", "fundamental", "technical", "sector", "mean_reversion"]
        results = {}

        for eng in engine_names:
            rows = conn.execute(
                """SELECT es.signal, es.numeric_signal, es.confidence,
                          ao.actual_return_pct, ao.signal_correct,
                          ah.action as combined_action, ah.regime
                   FROM engine_signals es
                   JOIN analysis_history ah ON es.analysis_id = ah.id
                   JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
                   WHERE es.engine_name = ?
                   AND ah.analysis_date >= ?
                   AND es.signal != 'NO_DATA'""",
                (eng, cutoff)
            ).fetchall()

            if not rows:
                results[eng] = _empty_attribution()
                continue

            bullish = [r for r in rows if r["signal"] in ("BUY", "STRONG_BUY")]
            bearish = [r for r in rows if r["signal"] in ("SELL", "STRONG_SELL")]
            neutral = [r for r in rows if r["signal"] == "HOLD"]

            # Bullish accuracy
            bullish_wins = [r for r in bullish if (r["actual_return_pct"] or 0) > 0]
            bullish_returns = [r["actual_return_pct"] for r in bullish if r["actual_return_pct"] is not None]

            # Bearish accuracy
            bearish_wins = [r for r in bearish if (r["actual_return_pct"] or 0) < 0]
            bearish_returns = [r["actual_return_pct"] for r in bearish if r["actual_return_pct"] is not None]

            # High confidence accuracy (confidence > 0.7)
            high_conf = [r for r in rows if (r["confidence"] or 0) > 0.7]
            high_conf_correct = [r for r in high_conf if r["signal_correct"]]

            # Contribution score: combines accuracy and magnitude
            # A good engine: high bullish win rate + positive avg return when bullish
            bull_wr = len(bullish_wins) / len(bullish) if bullish else 0.5
            bear_wr = len(bearish_wins) / len(bearish) if bearish else 0.5
            avg_bull_ret = np.mean(bullish_returns) if bullish_returns else 0
            avg_bear_ret = np.mean(bearish_returns) if bearish_returns else 0

            # Contribution = weighted combo of accuracy and return magnitude
            contribution = (
                (bull_wr - 0.5) * len(bullish) +  # Excess accuracy * volume (bullish)
                (bear_wr - 0.5) * len(bearish) +   # Excess accuracy * volume (bearish)
                avg_bull_ret * len(bullish) * 10     # Return magnitude when bullish
            )

            results[eng] = {
                "total_signals": len(rows),
                "bullish_count": len(bullish),
                "bearish_count": len(bearish),
                "neutral_count": len(neutral),
                "bullish_win_rate": round(bull_wr, 3),
                "bearish_win_rate": round(bear_wr, 3),
                "avg_return_when_bullish": round(avg_bull_ret, 4) if bullish_returns else None,
                "avg_return_when_bearish": round(avg_bear_ret, 4) if bearish_returns else None,
                "high_conf_accuracy": round(len(high_conf_correct) / len(high_conf), 3) if high_conf else None,
                "high_conf_count": len(high_conf),
                "contribution_score": round(contribution, 2),
            }

        conn.close()
        return results

    except Exception as e:
        logger.error(f"Attribution calculation failed: {e}")
        return {}


def _empty_attribution() -> Dict:
    return {
        "total_signals": 0,
        "bullish_count": 0, "bearish_count": 0, "neutral_count": 0,
        "bullish_win_rate": 0.5, "bearish_win_rate": 0.5,
        "avg_return_when_bullish": None, "avg_return_when_bearish": None,
        "high_conf_accuracy": None, "high_conf_count": 0,
        "contribution_score": 0,
    }


def get_regime_attribution(db_path: str = None) -> Dict[str, Dict]:
    """Break down attribution by market regime.

    Returns dict keyed by regime name, each containing per-engine attribution.
    Answers: "Which engines work in which market conditions?"
    """
    try:
        from datetime import datetime, timedelta

        conn = _get_db(db_path)
        cutoff = (datetime.now() - timedelta(days=180)).isoformat()

        # Get all regimes in data
        regimes = conn.execute(
            """SELECT DISTINCT ah.regime
               FROM analysis_history ah
               WHERE ah.analysis_date >= ? AND ah.regime IS NOT NULL""",
            (cutoff,)
        ).fetchall()

        results = {}
        for regime_row in regimes:
            regime = regime_row["regime"]
            engine_names = ["momentum", "fundamental", "technical", "sector", "mean_reversion"]
            regime_data = {}

            for eng in engine_names:
                rows = conn.execute(
                    """SELECT es.signal, ao.actual_return_pct, ao.signal_correct
                       FROM engine_signals es
                       JOIN analysis_history ah ON es.analysis_id = ah.id
                       JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
                       WHERE es.engine_name = ? AND ah.regime = ?
                       AND ah.analysis_date >= ? AND es.signal != 'NO_DATA'""",
                    (eng, regime, cutoff)
                ).fetchall()

                if not rows:
                    regime_data[eng] = {"accuracy": 0.5, "count": 0}
                    continue

                correct = sum(1 for r in rows if r["signal_correct"])
                regime_data[eng] = {
                    "accuracy": round(correct / len(rows), 3),
                    "count": len(rows),
                }

            results[regime] = regime_data

        conn.close()
        return results

    except Exception as e:
        logger.error(f"Regime attribution failed: {e}")
        return {}


def get_signal_agreement_analysis(db_path: str = None) -> Dict:
    """Analyze whether engine agreement actually predicts better outcomes.

    Compares outcomes when 4-5 engines agree vs when only 2-3 agree.
    """
    try:
        from datetime import datetime, timedelta

        conn = _get_db(db_path)
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()

        rows = conn.execute(
            """SELECT ah.id, ah.agreement_pct, ah.confidence, ah.action,
                      ao.actual_return_pct, ao.signal_correct
               FROM analysis_history ah
               JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
               WHERE ah.analysis_date >= ?
               AND ah.action != 'HOLD'""",
            (cutoff,)
        ).fetchall()

        conn.close()

        if not rows:
            return {"message": "Insufficient data"}

        # Group by agreement level
        high_agreement = [r for r in rows if (r["agreement_pct"] or 0) >= 0.7]
        low_agreement = [r for r in rows if (r["agreement_pct"] or 0) < 0.7]

        high_correct = sum(1 for r in high_agreement if r["signal_correct"])
        low_correct = sum(1 for r in low_agreement if r["signal_correct"])

        high_returns = [r["actual_return_pct"] for r in high_agreement if r["actual_return_pct"] is not None]
        low_returns = [r["actual_return_pct"] for r in low_agreement if r["actual_return_pct"] is not None]

        return {
            "high_agreement": {
                "count": len(high_agreement),
                "win_rate": round(high_correct / len(high_agreement), 3) if high_agreement else 0,
                "avg_return": round(np.mean(high_returns), 4) if high_returns else 0,
            },
            "low_agreement": {
                "count": len(low_agreement),
                "win_rate": round(low_correct / len(low_agreement), 3) if low_agreement else 0,
                "avg_return": round(np.mean(low_returns), 4) if low_returns else 0,
            },
            "agreement_matters": (
                len(high_agreement) >= 5 and len(low_agreement) >= 5 and
                (high_correct / len(high_agreement) if high_agreement else 0) >
                (low_correct / len(low_agreement) if low_agreement else 0)
            ),
        }

    except Exception as e:
        logger.error(f"Agreement analysis failed: {e}")
        return {"message": f"Error: {e}"}
