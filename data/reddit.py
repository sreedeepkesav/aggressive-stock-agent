"""Reddit sentiment via public JSON API (no auth, no PRAW needed)."""

import logging
import re
from collections import defaultdict
from typing import Dict, List

import requests

logger = logging.getLogger("stock_agent")

_HEADERS = {"User-Agent": "StockAgent/2.0"}

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options", "StockMarket"]

# Match $TICKER or standalone 1-5 letter uppercase tickers
_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b|(?<!\w)([A-Z]{2,5})(?!\w)")
# Common false positives
_NOISE = {"I", "A", "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS",
          "ONE", "OUR", "OUT", "DD", "CEO", "IPO", "ETF", "YOLO", "IMO", "FOMO", "TIL", "OP",
          "USA", "PM", "AM", "EST", "PST", "GDP", "CPI", "SEC", "FDA", "AI", "EPS", "PE", "ATH",
          "DCA", "LOL", "EDIT", "JUST", "LIKE", "THIS", "THAT", "WHAT", "WHEN", "WITH"}


def _extract_tickers(text: str) -> List[str]:
    """Extract plausible tickers from text, filtering noise."""
    matches = _TICKER_RE.findall(text)
    tickers = set()
    for dollar, bare in matches:
        t = dollar or bare
        if t and t not in _NOISE:
            tickers.add(t)
    return list(tickers)


def get_subreddit_posts(subreddit: str, limit: int = 25) -> List[Dict]:
    """Fetch top posts from a subreddit using public JSON API."""
    try:
        resp = requests.get(
            f"https://www.reddit.com/r/{subreddit}/hot.json",
            params={"limit": limit},
            headers=_HEADERS,
            timeout=10,
        )
        if not resp.ok:
            logger.warning(f"Reddit fetch failed for r/{subreddit}: {resp.status_code}")
            return []

        posts = []
        for child in resp.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title": d.get("title", ""),
                "selftext": d.get("selftext", "")[:500],
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "subreddit": subreddit,
                "url": d.get("url", ""),
                "created_utc": d.get("created_utc", 0),
            })
        return posts
    except Exception as e:
        logger.warning(f"Reddit error for r/{subreddit}: {e}")
        return []


def get_ticker_mentions(subreddits: List[str] = None, limit: int = 25) -> Dict[str, Dict]:
    """Scan subreddits and return aggregated ticker mention counts + sentiment proxy."""
    subreddits = subreddits or SUBREDDITS
    mentions: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "score_sum": 0, "subreddits": set(), "posts": []})

    for sub in subreddits:
        for post in get_subreddit_posts(sub, limit=limit):
            text = post["title"] + " " + post["selftext"]
            for ticker in _extract_tickers(text):
                m = mentions[ticker]
                m["count"] += 1
                m["score_sum"] += post["score"]
                m["subreddits"].add(sub)
                if len(m["posts"]) < 3:
                    m["posts"].append(post["title"][:100])

    # Convert sets to lists for serialization
    result = {}
    for ticker, data in mentions.items():
        if data["count"] >= 2:  # Filter noise: require at least 2 mentions
            result[ticker] = {
                "count": data["count"],
                "avg_score": data["score_sum"] / data["count"],
                "subreddits": list(data["subreddits"]),
                "sample_posts": data["posts"],
            }

    return dict(sorted(result.items(), key=lambda x: x[1]["count"], reverse=True))
