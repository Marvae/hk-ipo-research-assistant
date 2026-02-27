"""AAStocks data fetching for HK IPO information.

Data source: http://www.aastocks.com/tc/stocks/market/ipo/upcomingipo
If this script fails, the agent can visit the URL directly.

Returns pure data dicts/lists, no scoring or judgment.
"""

import re
import sys
import time
import httpx

from .ah import search_a_share_code

CNY_HKD_RATE = 1.12

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
BASE_URL = "http://www.aastocks.com/tc/stocks/market/ipo/upcomingipo"


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


def fetch_upcoming_ipos() -> list[dict]:
    """Fetch currently subscribing IPOs from AAStocks.

    Returns list of dicts with keys:
        code, name, price_range, lot_size, entry_fee, deadline, listing_date, is_ah_stock
    """
    url = f"{BASE_URL}.aspx"
    try:
        html = _get_with_retry(url)

        table_match = re.search(
            r'<table[^>]*id="tblGMUpcoming"[^>]*>(.*?)</table>', html, re.DOTALL
        )
        if not table_match:
            return []

        ipos = []
        rows = re.findall(
            r'<tr[^>]*>\s*<td class="txt_l">(.*?)</tr>',
            table_match.group(1),
            re.DOTALL,
        )

        clean = lambda x: re.sub(r"<[^>]+>", " ", x).strip()
        clean_num = lambda x: re.sub(r"[^\d.]", "", clean(x))

        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) < 8:
                continue

            name_match = re.search(r">([^<]+)</a>", cells[0])
            code_match = re.search(r"(\d{5})\.HK", cells[0])
            if not name_match or not code_match:
                continue

            lot_size_str = clean_num(cells[3])
            entry_fee_str = clean_num(cells[4])
            name = name_match.group(1).strip()

            # Check if it's an A+H stock during list fetch
            a_code = search_a_share_code(name)

            ipos.append(
                {
                    "code": code_match.group(1),
                    "name": name,
                    "price_range": clean(cells[2]).replace("N/A", ""),
                    "lot_size": int(lot_size_str) if lot_size_str else 0,
                    "entry_fee": float(entry_fee_str) if entry_fee_str else 0,
                    "deadline": clean(cells[5]).replace("/", "-"),
                    "listing_date": clean(cells[7]).replace("/", "-"),
                    "is_ah_stock": a_code is not None,
                    "a_share_code": a_code,
                }
            )

        return ipos
    except Exception as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return []


def fetch_ipo_detail(code: str) -> dict:
    """Fetch detailed IPO information from AAStocks.

    Returns a dict with all available fields (code, name, industry, sponsors,
    lot_size, offer_price, market_cap, listing_date, deadline,
    cornerstone_investors, has_greenshoe, fund_usage, clawback, is_ah_stock, etc.)
    """
    detail = {
        "code": code,
        "name": "",
        "industry": "",
        "sponsors": [],
        "underwriters": [],
        "global_coordinators": [],
        "lot_size": 0,
        "offer_price": "",
        "market_cap": "",
        "listing_date": "",
        "deadline": "",
        "total_shares": "",
        "public_shares": "",
        "public_ratio": "",
        "intl_shares": "",
        "intl_ratio": "",
        "fund_usage": [],
        "clawback": [],
        "cornerstone_investors": [],
        "cornerstone_total": "",
        "has_greenshoe": False,
        "company_intro": "",
        "is_ah_stock": False,
        "a_share_code": None,
        "pricing_mechanism": None,  # "A" (有回拨) or "B" (无回拨)
    }

    try:
        # Company profile page
        html = _get_with_retry(f"{BASE_URL}/company-profile?symbol={code}")

        # Company introduction
        m = re.search(r'<div class="summary[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            intro = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            detail["company_intro"] = intro[:200] + "..." if len(intro) > 200 else intro

        # Cornerstone investors
        investor_rows = re.findall(
            r'<td class="col1 txt_l">([^<]+)</td>\s*<td class="col2 txt_l">([^<]+)</td>\s*<td class="col3 txt_r">([^<]+)</td>',
            html,
        )
        if investor_rows:
            for name, inv_type, amount in investor_rows:
                if name.strip() == "名稱":
                    continue
                detail["cornerstone_investors"].append(
                    {
                        "name": name.strip(),
                        "type": inv_type.strip(),
                        "amount": amount.strip(),
                    }
                )

        # Industry
        m = re.search(r'>行業</td>\s*<td[^>]*class="txt_r"[^>]*>([^<]+)', html)
        if m:
            detail["industry"] = m.group(1).strip()

        # Listing date
        m = re.search(r">上市日期</td>\s*<td[^>]*>([^<]+)", html)
        if m:
            detail["listing_date"] = m.group(1).strip()

        # IPO info page
        html2 = _get_with_retry(f"{BASE_URL}/ipo-info?symbol={code}")

        # Name
        m = re.search(r'<div class="title">([^<(]+)', html2)
        if m:
            detail["name"] = m.group(1).strip()

        # Check A+H status after getting name
        if detail["name"]:
            a_code = search_a_share_code(detail["name"])
            detail["is_ah_stock"] = a_code is not None
            detail["a_share_code"] = a_code

        # Lot size
        m = re.search(
            r'>每手股數</td>\s*<td[^>]*class="font-num[^"]*"[^>]*>(\d+)', html2
        )
        if m:
            detail["lot_size"] = int(m.group(1))

        # Offer price
        m = re.search(
            r'>招股價</td>\s*<td[^>]*class="font-num[^"]*"[^>]*>([^<]+)', html2
        )
        if m:
            detail["offer_price"] = m.group(1).strip()

        # Market cap
        m = re.search(
            r'>市值</td>\s*<td[^>]*class="font-num[^"]*"[^>]*>([^<]+)', html2
        )
        if m:
            detail["market_cap"] = m.group(1).strip()

        # Deadline
        m = re.search(r">截止日期</td>\s*<td[^>]*>([^<]+)", html2)
        if m:
            detail["deadline"] = m.group(1).strip()

        # Total shares
        m = re.search(r">全球發售股數[^<]*</td>\s*<td[^>]*>([0-9,]+)", html2)
        if m:
            detail["total_shares"] = m.group(1).strip()

        # Public shares - format: 香港/公開發售股數<sup>2</sup></td> <td class="font-num cls">2034000(10.00%)
        m = re.search(
            r">香港/公開發售股數<sup>\d+</sup></td>\s*<td[^>]*>([0-9,]+)\(([0-9.]+)%\)",
            html2,
        )
        if m:
            detail["public_shares"] = m.group(1).strip()
            detail["public_ratio"] = m.group(2).strip()

        # International shares - format: 國際配售股數<sup>2</sup></td> <td...>18302000(90.00%)
        m = re.search(
            r">國際配售股數<sup>\d+</sup></td>\s*<td[^>]*>([0-9,]+)\(([0-9.]+)%\)", html2
        )
        if m:
            detail["intl_shares"] = m.group(1).strip()
            detail["intl_ratio"] = m.group(2).strip()

        # Greenshoe
        detail["has_greenshoe"] = "超額配股權" in html2 or "穩定價格" in html2

        # Sponsors
        m = re.search(r">保薦人</td>\s*<td>(.+?)</tr>", html2, re.DOTALL)
        if m:
            sponsors = re.findall(r"sponsor[^>]*>([^<]+)</a>", m.group(1))
            detail["sponsors"] = [s.strip() for s in sponsors if s.strip()]

        # Global coordinators
        m = re.search(r">全球協調人</td>\s*<td>(.+?)</tr>", html2, re.DOTALL)
        if m:
            coords = re.sub(r"<[^>]+>", "\n", m.group(1)).strip().split("\n")
            detail["global_coordinators"] = [c.strip() for c in coords if c.strip()]

        # Fund usage
        fund_items = re.findall(r"y:(\d+),\s*name:'([^']+)'", html2)
        if fund_items:
            detail["fund_usage"] = [
                {"purpose": n, "ratio": int(r)} for r, n in fund_items
            ]

        # Clawback - extract from table
        clawback_section = re.search(r'回撥比例.*?</table>', html2, re.DOTALL)
        if clawback_section:
            # Match rows like: <td class="font-num cls">15≤X<50倍</td> <td class="font-num cls">15</td>
            clawback_rows = re.findall(
                r'<td[^>]*>([^<]*[≤<X][^<]*)</td>\s*<td[^>]*>(\d+)</td>',
                clawback_section.group(0)
            )
            for condition, ratio in clawback_rows:
                if ratio != "0":  # Only include non-zero clawback
                    detail["clawback"].append({
                        "condition": condition.strip(),
                        "ratio": int(ratio)
                    })
        
        # Determine pricing mechanism (A or B) based on clawback presence
        # 机制 B = 无回拨；机制 A = 有回拨
        if detail["clawback"]:
            detail["pricing_mechanism"] = "A"  # 有回拨
        else:
            # Check if public ratio is set (机制 B sets fixed ratio, no clawback)
            if detail.get("public_ratio"):
                detail["pricing_mechanism"] = "B"  # 无回拨，固定比例
            else:
                detail["pricing_mechanism"] = None

        return detail
    except Exception as e:
        print(f"Fetch detail failed: {e}", file=sys.stderr)
        return detail
