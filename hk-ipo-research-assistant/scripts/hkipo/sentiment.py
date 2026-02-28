"""Market sentiment data sources.

Provides market sentiment indicators for HK IPO analysis:
- VHSI (HSI Volatility Index) - market fear gauge
- Sponsor historical performance from AASTOCKS
"""

import json
import sys
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


def get_vhsi() -> dict:
    """Get market sentiment via HSI (Hang Seng Index) data.
    
    Note: VHSI is not available on Yahoo Finance. 
    We use HSI price movement as a proxy for market sentiment.
    
    Returns:
        dict with keys: hsi, change, change_pct, interpretation
        
    Interpretation based on recent movement:
        Strong rally (>2%): Bullish sentiment
        Mild up (0-2%): Neutral-positive
        Flat (-1% to 0%): Neutral
        Decline (<-1%): Risk-off sentiment
        Sharp drop (<-3%): Panic
    """
    if requests is None:
        return {"error": "requests not installed"}
    
    url = "https://query1.finance.yahoo.com/v8/finance/chart/^HSI"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HKIPOResearch/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        result = data["chart"]["result"][0]
        meta = result["meta"]
        
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", 0)
        change = round(price - prev_close, 2)
        change_pct = round((price / prev_close - 1) * 100, 2) if prev_close else 0
        
        return {
            "index": "HSI",
            "price": price,
            "previous_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "day_high": meta.get("regularMarketDayHigh"),
            "day_low": meta.get("regularMarketDayLow"),
            "52w_high": meta.get("fiftyTwoWeekHigh"),
            "52w_low": meta.get("fiftyTwoWeekLow"),
            "interpretation": _interpret_hsi_change(change_pct)
        }
    except Exception as e:
        return {"error": str(e)}


def _interpret_hsi_change(change_pct: float) -> str:
    """Provide interpretation of HSI daily change."""
    if change_pct > 3:
        return "大涨，市场极度乐观"
    elif change_pct > 1:
        return "上涨，市场乐观"
    elif change_pct > 0:
        return "小涨，市场偏乐观"
    elif change_pct > -1:
        return "平稳，市场中性"
    elif change_pct > -3:
        return "下跌，市场谨慎"
    else:
        return "大跌，市场恐慌"


def get_all_sponsors() -> dict:
    """Get all available sponsors from AASTOCKS dropdown.
    
    Returns:
        dict mapping sponsor name to sponsor id
    """
    if requests is None or BeautifulSoup is None:
        return {}
    
    url = "http://www.aastocks.com/sc/stocks/market/ipo/sponsor.aspx"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HKIPOResearch/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        
        soup = BeautifulSoup(resp.text, 'lxml')
        select = soup.find('select', {'id': 'cp_ddlSponsor'})
        if not select:
            return {}
        
        sponsors = {}
        for option in select.find_all('option'):
            value = option.get('value', '')
            name = option.get_text(strip=True)
            if value and name and name != '所有保荐人':
                sponsors[name] = value
        return sponsors
    except Exception:
        return {}


def get_sponsor_detail(sponsor_id: str) -> Optional[dict]:
    """Get detailed stats for a specific sponsor by ID.
    
    Args:
        sponsor_id: The sponsor ID from AASTOCKS
        
    Returns:
        dict with sponsor stats or None
    """
    if requests is None or BeautifulSoup is None:
        return None
    
    url = f"http://www.aastocks.com/sc/stocks/market/ipo/sponsor.aspx?s=1&o=&s2=0&o2=0&f1={sponsor_id}&f2=&page=1"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HKIPOResearch/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # Get IPO list for this sponsor
        table = soup.find('table', {'id': 'tblData'})
        if not table:
            return None
        
        tbody = table.find('tbody')
        if not tbody:
            return None
        
        rows = tbody.find_all('tr')
        ipo_count = len(rows)
        up_count = 0
        down_count = 0
        first_day_returns = []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 6:
                # Column 5 is first day performance
                perf_text = cells[5].get_text(strip=True)
                perf = _parse_pct(perf_text)
                if perf is not None:
                    first_day_returns.append(perf)
                    if perf > 0:
                        up_count += 1
                    elif perf < 0:
                        down_count += 1
        
        avg_first_day = round(sum(first_day_returns) / len(first_day_returns), 2) if first_day_returns else 0
        win_rate = round(up_count / ipo_count * 100, 1) if ipo_count > 0 else 0
        
        return {
            "ipo_count": ipo_count,
            "up_count": up_count,
            "down_count": down_count,
            "avg_first_day": avg_first_day,
            "win_rate": win_rate
        }
    except Exception:
        return None


def get_sponsor_history() -> list[dict]:
    """Get sponsor historical IPO performance from AASTOCKS.
    
    Returns:
        List of dicts with sponsor performance data:
        - name: Sponsor name
        - ipo_count: Number of IPOs
        - up_count: Number that went up on first day
        - down_count: Number that went down
        - avg_first_day: Average first day return %
        - avg_cumulative: Average cumulative return %
        - best_stock: Best performing stock
        - worst_stock: Worst performing stock
    """
    if requests is None or BeautifulSoup is None:
        return [{"error": "requests or beautifulsoup4 not installed"}]
    
    url = "http://www.aastocks.com/sc/stocks/market/ipo/sponsor.aspx"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HKIPOResearch/1.0)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # Find the summary table (tblSummary)
        table = soup.find('table', {'id': 'tblSummary'})
        if not table:
            return [{"error": "Could not find sponsor summary table"}]
        
        sponsors = []
        tbody = table.find('tbody')
        if not tbody:
            return [{"error": "Could not find table body"}]
            
        rows = tbody.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 10:
                try:
                    sponsor = {
                        "name": cells[0].get_text(strip=True),
                        "ipo_count": _parse_int(cells[1].get_text(strip=True)),
                        "up_count": _parse_int(cells[2].get_text(strip=True)),
                        "down_count": _parse_int(cells[3].get_text(strip=True)),
                        "avg_first_day": _parse_pct(cells[4].get_text(strip=True)),
                        "avg_cumulative": _parse_pct(cells[5].get_text(strip=True)),
                        "best_stock": cells[6].get_text(strip=True),
                        "best_return": _parse_pct(cells[7].get_text(strip=True)),
                        "worst_stock": cells[8].get_text(strip=True),
                        "worst_return": _parse_pct(cells[9].get_text(strip=True)),
                    }
                    # Calculate win rate
                    total = sponsor["ipo_count"]
                    if total > 0:
                        sponsor["win_rate"] = round(sponsor["up_count"] / total * 100, 1)
                    else:
                        sponsor["win_rate"] = 0
                    sponsors.append(sponsor)
                except (IndexError, ValueError):
                    continue
        
        return sponsors
    except Exception as e:
        return [{"error": str(e)}]


def _parse_int(s: str) -> int:
    """Parse integer from string, return 0 if failed."""
    try:
        return int(s.replace(',', '').strip())
    except (ValueError, AttributeError):
        return 0


def _parse_pct(s: str) -> Optional[float]:
    """Parse percentage from string like '+12.5%' or '-3.2%'."""
    try:
        s = s.replace('%', '').replace('+', '').strip()
        return float(s)
    except (ValueError, AttributeError):
        return None


def _normalize_sponsor_name(name: str) -> str:
    """Normalize sponsor name for matching (simplified Chinese, remove suffixes)."""
    # Common traditional -> simplified mappings for sponsor names
    t2s = {
        '證': '证', '國': '国', '際': '际', '銀': '银', '華': '华',
        '東': '东', '業': '业', '資': '资', '產': '产', '開': '开',
        '發': '发', '創': '创', '亞': '亚', '萬': '万', '廣': '广',
        '進': '进', '達': '达', '馬': '马', '財': '财', '貿': '贸',
        '實': '实', '電': '电', '訊': '讯', '對': '对', '環': '环',
        '聯': '联', '網': '网', '點': '点', '無': '无', '與': '与',
    }
    result = name
    for t, s in t2s.items():
        result = result.replace(t, s)
    # Remove common suffixes
    for suffix in ['有限公司', '有限责任公司', '股份有限公司']:
        result = result.replace(suffix, '')
    return result.strip().lower()


def search_sponsor(sponsors: list[dict], name: str) -> Optional[dict]:
    """Find a sponsor by name (partial match, handles traditional/simplified Chinese).
    
    First tries to match in the top 10 list, then falls back to full sponsor lookup.
    """
    name_normalized = _normalize_sponsor_name(name)
    
    # Try matching in provided list first (top 10 from summary)
    for s in sponsors:
        sponsor_normalized = _normalize_sponsor_name(s.get("name", ""))
        if name_normalized in sponsor_normalized or sponsor_normalized in name_normalized:
            return s
    
    # Not in top 10? Try full sponsor list from AASTOCKS
    all_sponsors = get_all_sponsors()
    for sponsor_name, sponsor_id in all_sponsors.items():
        sponsor_normalized = _normalize_sponsor_name(sponsor_name)
        if name_normalized in sponsor_normalized or sponsor_normalized in name_normalized:
            # Found! Get detailed stats
            detail = get_sponsor_detail(sponsor_id)
            if detail:
                return {
                    "name": sponsor_name,
                    **detail,
                    "avg_cumulative": None,
                    "best_stock": "N/A",
                    "best_return": None,
                    "worst_stock": "N/A", 
                    "worst_return": None,
                }
    
    return None


def main(argv=None):
    """CLI interface for sentiment data."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Market sentiment data for HK IPO")
    parser.add_argument("command", choices=["vhsi", "sponsor", "sponsor-search"],
                        help="Data to fetch")
    parser.add_argument("--name", "-n", help="Sponsor name to search")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args(argv)
    
    if args.command == "vhsi":
        data = get_vhsi()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            if "error" in data:
                print(f"Error: {data['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"恒生指数 (HSI): {data['price']:.2f}")
            print(f"变动: {data['change']:+.2f} ({data['change_pct']:+.2f}%)")
            print(f"今日区间: {data['day_low']:.2f} - {data['day_high']:.2f}")
            print(f"52周区间: {data['52w_low']:.2f} - {data['52w_high']:.2f}")
            print(f"市场情绪: {data['interpretation']}")
    
    elif args.command == "sponsor":
        sponsors = get_sponsor_history()
        if sponsors and "error" in sponsors[0]:
            print(f"Error: {sponsors[0]['error']}", file=sys.stderr)
            sys.exit(1)
        
        if args.json:
            print(json.dumps(sponsors, ensure_ascii=False, indent=2))
        else:
            print(f"{'保荐人':<20} {'IPO数':>6} {'首日上涨':>8} {'首日下跌':>8} {'胜率':>8} {'平均首日':>10}")
            print("-" * 70)
            for s in sponsors[:20]:  # Top 20
                print(f"{s['name']:<20} {s['ipo_count']:>6} {s['up_count']:>8} {s['down_count']:>8} {s['win_rate']:>7.1f}% {s['avg_first_day'] or 'N/A':>10}")
    
    elif args.command == "sponsor-search":
        if not args.name:
            print("Error: --name required for sponsor-search", file=sys.stderr)
            sys.exit(1)
        
        sponsors = get_sponsor_history()
        if sponsors and "error" in sponsors[0]:
            print(f"Error: {sponsors[0]['error']}", file=sys.stderr)
            sys.exit(1)
        
        result = search_sponsor(sponsors, args.name)
        if result:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"保荐人: {result['name']}")
                print(f"IPO 数量: {result['ipo_count']}")
                print(f"首日上涨: {result['up_count']} ({result['win_rate']:.1f}%)")
                print(f"首日下跌: {result['down_count']}")
                print(f"平均首日表现: {result['avg_first_day']}%")
                print(f"平均累计表现: {result['avg_cumulative']}%")
                print(f"最佳: {result['best_stock']}")
                print(f"最差: {result['worst_stock']}")
        else:
            print(f"未找到保荐人: {args.name}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
