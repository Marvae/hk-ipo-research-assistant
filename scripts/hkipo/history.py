"""Historical IPO data from AAStocks.

Data source: http://www.aastocks.com/tc/stocks/market/ipo/listedipo.aspx
"""

import re
import sys
import time
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _get_with_retry(url: str, max_retries: int = 3) -> str:
    """GET with retry on connection errors."""
    for attempt in range(max_retries):
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
            return resp.text
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout) as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise e
    return ""


def fetch_history(limit: int = 50) -> dict:
    """Fetch historical IPO data from AAStocks.

    Args:
        limit: Max number of results

    Returns: {"ipos": [{"code", "name", "listing_date", "offer_price",
              "listing_price", "first_day_change_pct", "oversubscription",
              "win_rate_pct"}]}
    """
    url = "http://www.aastocks.com/tc/stocks/market/ipo/listedipo.aspx"
    try:
        html = _get_with_retry(url)

        # Find the tbody section of ns2 dataTable
        tbody_match = re.search(
            r'<table[^>]*class="ns2 dataTable"[^>]*>.*?<tbody>(.*?)</tbody>',
            html, re.DOTALL
        )
        if not tbody_match:
            return {"ipos": []}

        tbody = tbody_match.group(1)
        
        # Match all rows (no class attribute on tr)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody, re.DOTALL)

        ipos = []
        clean = lambda x: re.sub(r"<[^>]+>", "", x).strip()

        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) < 12:
                continue

            # cells[1]: name + code
            name_match = re.search(r">([^<]+)</a>", cells[1])
            code_match = re.search(r"(\d{5})\.HK", cells[1])
            if not name_match or not code_match:
                continue

            # cells[2]: listing date
            # cells[5]: offer price
            # cells[6]: listing price
            # cells[7]: oversubscription (倍數)
            # cells[9]: win rate (中籤率)
            # cells[11]: first day change %

            oversub_str = clean(cells[7])
            oversub_val = None
            m = re.search(r"([0-9,.]+)", oversub_str.replace(",", ""))
            if m:
                oversub_val = float(m.group(1))

            win_rate_str = clean(cells[9])
            win_rate_val = None
            m = re.search(r"([0-9.]+)%?", win_rate_str)
            if m:
                win_rate_val = float(m.group(1))

            change_str = clean(cells[11])
            change_val = None
            m = re.search(r"([+-]?[0-9.]+)%", change_str)
            if m:
                change_val = float(m.group(1))

            entry = {
                "code": code_match.group(1),
                "name": name_match.group(1).strip(),
                "listing_date": clean(cells[2]).replace("/", "-"),
                "offer_price": clean(cells[5]),
                "listing_price": clean(cells[6]),
                "oversubscription": oversub_val,
                "win_rate_pct": win_rate_val,
                "first_day_change_pct": change_val,
            }

            ipos.append(entry)

        return {"ipos": ipos[:limit]}
    except Exception as e:
        print(f"Fetch history failed: {e}", file=sys.stderr)
        return {"ipos": []}
