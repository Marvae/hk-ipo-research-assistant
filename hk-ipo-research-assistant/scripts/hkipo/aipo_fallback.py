"""
AiPO 替代数据源（AAStocks + 富途，全部免登录）

背景：AiPO (aipo.myiqdii.com) 自 2026-06 起不可用（见仓库 issue #1）。
本模块用 AAStocks 新股详情页与富途新股列表拼出与 aipo.py 相同形状的数据，
供 aipo.py 的公开函数在 AiPO 失败时回退调用。返回纯 dict/list，dataclass
转换由 aipo.py 完成。

已知差距（无免登录平替）：
- 实时孖展认购总额与逐券商认购明细：AAStocks 只有孖展「供应」（利率/成数），
  不是认购额，不做映射以免误导。配发结果公布后可用超购倍数（tblAllotmentResult）。
- 机构评级（AiPO 聚合）：无替代源，回退为空。
- 基石投资者金额为 AAStocks 披露的认购额（多为美元），持股数/比例按
  发行价上限与总发行股数估算，FX 取近似值（USD/HKD 7.80、CNY/HKD 1.09）。
"""

from __future__ import annotations

import re
import threading
from datetime import date

try:
    from common import USER_AGENT, fetch_text
except ImportError:  # 包模式且本目录不在 sys.path 时
    from .common import USER_AGENT, fetch_text

_FX = {"美元": 7.80, "港元": 1.0, "人民幣": 1.09, "人民币": 1.09, "歐元": 8.40, "英鎊": 9.90}
_UNITS = {"百萬": 1e6, "億": 1e8, "千萬": 1e7, "萬": 1e4}


# =============================================================================
# 进程内缓存
# 同一进程里 analyze 会对同一 code 依次调 brief / margin / cornerstone，
# 它们底层都抓同一张 AAStocks 详情页。memo 后同 key 只真正抓一次；
# per-key 锁保证多线程并发时同 key 也只抓一次（不同 key 互不阻塞）。
# producer 抛异常时不写缓存，后续调用可重试。
# =============================================================================

_cache: dict = {}
_cache_locks: dict = {}
_cache_guard = threading.Lock()


def _memoized(key, producer):
    with _cache_guard:
        if key in _cache:
            return _cache[key]
        lock = _cache_locks.setdefault(key, threading.Lock())
    with lock:
        with _cache_guard:
            if key in _cache:
                return _cache[key]
        value = producer()
        with _cache_guard:
            _cache[key] = value
        return value


def _norm_date(s: str | None) -> str | None:
    """'2026/10/28' / '2026年10月28日' -> '2026-10-28'"""
    if not s:
        return None
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if not m:
        return None
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _parse_price_range(s: str | None) -> tuple[float, float]:
    """'最高 93.8' -> (93.8, 93.8); '10.50 - 12.30' -> (10.5, 12.3); '1.55' -> (1.55, 1.55)"""
    if not s:
        return 0.0, 0.0
    nums = [float(x) for x in re.findall(r"\d+\.?\d*", s.replace(",", ""))]
    if not nums:
        return 0.0, 0.0
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums), max(nums)


def _parse_amount_hkd(s: str | None) -> float:
    """'美元45百萬' -> 45e6 * 7.80; '港元15.7百萬' -> 15.7e6"""
    if not s:
        return 0.0
    m = re.search(r"([\d,.]+)\s*(百萬|千萬|億|萬)?", s)
    if not m:
        return 0.0
    value = float(m.group(1).replace(",", ""))
    value *= _UNITS.get(m.group(2) or "", 1.0)
    for cur, fx in _FX.items():
        if cur in s:
            return value * fx
    return value


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def _detail(code: str) -> dict | None:
    def produce():
        from aastocks import get_ipo_detail
        try:
            return get_ipo_detail(code.zfill(5))
        except Exception:
            return None
    return _memoized(("detail", code.zfill(5)), produce)


def _upcoming_ipos() -> list:
    def produce():
        from aastocks import get_upcoming_ipos
        try:
            return get_upcoming_ipos()
        except Exception:
            return []
    return _memoized(("upcoming",), produce)


def _allotment_rows() -> list:
    def produce():
        from aastocks import get_allotment_results
        try:
            return get_allotment_results()
        except Exception:
            return []
    return _memoized(("allotment",), produce)


def _total_shares(detail: dict) -> float:
    """由香港发售股数与占比反推总发行股数：'11378400(10.00%)' -> 113,784,000"""
    raw = detail.get("public_offer_shares") or ""
    m = re.search(r"([\d,]+)\s*\((\d+(?:\.\d+)?)%\)", raw)
    if not m:
        return 0.0
    pub = float(m.group(1).replace(",", ""))
    pct = float(m.group(2))
    return pub / (pct / 100.0) if pct > 0 else 0.0


def _allotment_for(code: str) -> dict | None:
    rows = _allotment_rows()
    target = code.zfill(5)
    for r in rows:
        if (r.get("symbol") or "").zfill(5) == target:
            return r
    return None


def _company_info(code: str) -> dict:
    return _memoized(("company_info", code.zfill(5)), lambda: _company_info_fetch(code))


def _company_info_fetch(code: str) -> dict:
    """AAStocks 公司資料頁：業務簡介、主席、主要股東（best-effort）"""
    out = {"principal_activities": "", "chairman": "", "substantial_shareholders": ""}
    try:
        from bs4 import BeautifulSoup
        url = f"https://www.aastocks.com/tc/stocks/market/ipo/upcomingipo/company-info?symbol={code.zfill(5)}"
        html = fetch_text(url, headers={"User-Agent": USER_AGENT})
        soup = BeautifulSoup(html, "html.parser")
        for title in soup.find_all("div", class_="title"):
            if title.get_text(strip=True) == "業務簡介":
                el = title
                for _ in range(4):  # 向上找到 comm-panel（标题的祖父级容器含正文）
                    el = el.parent
                    if el is None:
                        break
                    text = el.get_text(" ", strip=True)
                    if len(text) > 60:
                        out["principal_activities"] = text.replace("業務簡介", "", 1).strip()[:400]
                        break
                break
        page_text = soup.get_text(" ", strip=True)
        m = re.search(r"主要股東\s*(.+?)(?:公司董事|公司秘書|核數師|$)", page_text)
        if m:
            out["substantial_shareholders"] = m.group(1).strip()[:200]
        m = re.search(r"([\u4e00-\u9fa5]{2,4})\s*\(主席", page_text)
        if m:
            out["chairman"] = m.group(1)
    except Exception:
        pass
    return out


# =============================================================================
# Brief
# =============================================================================

def fallback_brief(code: str) -> dict | None:
    d = _detail(code)
    if not d:
        return None
    floor, ceiling = _parse_price_range(d.get("offer_price_range"))

    apply_start = apply_end = None
    period = d.get("subscription_period") or ""
    parts = [p.strip() for p in re.split(r"[-~至]", period) if p.strip()]
    if len(parts) >= 2:
        apply_start, apply_end = _norm_date(parts[0]), _norm_date(parts[1])
    elif parts:
        apply_end = _norm_date(parts[0])

    # 入场费：优先用招股列表的官方值，否则按 入场费≈最高价×每手×1.010085 估算
    entry_fee = 0.0
    for ipo in _upcoming_ipos():
        if (ipo.get("symbol") or "").zfill(5) == code.zfill(5):
            entry_fee = float(ipo.get("entry_fee") or 0)
            if not apply_end:
                apply_end = _norm_date(ipo.get("subscription_deadline"))
            break
    if not entry_fee and ceiling and d.get("lot_size"):
        entry_fee = round(ceiling * float(d["lot_size"]) * 1.010085, 2)

    ci = _company_info(code)
    return {
        "code": code.zfill(5),
        "principal_office": "",
        "registrars": "",
        "chairman": ci["chairman"],
        "secretary": "",
        "principal_activities": ci["principal_activities"] or d.get("background", ""),
        "substantial_shareholders": ci["substantial_shareholders"],
        "industry": d.get("industry", ""),
        "sponsors": ", ".join(d.get("sponsors") or []),
        "bookrunners": "",
        "lead_agent": "",
        "coordinator": "",
        "ipo_price_floor": floor,
        "ipo_price_ceiling": ceiling,
        "ipo_pricing": d.get("offer_price_range", ""),
        "apply_start": apply_start,
        "apply_end": apply_end,
        "listing_date": _norm_date(d.get("listing_date")),
        "shares": _total_shares(d),
        "minimum_capital": entry_fee,
        "subscribed_count": 0.0,
        "market_cap": d.get("market_cap_range", ""),
        "pe": 0.0,
        "codes_rate": "",
    }


# =============================================================================
# Cornerstone （AAStocks 机构性投资者表）
# =============================================================================

def fallback_cornerstone(code: str) -> list[dict]:
    d = _detail(code)
    if not d:
        return []
    investors = d.get("institutional_investors") or []
    if not investors:
        return []
    _, ceiling = _parse_price_range(d.get("offer_price_range"))
    total_shares = _total_shares(d)
    listing = _norm_date(d.get("listing_date"))
    release = None
    if listing:
        try:
            y, m, dd = (int(x) for x in listing.split("-"))
            release = _add_months(date(y, m, dd), 6).isoformat()
        except ValueError:
            release = None

    result = []
    for inv in investors:
        amount_hkd = _parse_amount_hkd(inv.get("amount"))
        shares = amount_hkd / ceiling if ceiling else 0.0
        pct = shares / total_shares * 100 if total_shares else 0.0
        result.append({
            "name": inv.get("name", ""),
            "shareholding": round(shares),
            "shareholding_pct": round(pct, 2),
            "release_date": release,
            "profile": inv.get("type", ""),
        })
    return result


# =============================================================================
# Margin（仅配发后：超购倍数；实时认购额无免登录源）
# =============================================================================

def fallback_margin_detail(code: str) -> dict | None:
    row = _allotment_for(code)
    if not row:
        return None
    d = _detail(code)
    total_shares = _total_shares(d) if d else 0.0
    _, ceiling = _parse_price_range(d.get("offer_price_range")) if d else (0.0, 0.0)
    return {
        "code": code.zfill(5),
        "name": row.get("name", ""),
        "apply_start": None,
        "apply_end": None,
        "listing_date": _norm_date(d.get("listing_date")) if d else None,
        "total_margin": 0.0,
        "raise_money": round(total_shares * ceiling / 1e8, 2) if total_shares and ceiling else 0.0,
        "oversubscription_actual": row.get("over_subscription_ratio"),
        "oversubscription_forecast": None,
        "broker_margins": [],
        "update_time": None,
    }


def fallback_margin_list() -> list[dict]:
    ipos = _upcoming_ipos()
    return [{
        "code": ipo.get("symbol", ""),
        "name": ipo.get("name_tc", ""),
        "apply_start": None,
        "apply_end": _norm_date(ipo.get("subscription_deadline")),
        "listing_date": _norm_date(ipo.get("listing_date")),
        "total_margin": 0.0,  # 实时认购额无免登录源，见模块 docstring
        "margin_type": None,
        "interest_rate": 0.0,
    } for ipo in ipos]


# =============================================================================
# Grey market（富途已上市新股的暗盘涨跌幅）
# =============================================================================

def _parse_pct(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", s)
    return float(m.group(1)) if m else None


def fallback_grey_list(page_size: int = 100) -> list[dict]:
    try:
        from futu import fetch_futu_listed_ipos
        ipos = fetch_futu_listed_ipos(limit=max(page_size, 50))
    except Exception:
        return []
    result = []
    for ipo in ipos:
        pct = _parse_pct(ipo.dark_change)
        if pct is None or not ipo.ipo_price:
            continue
        result.append({
            "code": ipo.code,
            "name": ipo.name,
            "ipo_price": ipo.ipo_price,
            "grey_price": round(ipo.ipo_price * (1 + pct / 100), 3),
            "grey_change_pct": pct,
            "grey_volume": 0.0,
            "grey_turnover": 0.0,
            "result_date": None,
            "listing_date": (lambda d: d if d and d >= "2000-01-01" else None)(_norm_date(ipo.listing_date)),
            "issue_number": 0.0,
            "issue_number_hk": 0.0,
            "issue_number_intl": 0.0,
        })
    return result[:page_size]


# =============================================================================
# Allotment（AAStocks 配发结果对比表）
# =============================================================================

def fallback_allotment_results() -> list[dict]:
    rows = _allotment_rows()
    return [{
        "code": r.get("symbol", ""),
        "name": r.get("name", ""),
        "sector": "",
        "industry": "",
        "apply_start": None,
        "apply_end": None,
        "result_date": None,
        "listing_date": None,
        "ipo_price": 0.0,
        "price_range": "",
        "subscribed": r.get("over_subscription_ratio", 0.0),
        "sponsors": "",
        "market_value": 0.0,
        "pe": 0.0,
        "margin_data": 0.0,
        "one_lot_success_rate": r.get("one_lot_success_rate", ""),
        "guaranteed_lots": r.get("guaranteed_lots", ""),
    } for r in rows]


def fallback_today_grey(top: int = 10) -> list[dict]:
    """grey-today 的回退：用最近配发结果（超购倍数 + 一手中签率）拼同形状数据"""
    rows = fallback_allotment_results()
    result = []
    for r in rows[:top]:
        result.append({
            "code": r["code"],
            "name": r["name"],
            "ipo_price": 0.0,
            "subscribed": r.get("subscribed", 0.0),
            "clawback": 0.0,
            "codes_rate": _parse_pct(r.get("one_lot_success_rate")) or 0.0,
            "result_date": None,
        })
    return result
