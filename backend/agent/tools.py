"""Agent dependencies and the search tool backed by the MCP pool."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from mcp_layer.pool import MCPPool
from mcp_layer.types import Attempt, Offer

logger = logging.getLogger("agent.tools")

EventEmitter = Callable[[str, dict], Awaitable[None]]


@dataclass
class AgentDeps:
    """Everything the agent tools need, plus the state they accumulate."""

    pool: MCPPool
    sites: list[str]
    max_results: int = 5
    max_tool_calls: int = 3
    emit: Optional[EventEmitter] = None

    # Accumulated state (read by the API layer after the run).
    offers: list[Offer] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    servers_used: list[str] = field(default_factory=list)
    tool_calls: int = 0
    is_sample: bool = False

    async def notify(self, event_type: str, payload: dict | None = None) -> None:
        if self.emit is not None:
            try:
                await self.emit(event_type, payload or {})
            except Exception:  # noqa: BLE001 - event delivery must never kill a run
                logger.exception("Event emitter failed for %s", event_type)

    def add_offers(self, offers: list[Offer]) -> list[int]:
        """Append new (deduplicated) offers; return the IDs assigned to them."""
        seen = {offer.dedupe_key for offer in self.offers}
        ids: list[int] = []
        for offer in offers:
            if offer.dedupe_key in seen:
                continue
            seen.add(offer.dedupe_key)
            self.offers.append(offer)
            ids.append(len(self.offers) - 1)
            if offer.source_server and offer.source_server not in self.servers_used:
                self.servers_used.append(offer.source_server)
            if offer.is_sample:
                self.is_sample = True
        return ids

    def compact_listings(self) -> list[dict]:
        """All accumulated listings, in the compact shape the LLM sees."""
        return [{"id": index, **offer.compact()} for index, offer in enumerate(self.offers)]
