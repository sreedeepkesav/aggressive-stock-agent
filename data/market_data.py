"""yfinance wrapper with TTL caching and canonical indicator calculation."""

import logging
import warnings
from typing import Optional

import pandas as pd
import yfinance as yf

from data.cache import get_cache
from data.indicators import add_all_indicators

logger = logging.getLogger("stock_agent")


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


def get_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch price history with caching."""
    cache = get_cache()
    key = f"history:{symbol}:{period}:{interval}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ticker = get_ticker(symbol)
            df = ticker.history(period=period, interval=interval)
        if not df.empty:
            cache.set(key, df)
        return df
    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
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
