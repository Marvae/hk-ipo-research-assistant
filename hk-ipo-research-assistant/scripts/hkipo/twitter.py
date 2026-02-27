"""Twitter sentiment data source for HK IPO stocks.

Uses DuckDuckGo search to find relevant tweets, then FxTwitter API to fetch details.
Returns raw tweet data for the agent to analyze.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Path to web-search script
WEB_SEARCH_SCRIPT = Path.home() / ".openclaw/skills/web-search/web-search/scripts/search.py"


@dataclass
class Tweet:
    """A tweet with engagement metrics."""

    text: str
    author: str
    author_name: str
    likes: int
    retweets: int
    created_at: str
    url: str
    views: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "author": self.author,
            "author_name": self.author_name,
            "likes": self.likes,
            "retweets": self.retweets,
            "created_at": self.created_at,
            "url": self.url,
            "views": self.views,
        }


def _extract_tweet_ids(search_results: list[dict]) -> list[tuple[str, str]]:
    """Extract (username, status_id) pairs from search results.

    Looks for x.com or twitter.com URLs in the format:
    https://x.com/{user}/status/{id}
    https://twitter.com/{user}/status/{id}
    """
    pattern = r"(?:x\.com|twitter\.com)/([^/]+)/status/(\d+)"
    tweet_ids = []

    for result in search_results:
        href = result.get("href", "")
        match = re.search(pattern, href)
        if match:
            username, status_id = match.groups()
            # Skip settings, help, and other non-user pages
            if username not in ("settings", "help", "i", "search", "explore", "home"):
                tweet_ids.append((username, status_id))

    return tweet_ids


def _fetch_tweet_via_fxtwitter(username: str, status_id: str) -> Optional[Tweet]:
    """Fetch tweet details using FxTwitter API.

    FxTwitter is a free API that doesn't require authentication.
    """
    url = f"https://api.fxtwitter.com/{username}/status/{status_id}"

    try:
        result = subprocess.run(
            ["curl", "-sL", url],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        if data.get("code") != 200:
            return None

        tweet = data.get("tweet", {})
        author = tweet.get("author", {})

        return Tweet(
            text=tweet.get("text", ""),
            author=author.get("screen_name", username),
            author_name=author.get("name", ""),
            likes=tweet.get("likes", 0),
            retweets=tweet.get("retweets", 0),
            created_at=tweet.get("created_at", ""),
            url=tweet.get("url", f"https://x.com/{username}/status/{status_id}"),
            views=tweet.get("views"),
        )

    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        return None


def _search_ddg(query: str, max_results: int = 10) -> list[dict]:
    """Search DuckDuckGo and return results."""
    if not WEB_SEARCH_SCRIPT.exists():
        return []

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(WEB_SEARCH_SCRIPT),
                query,
                "--max-results",
                str(max_results),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return []

        # The script outputs non-JSON lines first, find the JSON array
        output = result.stdout
        json_start = output.find("[")
        if json_start == -1:
            return []

        return json.loads(output[json_start:])

    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def search_stock_sentiment(stock_name: str, limit: int = 5) -> list[dict]:
    """Search Twitter/X for sentiment about a HK IPO stock.

    Args:
        stock_name: Name of the stock (Chinese or English)
        limit: Maximum number of tweets to return

    Returns:
        List of tweet dicts with keys:
            text, author, author_name, likes, retweets, created_at, url, views

        Empty list if no tweets found.

    Example:
        >>> tweets = search_stock_sentiment("蜜雪冰城")
        >>> for t in tweets:
        ...     print(f"@{t['author']}: {t['text'][:50]}...")
    """
    # Try multiple search queries for better coverage
    queries = [
        f"{stock_name} 港股打新 site:x.com",
        f"{stock_name} IPO 香港 site:x.com",
        f"{stock_name} 新股 site:twitter.com",
    ]

    seen_ids: set[str] = set()
    tweets: list[Tweet] = []

    for query in queries:
        if len(tweets) >= limit:
            break

        # Search needs more results since many won't be valid tweets
        search_results = _search_ddg(query, max_results=10)
        tweet_ids = _extract_tweet_ids(search_results)

        for username, status_id in tweet_ids:
            if len(tweets) >= limit:
                break

            if status_id in seen_ids:
                continue

            seen_ids.add(status_id)
            tweet = _fetch_tweet_via_fxtwitter(username, status_id)

            if tweet and tweet.text:
                # Basic relevance check - tweet should mention the stock
                # Use lowercase for comparison
                text_lower = tweet.text.lower()
                name_lower = stock_name.lower()

                # Accept if stock name appears OR it's about HK IPO
                if (
                    name_lower in text_lower
                    or "港股" in tweet.text
                    or "打新" in tweet.text
                    or "ipo" in text_lower
                    or "新股" in tweet.text
                ):
                    tweets.append(tweet)

    # Sort by engagement (likes + retweets)
    tweets.sort(key=lambda t: t.likes + t.retweets, reverse=True)

    return [t.to_dict() for t in tweets[:limit]]


def main(argv=None):
    """CLI interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Search Twitter for HK IPO sentiment")
    parser.add_argument("stock_name", help="Stock name to search for")
    parser.add_argument(
        "--limit", "-n", type=int, default=5, help="Max tweets to return"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args(argv)

    tweets = search_stock_sentiment(args.stock_name, limit=args.limit)

    if not tweets:
        print(f"No tweets found for: {args.stock_name}", file=sys.stderr)
        sys.exit(0)

    if args.json:
        print(json.dumps(tweets, ensure_ascii=False, indent=2))
    else:
        for i, t in enumerate(tweets, 1):
            print(f"\n--- Tweet {i} ---")
            print(f"@{t['author']} ({t['author_name']})")
            print(f"Likes: {t['likes']} | Retweets: {t['retweets']} | Views: {t['views']}")
            print(f"Date: {t['created_at']}")
            print(f"URL: {t['url']}")
            print(f"\n{t['text']}")


if __name__ == "__main__":
    main()
