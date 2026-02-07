"""Earnings calendar awareness - detect upcoming earnings to suppress signals during binary events."""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import yfinance as yf

logger = logging.getLogger("stock_agent")

# Cache to avoid repeated yfinance calls within a session
_earnings_cache: Dict[str, Optional[date]] = {}
_surprise_cache: Dict[str, dict] = {}


def get_next_earnings_date(symbol: str) -> Optional[date]:
    """Get the next earnings date for a symbol.

    Tries yf.Ticker.calendar first, falls back to earnings_dates.
    Returns None if no upcoming date found.
    """
    if symbol in _earnings_cache:
        return _earnings_cache[symbol]

    try:
        ticker = yf.Ticker(symbol)

        # Try calendar first (most reliable for next earnings)
        try:
            cal = ticker.calendar
            if cal is not None:
                # calendar can be a dict or DataFrame depending on yfinance version
                if isinstance(cal, dict):
                    ed = cal.get("Earnings Date")
                    if ed:
                        # Can be a list of dates or a single date
                        dates = ed if isinstance(ed, list) else [ed]
                        for d in dates:
                            parsed = _parse_date(d)
                            if parsed and parsed >= date.today():
                                _earnings_cache[symbol] = parsed
                                return parsed
                else:
                    # DataFrame format
                    if "Earnings Date" in cal.index:
                        ed = cal.loc["Earnings Date"]
                        parsed = _parse_date(ed.iloc[0] if hasattr(ed, 'iloc') else ed)
                        if parsed and parsed >= date.today():
                            _earnings_cache[symbol] = parsed
                            return parsed
        except Exception:
            pass

        # Fallback: earnings_dates (historical + future)
        try:
            ed = ticker.earnings_dates
            if ed is not None and not ed.empty:
                today = date.today()
                for idx in ed.index:
                    parsed = _parse_date(idx)
                    if parsed and parsed >= today:
                        _earnings_cache[symbol] = parsed
                        return parsed
        except Exception:
            pass

    except Exception as e:
        logger.debug(f"Could not get earnings date for {symbol}: {e}")

    _earnings_cache[symbol] = None
    return None


def get_earnings_surprise_history(symbol: str) -> dict:
    """Get earnings surprise statistics from recent quarters.

    Returns dict with avg_surprise_pct, beat_rate, consecutive_beats.
    """
    if symbol in _surprise_cache:
        return _surprise_cache[symbol]

    result = {"avg_surprise_pct": 0.0, "beat_rate": 0.0, "consecutive_beats": 0}

    try:
        ticker = yf.Ticker(symbol)
        ed = ticker.earnings_dates
        if ed is None or ed.empty:
            _surprise_cache[symbol] = result
            return result

        # Look for Surprise(%) column
        surprise_col = None
        for col in ed.columns:
            if "surprise" in col.lower() and "%" in col.lower():
                surprise_col = col
                break
            elif "surprise" in col.lower():
                surprise_col = col
                break

        if surprise_col is None:
            _surprise_cache[symbol] = result
            return result

        # Get past earnings only (with actual surprise data)
        surprises = ed[surprise_col].dropna()
        if surprises.empty:
            _surprise_cache[symbol] = result
            return result

        # Filter to past dates only
        today = date.today()
        past_surprises = []
        for idx, val in surprises.items():
            parsed = _parse_date(idx)
            if parsed and parsed < today:
                try:
                    past_surprises.append(float(val))
                except (ValueError, TypeError):
                    continue

        if not past_surprises:
            _surprise_cache[symbol] = result
            return result

        # Calculate stats (use last 8 quarters max)
        recent = past_surprises[:8]
        beats = [s for s in recent if s > 0]

        result["avg_surprise_pct"] = sum(recent) / len(recent)
        result["beat_rate"] = len(beats) / len(recent) if recent else 0.0

        # Consecutive beats from most recent
        consecutive = 0
        for s in recent:
            if s > 0:
                consecutive += 1
            else:
                break
        result["consecutive_beats"] = consecutive

    except Exception as e:
        logger.debug(f"Could not get earnings surprises for {symbol}: {e}")

    _surprise_cache[symbol] = result
    return result


def days_until_earnings(symbol: str) -> Optional[int]:
    """Calendar days until next earnings. None if unknown."""
    next_date = get_next_earnings_date(symbol)
    if next_date is None:
        return None
    delta = (next_date - date.today()).days
    return max(0, delta)


def is_earnings_blackout(symbol: str, days_before: int = 3, days_after: int = 1) -> bool:
    """True if within the earnings blackout window.

    Default: 3 days before to 1 day after earnings.
    """
    days = days_until_earnings(symbol)
    if days is None:
        return False
    # days_until is >= 0 for future earnings
    # Within blackout if earnings is 0 to days_before days away
    if 0 <= days <= days_before:
        return True
    # Check if we're in the post-earnings window (earnings was recently)
    # This is harder to detect - we'd need the last earnings date
    # For now, only block pre-earnings since post-earnings data updates quickly
    return False


def _parse_date(val) -> Optional[date]:
    """Parse various date formats from yfinance into a date object."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        # pandas Timestamp
        return val.date()
    except AttributeError:
        pass
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
