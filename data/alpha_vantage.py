"""Alpha Vantage fallback data source.

Used when yfinance fails or is rate-limited. Free tier: 25 requests/day (premium: 500/day).

Provides:
    av_get_daily(symbol) -> pd.DataFrame  (OHLCV, same shape as yfinance output)
    av_get_quote(symbol) -> dict           (current quote info)
"""

import logging
import os
from typing import Optional

import pandas as pd
import requests

from data.cache import get_cache

logger = logging.getLogger("stock_agent")

_BASE_URL = "https://www.alphavantage.co/query"


def _get_api_key() -> str:
    """Get Alpha Vantage API key from environment."""
    return os.getenv("ALPHA_VANTAGE_API_KEY", "")


def av_get_daily(symbol: str, outputsize: str = "compact") -> pd.DataFrame:
    """Fetch daily OHLCV data from Alpha Vantage.

    Args:
        symbol: Ticker symbol (e.g., "AAPL")
        outputsize: "compact" (last 100 days) or "full" (20+ years)

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Index is DatetimeIndex (matching yfinance format).
        Empty DataFrame on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.debug("Alpha Vantage API key not set")
        return pd.DataFrame()

    cache = get_cache()
    cache_key = f"av_daily:{symbol}:{outputsize}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": api_key,
            "datatype": "json",
        }
        resp = requests.get(_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "Error Message" in data or "Note" in data:
            msg = data.get("Error Message") or data.get("Note", "Rate limited")
            logger.warning(f"Alpha Vantage error for {symbol}: {msg}")
            return pd.DataFrame()

        ts_key = "Time Series (Daily)"
        if ts_key not in data:
            logger.warning(f"Alpha Vantage: no time series in response for {symbol}")
            return pd.DataFrame()

        ts = data[ts_key]
        rows = []
        for date_str, values in ts.items():
            rows.append({
                "Date": pd.Timestamp(date_str),
                "Open": float(values["1. open"]),
                "High": float(values["2. high"]),
                "Low": float(values["3. low"]),
                "Close": float(values["4. close"]),
                "Volume": int(values["5. volume"]),
            })

        df = pd.DataFrame(rows)
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)

        if not df.empty:
            cache.set(cache_key, df)

        logger.info(f"Alpha Vantage: fetched {len(df)} days for {symbol}")
        return df

    except requests.RequestException as e:
        logger.error(f"Alpha Vantage request failed for {symbol}: {e}")
        return pd.DataFrame()
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Alpha Vantage parse error for {symbol}: {e}")
        return pd.DataFrame()


def av_get_quote(symbol: str) -> dict:
    """Fetch real-time quote from Alpha Vantage.

    Returns dict with keys like: price, volume, change_pct, etc.
    Empty dict on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        return {}

    cache = get_cache()
    cache_key = f"av_quote:{symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": api_key,
        }
        resp = requests.get(_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        quote = data.get("Global Quote", {})
        if not quote:
            return {}

        result = {
            "symbol": quote.get("01. symbol", symbol),
            "price": float(quote.get("05. price", 0)),
            "volume": int(quote.get("06. volume", 0)),
            "previousClose": float(quote.get("08. previous close", 0)),
            "change": float(quote.get("09. change", 0)),
            "changePercent": quote.get("10. change percent", "0%"),
        }

        cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Alpha Vantage quote failed for {symbol}: {e}")
        return {}


def av_search_symbol(keywords: str) -> list:
    """Search for symbols matching keywords.

    Returns list of dicts with: symbol, name, type, region, currency.
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    try:
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
            "apikey": api_key,
        }
        resp = requests.get(_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        matches = data.get("bestMatches", [])
        return [
            {
                "symbol": m.get("1. symbol", ""),
                "name": m.get("2. name", ""),
                "type": m.get("3. type", ""),
                "region": m.get("4. region", ""),
                "currency": m.get("8. currency", ""),
            }
            for m in matches
        ]

    except Exception as e:
        logger.error(f"Alpha Vantage search failed: {e}")
        return []
