"""Normalized types shared by the MCP layer, the agent and the API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

SITE_LABELS = {"amazon": "Amazon India", "flipkart": "Flipkart"}
DEFAULT_SITES = ("amazon", "flipkart")


def site_from_label(label: str) -> Optional[str]:
    """Map marketplace labels used by MCP servers to our canonical site keys."""
    if not label:
        return None
    normalized = label.strip().lower()
    if "amazon" in normalized:
        return "amazon"
    if "flipkart" in normalized:
        return "flipkart"
    return normalized or None


@dataclass
class Offer:
    """A single marketplace listing, normalized from any MCP server."""

    site: str
    title: str
    price: Optional[float]
    url: str
    mrp: Optional[float] = None
    discount_pct: Optional[float] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    image_url: str = ""
    seller: str = ""
    in_stock: Optional[bool] = None
    source_server: str = ""
    is_sample: bool = False
    raw: dict = field(default_factory=dict)

    @property
    def dedupe_key(self) -> tuple[str, str]:
        return (self.site, self.url.split("?")[0])

    def compact(self) -> dict[str, Any]:
        """Compact payload for LLM prompts (token budget friendly)."""
        payload: dict[str, Any] = {
            "site": self.site,
            "title": self.title,
            "price": self.price,
            "url": self.url,
        }
        if self.mrp and self.price and self.mrp > self.price:
            payload["mrp"] = self.mrp
        if self.discount_pct:
            payload["discount_pct"] = self.discount_pct
        if self.rating:
            payload["rating"] = self.rating
        if self.is_sample:
            payload["is_sample"] = True
        return payload


@dataclass
class Attempt:
    """Record of one MCP server attempt (drives failover logic and the UI)."""

    server: str
    ok: bool
    count: int = 0
    error: str = ""
    latency_ms: int = 0


@dataclass
class SearchOutcome:
    """Result of one pool search across all MCP servers."""

    query: str
    offers: list[Offer]
    attempts: list[Attempt]
    server: Optional[str] = None  # first server that produced offers
    is_sample: bool = False

    @property
    def any_success(self) -> bool:
        """True when at least one real call completed (even with zero results)."""
        return any(a.ok for a in self.attempts)

    def sites_found(self) -> list[str]:
        return sorted({offer.site for offer in self.offers})
