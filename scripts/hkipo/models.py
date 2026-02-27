"""Data structures for HK IPO data."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IPOStock:
    """IPO stock basic information."""
    code: str
    name: str
    price_range: str = ""
    lot_size: int = 0
    entry_fee: float = 0
    deadline: str = ""
    listing_date: str = ""
    industry: str = ""
    sponsors: list[str] = field(default_factory=list)
    cornerstone_investors: list[dict] = field(default_factory=list)
    has_greenshoe: bool = False
