"""yfinance wrapper with TTL caching, Alpha Vantage fallback, and canonical indicator calculation.

Data source priority:
    1. TTL cache (in-memory, configurable TTL)
    2. yfinance (primary source)
    3. Alpha Vantage (fallback when yfinance fails, requires ALPHA_VANTAGE_API_KEY)
"""

import logging
import warnings
from typing import Optional

import pandas as pd
import yfinance as yf

from data.cache import get_cache
from data.indicators import add_all_indicators

logger = logging.getLogger("stock_agent")

# Track data source for diagnostics
_last_source: dict = {}  # symbol -> "yfinance" | "alpha_vantage" | "cache"


def get_last_data_source(symbol: str) -> str:
    """Return which source provided the last data for this symbol."""
    return _last_source.get(symbol, "unknown")


def clean_symbol(symbol: str) -> str:
    """Normalize ticker symbol."""
    if not symbol:
        return symbol
    s = symbol.strip().upper()
    # Remove common suffixes yfinance doesn't accept
    for suffix in [" US EQUITY", " EQUITY", " US", ".US"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    # Replace dots with dashes for yfinance (BRK.B -> BRK-B)
    s = s.replace(".", "-")
    return s


def get_ticker(symbol: str) -> yf.Ticker:
    """Return a (possibly cached) yf.Ticker object."""
    cache = get_cache()
    key = f"ticker:{symbol}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    t = yf.Ticker(clean_symbol(symbol))
    cache.set(key, t)
    return t


def _try_alpha_vantage(symbol: str, period: str) -> pd.DataFrame:
    """Attempt to fetch data from Alpha Vantage as fallback.

    Maps yfinance period strings to Alpha Vantage outputsize.
    Returns empty DataFrame if AV is unavailable or fails.
    """
    try:
        from data.alpha_vantage import av_get_daily
    except ImportError:
        return pd.DataFrame()

    # Map period to outputsize: anything > 3mo needs full history
    full_periods = {"1y", "2y", "5y", "10y", "max", "6mo"}
    outputsize = "full" if period in full_periods else "compact"

    df = av_get_daily(symbol, outputsize=outputsize)
    if df.empty:
        return df

    # Trim to approximate period length
    period_days = {
        "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
        "1y": 365, "2y": 730,
    }
    max_days = period_days.get(period, 180)
    if len(df) > max_days:
        df = df.tail(max_days)

    return df


def get_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch price history with caching and Alpha Vantage fallback."""
    cache = get_cache()
    key = f"history:{symbol}:{period}:{interval}"
    cached = cache.get(key)
    if cached is not None:
        _last_source[symbol] = "cache"
        return cached

    # Primary source: yfinance
    df = pd.DataFrame()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ticker = get_ticker(symbol)
            df = ticker.history(period=period, interval=interval)
        if not df.empty:
            _last_source[symbol] = "yfinance"
            cache.set(key, df)
            return df
    except Exception as e:
        logger.warning(f"yfinance failed for {symbol}: {e}")

    # Fallback: Alpha Vantage (daily only)
    if interval == "1d":
        logger.info(f"Trying Alpha Vantage fallback for {symbol}")
        df = _try_alpha_vantage(symbol, period)
        if not df.empty:
            _last_source[symbol] = "alpha_vantage"
            cache.set(key, df)
            return df
        logger.warning(f"Alpha Vantage also failed for {symbol}")

    return pd.DataFrame()


def get_history_with_indicators(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch price history and add all standard technical indicators."""
    cache = get_cache()
    key = f"hist_ind:{symbol}:{period}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    df = get_history(symbol, period=period)
    if df.empty or len(df) < 50:
        return pd.DataFrame()

    df = add_all_indicators(df)
    cache.set(key, df)
    return df


def get_weekly_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch weekly price history for multi-timeframe analysis."""
    cache = get_cache()
    key = f"weekly:{symbol}:{period}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ticker = get_ticker(symbol)
            df = ticker.history(period=period, interval="1wk")
        if not df.empty:
            cache.set(key, df)
        return df
    except Exception as e:
        logger.error(f"Error fetching weekly history for {symbol}: {e}")
        return pd.DataFrame()


def get_info(symbol: str) -> dict:
    """Return ticker.info with caching."""
    cache = get_cache()
    key = f"info:{symbol}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            info = get_ticker(symbol).info or {}
        cache.set(key, info)
        return info
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {e}")
        return {}
