"""Free SEC EDGAR API for insider trading data. No API key required."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("stock_agent")

_HEADERS = {"User-Agent": "StockAgent/2.0 research@example.com", "Accept": "application/json"}
_BASE_URL = "https://efts.sec.gov/LATEST"


def _get_cik(symbol: str) -> Optional[str]:
    """Look up CIK number for a ticker symbol."""
    try:
        resp = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar",
            params={"action": "getcompany", "company": symbol, "type": "4", "dateb": "", "owner": "include",
                     "count": "1", "search_text": "", "output": "atom"},
            headers=_HEADERS, timeout=10,
        )
        if resp.ok and "cik=" in resp.text:
            import re
            match = re.search(r"cik=(\d+)", resp.text)
            if match:
                return match.group(1)
    except Exception as e:
        logger.debug(f"CIK lookup failed for {symbol}: {e}")
    return None


def get_insider_filings(symbol: str, days_back: int = 30) -> List[Dict]:
    """Fetch recent Form 4 (insider trading) filings from EDGAR full-text search."""
    try:
        resp = requests.get(
            f"{_BASE_URL}/search-index",
            params={
                "q": f'"{symbol}"',
                "dateRange": "custom",
                "startdt": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
                "enddt": datetime.now().strftime("%Y-%m-%d"),
                "forms": "4",
            },
            headers=_HEADERS,
            timeout=15,
        )
        if not resp.ok:
            logger.warning(f"EDGAR search failed ({resp.status_code}) for {symbol}")
            return []

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        filings = []
        for hit in hits[:10]:
            source = hit.get("_source", {})
            filings.append({
                "ticker": symbol,
                "form_type": source.get("forms", "4"),
                "filed_date": source.get("file_date", ""),
                "company": source.get("entity_name", ""),
                "source": "sec_edgar_free",
            })
        return filings

    except Exception as e:
        logger.warning(f"EDGAR insider filing fetch failed for {symbol}: {e}")
        return []


def get_company_filings(symbol: str, form_type: str = "10-K", count: int = 5) -> List[Dict]:
    """Fetch recent company filings (10-K, 10-Q, 8-K, etc.)."""
    try:
        resp = requests.get(
            f"{_BASE_URL}/search-index",
            params={
                "q": f'"{symbol}"',
                "forms": form_type,
            },
            headers=_HEADERS,
            timeout=15,
        )
        if not resp.ok:
            return []

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        return [
            {
                "ticker": symbol,
                "form_type": form_type,
                "filed_date": h.get("_source", {}).get("file_date", ""),
                "company": h.get("_source", {}).get("entity_name", ""),
                "source": "sec_edgar_free",
            }
            for h in hits[:count]
        ]
    except Exception as e:
        logger.warning(f"EDGAR filing fetch failed for {symbol}: {e}")
        return []
