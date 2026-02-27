"""Calendar view - group IPOs by deadline."""

from itertools import groupby
from .fetcher import fetch_upcoming_ipos


def fetch_calendar() -> dict:
    """Group upcoming IPOs by deadline date.

    Returns: {"rounds": [{"deadline": "...", "ipos": [...]}]}
    """
    ipos = fetch_upcoming_ipos()
    ipos.sort(key=lambda x: x.get("deadline", ""))

    rounds = []
    for deadline, group in groupby(ipos, key=lambda x: x.get("deadline", "")):
        items = list(group)
        rounds.append({
            "deadline": deadline,
            "ipos": [
                {
                    "code": ipo["code"],
                    "name": ipo["name"],
                    "entry_fee": ipo.get("entry_fee", 0),
                    "listing_date": ipo.get("listing_date", ""),
                }
                for ipo in items
            ],
        })

    return {"rounds": rounds}
