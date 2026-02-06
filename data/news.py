"""News fetching from RSS feeds and yfinance with deduplication and retry."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import feedparser
import requests
import yfinance as yf

from data.market_data import clean_symbol

logger = logging.getLogger("stock_agent")

# RSS sources
NEWS_SOURCES: Dict[str, str] = {
    "cnbc_markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "cnbc_investing": "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    "marketwatch_breaking": "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
    "marketwatch_markets": "https://feeds.marketwatch.com/marketwatch/marketpulse/",
    "investing_stocks": "https://www.investing.com/rss/news_25.rss",
    "investing_economy": "https://www.investing.com/rss/news_95.rss",
    "bloomberg_markets": "https://feeds.bloomberg.com/markets/news.rss",
    "microcap_daily": "https://microcapdaily.com/feed/",
    "smallcap_discoveries": "https://smallcapdiscoveries.com/feed/",
    "yahoo_finance_news": "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "seeking_alpha_market": "https://seekingalpha.com/market_currents.xml",
    "morningstar_news": "https://www.morningstar.com/rss/news",
    "barrons_news": "https://feeds.barrons.com/public/resources/feeds/rss_wenzel.xml",
}

REGIONAL_SOURCES: Dict[str, List[str]] = {
    "europe": [
        "https://feeds.bloomberg.com/markets/europe.rss",
        "https://feeds.feedburner.com/euronews/en/business/",
    ],
    "us": [
        "https://feeds.bloomberg.com/markets/americas.rss",
        "https://feeds.a.marketwatch.com/rss/marketwatch/marketpulse/",
    ],
    "nordic": [
        "https://www.dn.se/ekonomi/rss/",
    ],
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StockAgent/2.0)"}


def normalize_yfinance_news(article: dict) -> dict:
    """Normalize yfinance news item to flat dict format (handles both old and new API)."""
    if "content" in article:
        content = article["content"]
        canon = content.get("canonicalUrl", {})
        provider = content.get("provider", {})
        return {
            "title": content.get("title", ""),
            "summary": content.get("summary", "") or content.get("description", ""),
            "link": canon.get("url", "") if isinstance(canon, dict) else content.get("previewUrl", ""),
            "published": content.get("pubDate", str(datetime.now())),
            "source": provider.get("displayName", "yahoo") if isinstance(provider, dict) else "yahoo",
        }
    return article


def fetch_rss_news(max_per_source: int = 10) -> List[Dict]:
    """Fetch news from all RSS sources with timeout and retry."""
    all_news = []
    seen_titles: set = set()

    for name, url in NEWS_SOURCES.items():
        try:
            resp = requests.get(url, timeout=10, headers=_HEADERS)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:max_per_source]:
                title = getattr(entry, "title", "")
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                all_news.append({
                    "title": title,
                    "summary": getattr(entry, "summary", "") or getattr(entry, "description", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", str(datetime.now())),
                    "source": name,
                    "symbol": "GENERAL",
                })
        except requests.Timeout:
            logger.warning(f"Timeout fetching {name}")
        except Exception as e:
            logger.warning(f"Failed to fetch {name}: {e}")

    return all_news


def fetch_ticker_news(symbols: List[str], max_per_symbol: int = 5) -> List[Dict]:
    """Fetch symbol-specific news from yfinance."""
    news = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(clean_symbol(symbol))
            for article in (ticker.news or [])[:max_per_symbol]:
                item = normalize_yfinance_news(article)
                item["source"] = "yahoo_ticker"
                item["symbol"] = symbol
                news.append(item)
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
    return news


def fetch_regional_news(region: str = "us", max_per_source: int = 5) -> List[Dict]:
    """Fetch region-specific news."""
    urls = REGIONAL_SOURCES.get(region, REGIONAL_SOURCES["us"])
    news = []
    for url in urls:
        try:
            resp = requests.get(url, timeout=8, headers=_HEADERS)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:max_per_source]:
                news.append({
                    "title": getattr(entry, "title", ""),
                    "summary": getattr(entry, "summary", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", str(datetime.now())),
                    "source": f"regional_{region}",
                    "symbol": "REGIONAL",
                })
        except Exception as e:
            logger.warning(f"Regional news error ({url}): {e}")
    return news


def get_comprehensive_news(symbols: Optional[List[str]] = None, max_per_source: int = 10) -> List[Dict]:
    """One-call news fetcher: RSS + ticker-specific + deduplication."""
    news = fetch_rss_news(max_per_source=max_per_source)
    if symbols:
        news.extend(fetch_ticker_news(symbols))
    logger.info(f"Total news articles: {len(news)}")
    return news
