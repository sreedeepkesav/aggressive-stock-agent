"""Trailing stops and dynamic exit management.

- ATR-based trailing stops that tighten as profit grows
- Staged profit taking at 2R, 3R, 5R
- Time-based exit for dead money (>20 days, <2% gain)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from data.indicators import calculate_atr
from data.market_data import get_history
from portfolio.models import Position

logger = logging.getLogger("stock_agent")


@dataclass
class ExitSignal:
    """An exit signal for an open position."""
    symbol: str
    position_id: int
    exit_type: str      # "trailing_stop", "profit_take", "time_exit"
    exit_price: float
    exit_pct: float     # % of position to exit (0.33, 0.5, 1.0)
    reason: str
    urgency: str        # "immediate", "end_of_day", "next_session"


def check_exit_signals(positions: List[Position]) -> List[ExitSignal]:
    """Check all open positions for exit signals.

    Returns list of ExitSignal objects for positions that should be partially or fully exited.
    """
    signals = []
    for pos in positions:
        try:
            exits = _evaluate_position(pos)
            signals.extend(exits)
        except Exception as e:
            logger.error(f"Exit check failed for {pos.symbol}: {e}")
    return signals


def _evaluate_position(pos: Position) -> List[ExitSignal]:
    """Evaluate a single position for all exit conditions."""
    exits = []

    if pos.current_price <= 0 or pos.entry_price <= 0:
        return exits

    # Get current ATR
    df = get_history(pos.symbol, period="3mo")
    if df.empty or len(df) < 20:
        return exits

    current_atr = calculate_atr(df).iloc[-1]
    if current_atr is None or current_atr <= 0:
        return exits

    current_price = pos.current_price
    entry_price = pos.entry_price
    risk_per_share = abs(entry_price - pos.stop_loss) if pos.stop_loss > 0 else current_atr * 2.0

    # Avoid division by zero
    if risk_per_share <= 0:
        risk_per_share = current_atr * 2.0
    if risk_per_share <= 0:
        return exits

    # R-multiple: how many R of profit
    profit_per_share = current_price - entry_price
    r_multiple = profit_per_share / risk_per_share

    # 1. Trailing stop
    trailing_exit = _check_trailing_stop(pos, current_price, current_atr, r_multiple)
    if trailing_exit:
        exits.append(trailing_exit)

    # 2. Staged profit taking
    profit_exits = _check_profit_taking(pos, current_price, r_multiple)
    exits.extend(profit_exits)

    # 3. Time-based exit
    time_exit = _check_time_exit(pos, current_price)
    if time_exit:
        exits.append(time_exit)

    return exits


def _check_trailing_stop(pos: Position, current_price: float, atr: float, r_multiple: float) -> Optional[ExitSignal]:
    """Check if trailing stop has been hit.

    Trailing multiplier starts at 2.5 ATR, tightens to 1.5 ATR after 3R profit.
    """
    # Determine trailing multiplier based on profit level
    if r_multiple >= 3.0:
        trail_mult = 1.5
    elif r_multiple >= 2.0:
        trail_mult = 2.0
    else:
        trail_mult = 2.5

    # Calculate trailing stop from high water mark
    # Use the highest close as HWM approximation
    df = get_history(pos.symbol, period="3mo")
    if df.empty:
        return None

    # Get prices since entry
    try:
        entry_dt = datetime.fromisoformat(pos.entry_date) if isinstance(pos.entry_date, str) else pos.entry_date
        since_entry = df[df.index >= entry_dt.strftime("%Y-%m-%d")]
        if since_entry.empty:
            since_entry = df.tail(20)  # Fallback
    except (ValueError, TypeError):
        since_entry = df.tail(20)

    high_water_mark = since_entry["Close"].max()
    trailing_stop = high_water_mark - (atr * trail_mult)

    if current_price < trailing_stop:
        return ExitSignal(
            symbol=pos.symbol,
            position_id=pos.id or 0,
            exit_type="trailing_stop",
            exit_price=current_price,
            exit_pct=1.0,
            reason=f"Trailing stop hit: ${trailing_stop:.2f} (HWM ${high_water_mark:.2f}, {trail_mult:.1f}x ATR)",
            urgency="immediate",
        )

    return None


def _check_profit_taking(pos: Position, current_price: float, r_multiple: float) -> List[ExitSignal]:
    """Staged profit taking at 2R, 3R, 5R levels."""
    exits = []

    # Only trigger if we haven't already taken profit (check by quantity reduction patterns)
    # In practice, partial exits reduce quantity in the position table.
    # Here we just signal what SHOULD happen.

    if r_multiple >= 5.0:
        exits.append(ExitSignal(
            symbol=pos.symbol,
            position_id=pos.id or 0,
            exit_type="profit_take",
            exit_price=current_price,
            exit_pct=1.0,
            reason=f"5R profit target ({r_multiple:.1f}R) - close remaining",
            urgency="end_of_day",
        ))
    elif r_multiple >= 3.0:
        exits.append(ExitSignal(
            symbol=pos.symbol,
            position_id=pos.id or 0,
            exit_type="profit_take",
            exit_price=current_price,
            exit_pct=0.33,
            reason=f"3R profit ({r_multiple:.1f}R) - take 33%, tighten stop",
            urgency="end_of_day",
        ))
    elif r_multiple >= 2.0:
        exits.append(ExitSignal(
            symbol=pos.symbol,
            position_id=pos.id or 0,
            exit_type="profit_take",
            exit_price=current_price,
            exit_pct=0.33,
            reason=f"2R profit ({r_multiple:.1f}R) - take 33%, move stop to breakeven",
            urgency="end_of_day",
        ))

    return exits


def _check_time_exit(pos: Position, current_price: float) -> Optional[ExitSignal]:
    """Exit if position held > 20 trading days with < 2% gain (dead money)."""
    try:
        entry_dt = datetime.fromisoformat(pos.entry_date) if isinstance(pos.entry_date, str) else pos.entry_date
        days_held = (datetime.now() - entry_dt).days

        if days_held < 28:  # ~20 trading days
            return None

        gain_pct = (current_price - pos.entry_price) / pos.entry_price
        if gain_pct < 0.02:
            return ExitSignal(
                symbol=pos.symbol,
                position_id=pos.id or 0,
                exit_type="time_exit",
                exit_price=current_price,
                exit_pct=1.0,
                reason=f"Dead money: {days_held} days held, only {gain_pct:.1%} gain",
                urgency="next_session",
            )
    except (ValueError, TypeError):
        pass

    return None


def calculate_trailing_stop_level(symbol: str, entry_price: float, entry_date: str) -> Optional[float]:
    """Calculate current trailing stop level for display purposes."""
    try:
        df = get_history(symbol, period="3mo")
        if df.empty or len(df) < 20:
            return None

        atr = calculate_atr(df).iloc[-1]
        if atr is None or atr <= 0:
            return None

        current_price = df["Close"].iloc[-1]
        risk_per_share = abs(entry_price - (entry_price - atr * 2.5))
        if risk_per_share <= 0:
            return None

        r_multiple = (current_price - entry_price) / risk_per_share
        trail_mult = 1.5 if r_multiple >= 3 else (2.0 if r_multiple >= 2 else 2.5)

        try:
            entry_dt = datetime.fromisoformat(entry_date) if isinstance(entry_date, str) else entry_date
            since_entry = df[df.index >= entry_dt.strftime("%Y-%m-%d")]
            if since_entry.empty:
                since_entry = df.tail(20)
        except (ValueError, TypeError):
            since_entry = df.tail(20)

        hwm = since_entry["Close"].max()
        return round(hwm - atr * trail_mult, 2)

    except Exception:
        return None
