"""Stock universe management: S&P 500 list, momentum/value screening, caching."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import yfinance as yf

from data.market_data import clean_symbol, get_history, get_info

logger = logging.getLogger("stock_agent")

_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "universe_cache.json")

# Static fallback lists
_FALLBACK_SP500 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "UNH", "XOM", "JPM",
    "JNJ", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV", "LLY",
    "COST", "PEP", "KO", "WMT", "TMO", "CSCO", "MCD", "CRM", "ACN", "ABT",
    "DHR", "LIN", "NEE", "AMD", "TXN", "PM", "UPS", "RTX", "LOW", "QCOM",
]

_FALLBACK_MOMENTUM = [
    "NVDA", "AMD", "SMCI", "ARM", "PLTR", "TSLA", "META", "NFLX", "COIN", "HOOD",
]

_FALLBACK_VALUE = [
    "BAC", "JPM", "WFC", "C", "XOM", "CVX", "F", "GM", "CAT", "GE",
]


def _load_cache() -> dict:
    try:
        with open(_CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save universe cache: {e}")


def _cache_age_hours(name: str) -> float:
    """Return hours since cache entry was updated, or inf if missing."""
    cache = _load_cache()
    entry = cache.get(name)
    if not entry or "updated" not in entry:
        return float("inf")
    try:
        updated = datetime.fromisoformat(entry["updated"])
        return (datetime.now() - updated).total_seconds() / 3600
    except Exception:
        return float("inf")


def get_sp500_list(max_symbols: int = 40) -> List[str]:
    """Fetch S&P 500 constituents from Wikipedia, with cache fallback."""
    # Try cache first
    if _cache_age_hours("sp500") < 24:
        cached = _load_cache().get("sp500", {}).get("symbols", [])
        if cached:
            return cached[:max_symbols]

    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        sp500_table = tables[0]

        col = "Symbol" if "Symbol" in sp500_table.columns else "Ticker symbol"
        symbols = []
        for sym in sp500_table[col].tolist():
            if sym and isinstance(sym, str) and len(sym) <= 5:
                clean = sym.replace(".", "-").strip().upper()
                if clean and clean not in ("NAN", "NULL", ""):
                    symbols.append(clean)

        if len(symbols) > 400:
            cache = _load_cache()
            cache["sp500"] = {"symbols": symbols, "updated": datetime.now().isoformat()}
            _save_cache(cache)
            return symbols[:max_symbols]
    except Exception as e:
        logger.warning(f"S&P 500 fetch failed: {e}")

    # Final fallback
    cached = _load_cache().get("sp500", {}).get("symbols", [])
    return (cached or _FALLBACK_SP500)[:max_symbols]


def get_momentum_stocks(max_symbols: int = 30, candidates: List[str] = None) -> List[str]:
    """Screen for momentum stocks: >5% monthly return + volume surge."""
    etfs = {"SPY", "QQQ", "IWM", "DIA", "XLK", "XLV", "XLF", "XLY", "XLP",
            "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC", "VXX"}
    if candidates is None:
        candidates = list(_FALLBACK_SP500)
    candidates = [s for s in candidates if s not in etfs]
    result = []
    for sym in candidates:
        try:
            hist = get_history(sym, period="3mo")
            if hist.empty or len(hist) < 60:
                continue
            ret_1m = (hist["Close"].iloc[-1] / hist["Close"].iloc[-21] - 1) * 100
            vol_ratio = hist["Volume"].tail(5).mean() / hist["Volume"].rolling(20).mean().iloc[-1]
            if ret_1m > 5 and vol_ratio > 1.2:
                result.append(sym)
        except Exception:
            continue

    return (result or _FALLBACK_MOMENTUM)[:max_symbols]


def get_value_stocks(max_symbols: int = 30, candidates: List[str] = None) -> List[str]:
    """Screen for value: P/E < 15, P/B < 2, >10% below 52-week high."""
    etfs = {"SPY", "QQQ", "IWM", "DIA", "XLK", "XLV", "XLF", "XLY", "XLP",
            "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC", "VXX"}
    if candidates is None:
        candidates = list(_FALLBACK_SP500)
    candidates = [s for s in candidates if s not in etfs]
    result = []
    for sym in candidates:
        try:
            info = get_info(sym)
            hist = get_history(sym, period="1y")
            if not info or hist.empty:
                continue
            pe = info.get("trailingPE", 100) or 100
            pb = info.get("priceToBook", 10) or 10
            discount = (hist["High"].max() - hist["Close"].iloc[-1]) / hist["High"].max() * 100
            if pe < 15 and pb < 2 and discount > 10:
                result.append(sym)
        except Exception:
            continue

    return (result or _FALLBACK_VALUE)[:max_symbols]


def update_all_universes(active_symbols: List[str] = None) -> Dict[str, List[str]]:
    """Refresh all stock universes. Uses active_symbols for momentum/value screening."""
    return {
        "sp500": get_sp500_list(),
        "momentum": get_momentum_stocks(candidates=active_symbols),
        "value": get_value_stocks(candidates=active_symbols),
    }
