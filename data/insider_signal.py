"""SEC insider transaction signal: cluster insider buying/selling as alpha indicator.

Uses the free SEC EDGAR full-text search API to find recent Form 4 filings.
Cluster buying by multiple insiders within 30 days = bullish signal.
Cluster selling = informational only (insiders sell for many non-bearish reasons).

Usage:
    from data.insider_signal import get_insider_signal

    signal = get_insider_signal("AAPL")
    # Returns: {"score": 0.3, "reason": "3 insider buys in 30 days", "filings": [...]}
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from data.cache import get_cache

logger = logging.getLogger("stock_agent")

_HEADERS = {
    "User-Agent": "StockAgent/2.0 research@stockagent.local",
    "Accept": "application/json",
}
_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"


def get_insider_filings_detailed(symbol: str, days_back: int = 90) -> List[Dict]:
    """Fetch Form 4 filings with transaction details from EDGAR full-text search.

    Returns list of dicts with: filed_date, filer_name, transaction_type, shares, price_per_share
    """
    cache = get_cache()
    cache_key = f"insider_filings:{symbol}:{days_back}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        resp = requests.get(
            _EFTS_URL,
            params={
                "q": f'"{symbol}"',
                "dateRange": "custom",
                "startdt": start_date,
                "enddt": end_date,
                "forms": "4",
            },
            headers=_HEADERS,
            timeout=15,
        )

        if not resp.ok:
            logger.debug(f"EDGAR search failed ({resp.status_code}) for {symbol}")
            return []

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        filings = []
        for hit in hits[:20]:
            source = hit.get("_source", {})
            filing = {
                "symbol": symbol,
                "filed_date": source.get("file_date", ""),
                "filer_name": source.get("display_names", ["Unknown"])[0] if source.get("display_names") else "Unknown",
                "company": source.get("entity_name", ""),
                "form_type": "4",
            }

            # Try to extract transaction details from the filing text
            # EDGAR full-text sometimes includes transaction codes
            file_desc = source.get("file_description", "")
            if "purchase" in file_desc.lower() or "acquisition" in file_desc.lower():
                filing["transaction_type"] = "BUY"
            elif "sale" in file_desc.lower() or "disposition" in file_desc.lower():
                filing["transaction_type"] = "SELL"
            else:
                filing["transaction_type"] = "UNKNOWN"

            filings.append(filing)

        cache.set(cache_key, filings)
        return filings

    except Exception as e:
        logger.debug(f"Insider filing fetch failed for {symbol}: {e}")
        return []


def get_insider_signal(symbol: str, days_back: int = 90) -> Dict:
    """Analyze insider transactions and return a trading signal.

    Returns:
        score: float (-1.0 to 1.0, positive = bullish insider activity)
        reason: str (human-readable explanation)
        buy_count: int
        sell_count: int
        net_sentiment: str ("BULLISH", "BEARISH", "NEUTRAL")
        filings: list of raw filings
    """
    filings = get_insider_filings_detailed(symbol, days_back)

    if not filings:
        return {
            "score": 0.0,
            "reason": "No recent insider filings found",
            "buy_count": 0,
            "sell_count": 0,
            "net_sentiment": "NEUTRAL",
            "filings": [],
        }

    buy_count = sum(1 for f in filings if f.get("transaction_type") == "BUY")
    sell_count = sum(1 for f in filings if f.get("transaction_type") == "SELL")
    unknown_count = sum(1 for f in filings if f.get("transaction_type") == "UNKNOWN")
    total = len(filings)

    # Count unique filers (cluster buying = multiple insiders)
    unique_buyers = len(set(
        f["filer_name"] for f in filings if f.get("transaction_type") == "BUY"
    ))

    # Recency weighting: filings in last 30 days count more
    recent_cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_buys = sum(
        1 for f in filings
        if f.get("transaction_type") == "BUY" and f.get("filed_date", "") >= recent_cutoff
    )
    recent_sells = sum(
        1 for f in filings
        if f.get("transaction_type") == "SELL" and f.get("filed_date", "") >= recent_cutoff
    )

    # Score calculation
    score = 0.0
    reasons = []

    # Cluster buying: multiple unique insiders buying = strong signal
    if unique_buyers >= 3:
        score += 0.5
        reasons.append(f"{unique_buyers} unique insiders buying")
    elif unique_buyers >= 2:
        score += 0.3
        reasons.append(f"{unique_buyers} insiders buying")
    elif buy_count >= 1:
        score += 0.1
        reasons.append(f"{buy_count} insider buy(s)")

    # Recent activity bonus
    if recent_buys >= 2:
        score += 0.2
        reasons.append(f"{recent_buys} buys in last 30 days")

    # Selling is weaker signal (insiders sell for many reasons)
    if sell_count > buy_count * 3:
        score -= 0.3
        reasons.append(f"Heavy insider selling ({sell_count} sells vs {buy_count} buys)")
    elif sell_count > buy_count * 2:
        score -= 0.15
        reasons.append(f"Moderate insider selling")

    # If mostly unknown transactions, reduce confidence
    if unknown_count > total * 0.7:
        score *= 0.5
        reasons.append("Most transactions unclassified")

    # Clamp score
    score = max(-1.0, min(1.0, score))

    # Net sentiment
    if score > 0.2:
        sentiment = "BULLISH"
    elif score < -0.2:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    return {
        "score": round(score, 3),
        "reason": "; ".join(reasons) if reasons else "Low insider activity",
        "buy_count": buy_count,
        "sell_count": sell_count,
        "unique_buyers": unique_buyers,
        "recent_buys": recent_buys,
        "recent_sells": recent_sells,
        "total_filings": total,
        "net_sentiment": sentiment,
        "filings": filings[:10],  # Return top 10 for display
    }
