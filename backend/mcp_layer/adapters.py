"""Adapters that normalize raw MCP tool results into `Offer` objects."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable, Optional

from .types import Offer, site_from_label

logger = logging.getLogger("mcp_layer.adapters")

_LIST_KEYS = (
    "results",
    "products",
    "items",
    "listings",
    "data",
    "amazon_india_results",
    "flipkart_results",
    "best_deals_ranked",
)


def unwrap_result(result: Any) -> Any:
    """Extract Python data from a fastmcp CallToolResult.

    Handles, in order: structured content (result.data), a JSON payload in the
    text content, a JSON array/object embedded in text, and finally raw text.
    """
    data = getattr(result, "data", None)
    if data is not None:
        return data

    content = getattr(result, "content", None) or []
    texts = [getattr(item, "text", "") for item in content if getattr(item, "text", None)]
    joined = "\n".join(text for text in texts if text).strip()
    if not joined:
        return None

    try:
        return json.loads(joined)
    except Exception:  # noqa: BLE001 - fall through to regex extraction
        pass

    for pattern in (r"\[[\s\S]*\]", r"\{[\s\S]*\}"):
        match = re.search(pattern, joined)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:  # noqa: BLE001
                continue

    return joined


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_offer(item: dict, server: str, default_site: Optional[str]) -> Optional[Offer]:
    title = str(item.get("title") or item.get("name") or "").strip()
    url = str(item.get("url") or item.get("link") or "").strip()
    if not title or not url:
        return None

    site = default_site or site_from_label(str(item.get("platform") or item.get("site") or ""))
    if not site:
        return None

    price = _num(item.get("price"))
    mrp = _num(item.get("mrp"))
    discount = _num(item.get("discount_percentage", item.get("discount_pct")))
    if discount is None and price and mrp and mrp > price:
        discount = round((mrp - price) / mrp * 100, 1)

    raw = dict(item)

    return Offer(
        site=site,
        title=title,
        price=price,
        url=url,
        mrp=mrp,
        discount_pct=discount,
        rating=_num(item.get("rating")),
        reviews=_int(item.get("reviews_count", item.get("reviews"))),
        image_url=str(item.get("image_url") or "").strip(),
        seller=str(item.get("seller") or "").strip(),
        in_stock=item.get("in_stock"),
        source_server=server,
        is_sample=bool(item.get("is_sample")),
        raw=raw,
    )


def _iter_items(payload: Any) -> Iterable[dict]:
    """Yield candidate listing dicts from an arbitrary payload shape."""
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        # If it looks like a single listing, yield it directly.
        if payload.get("title") or payload.get("name"):
            yield payload
            return
        # Otherwise walk the known list-bearing keys.
        seen_lists = 0
        for key in _LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                seen_lists += 1
                for item in value:
                    if isinstance(item, dict):
                        yield item
        if seen_lists == 0:
            # Last resort: any list value in the dict.
            for value in payload.values():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            yield item


def offers_from_payload(
    payload: Any,
    server: str,
    default_site: Optional[str] = None,
) -> list[Offer]:
    """Normalize an arbitrary MCP tool result into deduplicated offers."""
    offers: list[Offer] = []
    seen: set[tuple[str, str]] = set()

    for item in _iter_items(payload):
        offer = _to_offer(item, server=server, default_site=default_site)
        if offer is None:
            continue
        if offer.dedupe_key in seen:
            continue
        seen.add(offer.dedupe_key)
        offers.append(offer)

    if not offers and payload is not None:
        logger.debug("No offers parsed from payload: %s", str(payload)[:200])
    return offers
