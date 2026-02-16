"""Regime change alerting: detect shifts in market regime and notify user.

Tracks regime history in the database and sends alerts when the regime changes.
Supports email (SMTP) and webhook notifications.

Usage:
    from alerts.regime_alerts import check_and_alert_regime_change

    # Returns None if no change, or a dict describing the change
    change = check_and_alert_regime_change()
"""

import logging
import os
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional

from portfolio.state import _get_db

logger = logging.getLogger("stock_agent")


def _ensure_regime_table(db_path: str = None) -> None:
    """Create regime_history table if it doesn't exist."""
    conn = _get_db(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            regime TEXT NOT NULL,
            vix_level REAL,
            breadth_pct REAL,
            spy_trend TEXT,
            credit_stress REAL,
            yield_curve_inverted INTEGER DEFAULT 0,
            vix_term_structure TEXT,
            risk_appetite TEXT,
            confidence_multiplier REAL DEFAULT 1.0,
            block_buys INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def record_regime(regime_info, db_path: str = None) -> Optional[Dict]:
    """Record current regime and return change info if regime has shifted.

    Args:
        regime_info: RegimeInfo dataclass from engines.regime

    Returns:
        None if no change, or dict with {previous, current, timestamp, details}
    """
    _ensure_regime_table(db_path)

    conn = _get_db(db_path)
    current_regime = regime_info.regime.value

    # Get last recorded regime
    last = conn.execute(
        "SELECT regime, timestamp FROM regime_history ORDER BY id DESC LIMIT 1"
    ).fetchone()

    previous_regime = last["regime"] if last else None

    # Record current regime
    conn.execute(
        """INSERT INTO regime_history
           (timestamp, regime, vix_level, breadth_pct, spy_trend,
            credit_stress, yield_curve_inverted, vix_term_structure,
            risk_appetite, confidence_multiplier, block_buys)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now().isoformat(),
            current_regime,
            regime_info.vix_level,
            regime_info.breadth_pct,
            regime_info.spy_trend,
            regime_info.credit_stress,
            1 if regime_info.yield_curve_inverted else 0,
            regime_info.vix_term_structure,
            regime_info.risk_appetite,
            regime_info.confidence_multiplier,
            1 if regime_info.block_buys else 0,
        ),
    )
    conn.commit()
    conn.close()

    # Detect change
    if previous_regime and previous_regime != current_regime:
        change = {
            "previous": previous_regime,
            "current": current_regime,
            "timestamp": datetime.now().isoformat(),
            "vix": regime_info.vix_level,
            "breadth": regime_info.breadth_pct,
            "spy_trend": regime_info.spy_trend,
            "block_buys": regime_info.block_buys,
        }
        logger.warning(
            f"REGIME CHANGE: {previous_regime} -> {current_regime} "
            f"(VIX: {regime_info.vix_level:.1f}, Breadth: {regime_info.breadth_pct:.0%})"
        )
        return change

    return None


def check_and_alert_regime_change(db_path: str = None) -> Optional[Dict]:
    """Detect current regime, compare to last recorded, and send alerts if changed.

    This is the main entry point — call it from the dashboard or a cron job.
    """
    try:
        from engines.regime import detect_regime
        regime_info = detect_regime()
    except Exception as e:
        logger.error(f"Regime detection failed in alerting: {e}")
        return None

    change = record_regime(regime_info, db_path)

    if change:
        _dispatch_alerts(change)

    return change


def _dispatch_alerts(change: Dict) -> None:
    """Send alerts via all configured channels."""
    # Email
    smtp_host = os.getenv("ALERT_SMTP_HOST", "")
    alert_email = os.getenv("ALERT_EMAIL_TO", "")
    if smtp_host and alert_email:
        try:
            _send_email_alert(change, smtp_host, alert_email)
        except Exception as e:
            logger.error(f"Email alert failed: {e}")

    # Webhook (Telegram, Slack, Discord, etc.)
    webhook_url = os.getenv("ALERT_WEBHOOK_URL", "")
    if webhook_url:
        try:
            _send_webhook_alert(change, webhook_url)
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")

    # Always log
    logger.info(
        f"Regime alert dispatched: {change['previous']} -> {change['current']}"
    )


def _send_email_alert(change: Dict, smtp_host: str, to_email: str) -> None:
    """Send regime change alert via email."""
    smtp_port = int(os.getenv("ALERT_SMTP_PORT", "587"))
    smtp_user = os.getenv("ALERT_SMTP_USER", "")
    smtp_pass = os.getenv("ALERT_SMTP_PASS", "")
    from_email = os.getenv("ALERT_EMAIL_FROM", smtp_user)

    subject = f"Market Regime Change: {change['previous']} -> {change['current']}"

    body = f"""Market Regime Change Detected
{'='*50}

Previous Regime: {change['previous']}
Current Regime:  {change['current']}
Timestamp:       {change['timestamp']}

Market Conditions:
  VIX Level:     {change['vix']:.1f}
  Breadth:       {change['breadth']:.0%}
  SPY Trend:     {change['spy_trend']}
  Buy Block:     {'YES - Buys suppressed' if change['block_buys'] else 'No'}

{'='*50}
This is an automated alert from Stock Analysis Agent.
"""

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        if smtp_port == 587:
            server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    logger.info(f"Regime alert email sent to {to_email}")


def _send_webhook_alert(change: Dict, webhook_url: str) -> None:
    """Send regime change alert via webhook (works with Telegram, Slack, Discord)."""
    import requests

    payload = {
        "text": (
            f"*Market Regime Change*\n"
            f"{change['previous']} -> {change['current']}\n"
            f"VIX: {change['vix']:.1f} | Breadth: {change['breadth']:.0%} | "
            f"SPY: {change['spy_trend']}"
        ),
        "regime_change": change,
    }

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    logger.info(f"Regime alert webhook sent to {webhook_url}")


def get_regime_history(limit: int = 50, db_path: str = None) -> List[Dict]:
    """Get recent regime history for display."""
    _ensure_regime_table(db_path)
    try:
        conn = _get_db(db_path)
        rows = conn.execute(
            """SELECT * FROM regime_history
               ORDER BY id DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_regime_changes(limit: int = 20, db_path: str = None) -> List[Dict]:
    """Get only the regime transitions (where regime differs from previous entry)."""
    history = get_regime_history(limit=200, db_path=db_path)
    if not history:
        return []

    changes = []
    for i in range(len(history) - 1):
        if history[i]["regime"] != history[i + 1]["regime"]:
            changes.append({
                "from_regime": history[i + 1]["regime"],
                "to_regime": history[i]["regime"],
                "timestamp": history[i]["timestamp"],
                "vix": history[i]["vix_level"],
                "breadth": history[i]["breadth_pct"],
            })
            if len(changes) >= limit:
                break

    return changes
