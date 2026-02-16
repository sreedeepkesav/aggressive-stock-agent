"""Dynamic sector median P/E calculation with long-lived caching.

Fetches forward P/E from sector ETFs, caches for 7 days, and falls
back to hardcoded values if anything goes wrong.
"""

import logging
import time
from typing import Dict, Optional

from data.cache import get_cache
from data.market_data import get_info

logger = logging.getLogger("stock_agent")

# Sector ETF tickers — each ETF represents its GICS sector
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

# Static fallback — used when fetch fails (same as original hardcoded values)
SECTOR_MEDIAN_PE_FALLBACK: Dict[str, float] = {
    "Technology": 30.0, "Healthcare": 22.0, "Financials": 14.0,
    "Consumer Discretionary": 25.0, "Consumer Staples": 22.0,
    "Energy": 12.0, "Industrials": 20.0, "Materials": 16.0,
    "Utilities": 18.0, "Real Estate": 35.0, "Communication Services": 20.0,
}

# Cache key and TTL (7 days in seconds)
_CACHE_KEY = "sector_median_pe:dynamic"
_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 604800


def get_sector_median_pe(force_refresh: bool = False) -> Dict[str, float]:
    """Get current sector median P/E ratios from ETF data.

    Returns a dict mapping sector name -> forward P/E float.
    Falls back to hardcoded values per-sector if individual fetches fail,
    or entirely if the cache mechanism fails.

    The result is cached for 7 days (stored with timestamp, checked manually
    since TTLCache uses a single global TTL that's too short for this).
    """
    cache = get_cache()

    if not force_refresh:
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            stored_ts, sector_pes = cached
            age_seconds = time.time() - stored_ts
            if age_seconds < _CACHE_TTL_SECONDS:
                return sector_pes
            # Expired — fall through to refresh

    try:
        sector_pes: Dict[str, float] = {}
        fetched_count = 0

        for sector_name, etf_ticker in SECTOR_ETFS.items():
            try:
                info = get_info(etf_ticker)
                pe = info.get("forwardPE") or info.get("trailingPE")

                if pe and isinstance(pe, (int, float)) and pe > 0:
                    sector_pes[sector_name] = round(float(pe), 1)
                    fetched_count += 1
                else:
                    sector_pes[sector_name] = SECTOR_MEDIAN_PE_FALLBACK[sector_name]
                    logger.debug(
                        f"No P/E for {sector_name} ({etf_ticker}), "
                        f"using fallback {sector_pes[sector_name]}"
                    )
            except Exception as e:
                sector_pes[sector_name] = SECTOR_MEDIAN_PE_FALLBACK[sector_name]
                logger.debug(f"Error fetching {sector_name} P/E: {e}")

        # Store with timestamp for manual TTL check
        cache.set(_CACHE_KEY, (time.time(), sector_pes))

        if fetched_count > 0:
            logger.info(
                f"Refreshed sector median P/E: {fetched_count}/{len(SECTOR_ETFS)} "
                f"from live data"
            )
        return sector_pes

    except Exception as e:
        logger.error(f"Sector median refresh failed entirely, using fallback: {e}")
        return dict(SECTOR_MEDIAN_PE_FALLBACK)
