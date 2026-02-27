#!/usr/bin/env python3
"""hkipo CLI - Hong Kong IPO Data Tool

All commands output pure JSON. No scoring, no judgment, no emoji.

Usage:
    hkipo fetch list
    hkipo fetch detail <code>
    hkipo fetch ah <code>
    hkipo fetch calendar
    hkipo fetch history [--industry X] [--limit N]
"""

import sys
import json
import re
import argparse


def cmd_fetch_list():
    from hkipo.fetcher import fetch_upcoming_ipos
    data = fetch_upcoming_ipos()
    print(json.dumps({"ipos": data}, ensure_ascii=False, indent=2))


def cmd_fetch_detail(code: str):
    from hkipo.fetcher import fetch_ipo_detail
    data = fetch_ipo_detail(code)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_fetch_ah(code: str):
    from hkipo.fetcher import fetch_ipo_detail
    from hkipo.ah import fetch_ah_comparison

    detail = fetch_ipo_detail(code)
    name = detail.get("name", "")
    is_ah = detail.get("is_ah_stock", False)
    a_code = detail.get("a_share_code")
    offer_price = detail.get("offer_price", "")

    # Already know from detail if it's A+H
    if not is_ah:
        print(json.dumps({
            "is_ah_stock": False,
            "code": code,
            "name": name,
            "message": "Not an A+H stock"
        }, ensure_ascii=False, indent=2))
        return

    # Extract H-share price from offer price
    h_price = 0
    if offer_price and offer_price != "N/A":
        m = re.search(r"([0-9.]+)(?:-([0-9.]+))?", offer_price)
        if m:
            h_price = float(m.group(2) or m.group(1))

    if h_price <= 0:
        # A+H stock but offer price not yet determined
        print(json.dumps({
            "is_ah_stock": True,
            "code": code,
            "name": name,
            "a_share_code": a_code,
            "discount_pct": None,
            "message": "A+H stock, but H-share offer price not yet determined"
        }, ensure_ascii=False, indent=2))
        return

    result = fetch_ah_comparison(code, h_price, name)
    if result:
        result["is_ah_stock"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_fetch_calendar():
    from hkipo.calendar import fetch_calendar
    data = fetch_calendar()
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_fetch_history(limit: int):
    from hkipo.history import fetch_history
    data = fetch_history(limit=limit)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="HK IPO Data Tool")
    sub = parser.add_subparsers(dest="cmd")

    fetch_p = sub.add_parser("fetch", help="Fetch IPO data")
    fetch_sub = fetch_p.add_subparsers(dest="subcmd")

    fetch_sub.add_parser("list", help="Current IPO list")

    detail_p = fetch_sub.add_parser("detail", help="IPO detail")
    detail_p.add_argument("code", help="Stock code (e.g., 02715)")

    ah_p = fetch_sub.add_parser("ah", help="A+H comparison")
    ah_p.add_argument("code", help="Stock code (e.g., 02715)")

    fetch_sub.add_parser("calendar", help="Calendar view")

    hist_p = fetch_sub.add_parser("history", help="Historical IPO data")
    hist_p.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    args = parser.parse_args()

    if args.cmd != "fetch" or not args.subcmd:
        parser.print_help()
        sys.exit(0)

    if args.subcmd == "list":
        cmd_fetch_list()
    elif args.subcmd == "detail":
        cmd_fetch_detail(args.code)
    elif args.subcmd == "ah":
        cmd_fetch_ah(args.code)
    elif args.subcmd == "calendar":
        cmd_fetch_calendar()
    elif args.subcmd == "history":
        cmd_fetch_history(args.limit)


if __name__ == "__main__":
    main()
