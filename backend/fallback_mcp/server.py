"""Deterministic demo fallback MCP server.

Used as the last resort when every live MCP server fails (site blocked, network
down, offline development). Results are stable for a given query and clearly
flagged with `"is_sample": true` so the UI can badge them as demo data.

Runs as a stdio MCP server:

    python -m fallback_mcp.server
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

from fastmcp import FastMCP

DATA_FILE = Path(__file__).with_name("sample_data.json")
SAMPLES: List[Dict[str, Any]] = json.loads(DATA_FILE.read_text(encoding="utf-8"))

# Slight per-site price differences so comparisons look realistic.
SITE_FACTOR = {"amazon": 1.0, "flipkart": 0.97}
SITE_LABEL = {"amazon": "Amazon India", "flipkart": "Flipkart"}
SEARCH_URL = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
}
MODEL_SUFFIXES = ["", " Pro", " Lite", " Max", " Plus"]

mcp = FastMCP("deal-finder-demo-fallback")


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score(sample: Dict[str, Any], tokens: set[str]) -> int:
    tags = {str(t).lower() for t in sample.get("tags", [])}
    return len(tokens & tags)


def _stable_int(seed: str, low: int, high: int) -> int:
    """Deterministic pseudo-random int in [low, high] from a seed string."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()[:8]
    value = int.from_bytes(digest, "big") % (high - low + 1)
    return low + value


def _listing(sample: Dict[str, Any], query: str, site: str, index: int) -> Dict[str, Any]:
    base = float(sample.get("base_price") or _stable_int(query, 999, 99999))
    jitter = _stable_int(f"{query}|{site}|{index}|jitter", -5, 5) / 100.0
    price = max(99, round(base * SITE_FACTOR.get(site, 1.0) * (1 + jitter)))
    mrp = round(price * 1.18)
    discount = round((mrp - price) / mrp * 100, 1)
    rating_base = float(sample.get("rating") or 4.2)
    rating = round(min(5.0, max(3.0, rating_base + _stable_int(f"{query}|{site}|{index}|r", -20, 10) / 100.0)), 1)
    reviews = int(sample.get("reviews") or _stable_int(f"{query}|{site}|{index}|n", 120, 90000))

    return {
        "platform": SITE_LABEL[site],
        "title": sample.get("title") or f"{query.title()}{MODEL_SUFFIXES[index % len(MODEL_SUFFIXES)]}",
        "price": price,
        "mrp": mrp,
        "discount_percentage": discount,
        "rating": rating,
        "reviews_count": reviews,
        "url": SEARCH_URL[site].format(q=urllib.parse.quote_plus(query)),
        "image_url": "",
        "is_sample": True,
    }


def _synthetic_samples(query: str, limit: int) -> List[Dict[str, Any]]:
    """Build generic sample products when the query matches nothing in the catalogue."""
    return [
        {
            "title": f"{query.title()}{MODEL_SUFFIXES[i % len(MODEL_SUFFIXES)]} (Sample Product {i + 1})",
            "category": "generic",
            "tags": [],
            "base_price": _stable_int(f"{query}|{i}", 799, 89999),
            "rating": 4.0 + (i % 3) * 0.2,
            "reviews": _stable_int(f"{query}|{i}|rev", 50, 40000),
        }
        for i in range(limit)
    ]


@mcp.tool()
def search_products(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Return deterministic sample listings for a query across Amazon India and Flipkart.

    This is the demo fallback used when live marketplace data is unavailable.

    Args:
        query: The product search keywords.
        limit: Maximum listings per marketplace (default 5).

    Returns:
        A list of listing dictionaries flagged with `is_sample: true`.
    """
    tokens = _tokens(query)
    ranked = sorted(SAMPLES, key=lambda s: _score(s, tokens), reverse=True)
    matched = [s for s in ranked if _score(s, tokens) > 0][:limit]
    picks = matched or _synthetic_samples(query, limit)

    results: List[Dict[str, Any]] = []
    for site in ("amazon", "flipkart"):
        for index, sample in enumerate(picks[:limit]):
            results.append(_listing(sample, query, site, index))
    return results


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
