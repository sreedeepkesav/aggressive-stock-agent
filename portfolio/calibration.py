"""Signal confidence calibration: measures whether reported confidence matches actual outcomes.

When the system says 70% confidence, does the signal actually win 70% of the time?
If not, apply a calibration curve to correct future confidence reports.

Usage:
    from portfolio.calibration import get_calibration_data, apply_calibration

    # Get calibration stats
    data = get_calibration_data()
    # Returns: [{"bucket": "0.5-0.6", "predicted": 0.55, "actual": 0.48, "count": 12}, ...]

    # Apply calibration to a new confidence value
    calibrated = apply_calibration(0.75)
"""

import logging
from typing import Dict, List, Optional, Tuple

from portfolio.state import _get_db

logger = logging.getLogger("stock_agent")

# Confidence buckets for calibration
BUCKETS = [
    (0.0, 0.3, "0-30%"),
    (0.3, 0.5, "30-50%"),
    (0.5, 0.6, "50-60%"),
    (0.6, 0.7, "60-70%"),
    (0.7, 0.8, "70-80%"),
    (0.8, 0.9, "80-90%"),
    (0.9, 1.01, "90-100%"),
]

MIN_SAMPLES_FOR_CALIBRATION = 50


def get_calibration_data(db_path: str = None) -> List[Dict]:
    """Compute calibration curve: for each confidence bucket, what's the actual win rate?

    Returns list of dicts with:
        bucket: str label
        predicted_avg: float (mean confidence in this bucket)
        actual_win_rate: float (fraction of signals that were correct)
        count: int (number of signals in this bucket)
    """
    try:
        conn = _get_db(db_path)
        rows = conn.execute(
            """SELECT ah.confidence, ah.action, ao.actual_return_pct, ao.signal_correct
               FROM analysis_history ah
               JOIN analysis_outcomes ao ON ao.analysis_id = ah.id AND ao.days_after = 5
               WHERE ah.confidence IS NOT NULL
               AND ah.action != 'HOLD'"""
        ).fetchall()
        conn.close()

        if not rows:
            return []

        results = []
        for low, high, label in BUCKETS:
            bucket_rows = [r for r in rows if low <= (r["confidence"] or 0) < high]
            if not bucket_rows:
                continue

            predicted_avg = sum(r["confidence"] for r in bucket_rows) / len(bucket_rows)
            correct_count = sum(1 for r in bucket_rows if r["signal_correct"])
            actual_win_rate = correct_count / len(bucket_rows)

            results.append({
                "bucket": label,
                "predicted_avg": round(predicted_avg, 3),
                "actual_win_rate": round(actual_win_rate, 3),
                "count": len(bucket_rows),
                "correct": correct_count,
            })

        return results

    except Exception as e:
        logger.error(f"Calibration data fetch failed: {e}")
        return []


def get_calibration_curve(db_path: str = None) -> Dict[str, float]:
    """Build a mapping from predicted confidence ranges to calibrated confidence.

    Returns dict like: {"0.5-0.6": 0.48, "0.6-0.7": 0.63, ...}
    Only usable when we have MIN_SAMPLES_FOR_CALIBRATION total outcomes.
    """
    data = get_calibration_data(db_path)
    total_samples = sum(d["count"] for d in data)

    if total_samples < MIN_SAMPLES_FOR_CALIBRATION:
        return {}

    curve = {}
    for d in data:
        if d["count"] >= 5:  # Need at least 5 per bucket
            curve[d["bucket"]] = d["actual_win_rate"]

    return curve


def apply_calibration(raw_confidence: float, db_path: str = None) -> float:
    """Apply calibration curve to adjust a raw confidence value.

    If calibration data is insufficient, returns the raw confidence unchanged.
    """
    curve = get_calibration_curve(db_path)
    if not curve:
        return raw_confidence

    # Find which bucket this confidence falls into
    for low, high, label in BUCKETS:
        if low <= raw_confidence < high:
            if label in curve:
                return curve[label]

    return raw_confidence


def get_calibration_summary(db_path: str = None) -> Dict:
    """Get a summary of calibration health for the dashboard.

    Returns:
        total_outcomes: int
        is_calibrated: bool (enough data?)
        avg_overconfidence: float (positive = overconfident, negative = underconfident)
        worst_bucket: str (most miscalibrated bucket)
    """
    data = get_calibration_data(db_path)
    total = sum(d["count"] for d in data)

    if total < 10:
        return {
            "total_outcomes": total,
            "is_calibrated": False,
            "avg_overconfidence": 0.0,
            "worst_bucket": None,
            "message": f"Need {MIN_SAMPLES_FOR_CALIBRATION} outcomes, have {total}",
        }

    # Calculate average overconfidence
    weighted_diff = 0
    weighted_count = 0
    worst_diff = 0
    worst_bucket = None

    for d in data:
        diff = d["predicted_avg"] - d["actual_win_rate"]
        weighted_diff += diff * d["count"]
        weighted_count += d["count"]

        if abs(diff) > abs(worst_diff):
            worst_diff = diff
            worst_bucket = d["bucket"]

    avg_overconfidence = weighted_diff / weighted_count if weighted_count > 0 else 0

    return {
        "total_outcomes": total,
        "is_calibrated": total >= MIN_SAMPLES_FOR_CALIBRATION,
        "avg_overconfidence": round(avg_overconfidence, 3),
        "worst_bucket": worst_bucket,
        "worst_diff": round(worst_diff, 3) if worst_bucket else 0,
        "buckets": data,
    }
