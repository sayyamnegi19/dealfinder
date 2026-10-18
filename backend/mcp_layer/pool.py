"""MCP pool: queries configured MCP servers in priority order with failover.

The rest of the app (agent tools, API) only talks to `MCPPool.search()` and gets
back a normalized `SearchOutcome`, so individual MCP servers can be added,
disabled or swapped purely through `mcp_servers.json`.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .adapters import offers_from_payload, unwrap_result
from .config import ServerConfig
from .types import Attempt, DEFAULT_SITES, Offer, SearchOutcome

logger = logging.getLogger("mcp_layer.pool")


def _dedupe(offers: list[Offer]) -> list[Offer]:
    seen: set[tuple[str, str]] = set()
    result: list[Offer] = []
    for offer in offers:
        if offer.dedupe_key in seen:
            continue
        seen.add(offer.dedupe_key)
        result.append(offer)
    return result


class MCPPool:
    def __init__(self, configs: list[ServerConfig], force_fallback: bool = False):
        self.configs = [cfg for cfg in configs if cfg.enabled]
        self.force_fallback = force_fallback

    async def search(
        self,
        query: str,
        sites: list[str] | None = None,
        limit: int = 5,
    ) -> SearchOutcome:
        """Query servers in priority order; the first one that returns offers wins.

        A fallback server is only consulted when no regular server completed
        successfully, or when `force_fallback` is set.
        """
        sites = [s for s in (sites or list(DEFAULT_SITES)) if s]
        attempts: list[Attempt] = []

        for cfg in self.configs:
            if self.force_fallback and not cfg.is_fallback:
                logger.info("force_fallback: skipping live server %s.", cfg.name)
                continue
            if cfg.is_fallback and not self.force_fallback and any(a.ok for a in attempts):
                logger.info("Skipping fallback server %s (a live server already responded).", cfg.name)
                continue

            started = time.monotonic()
            try:
                offers = await self._query_server(cfg, query, sites, limit)
                latency_ms = int((time.monotonic() - started) * 1000)
                attempts.append(Attempt(server=cfg.name, ok=True, count=len(offers), latency_ms=latency_ms))
                logger.info("MCP server %s returned %d offers in %d ms.", cfg.name, len(offers), latency_ms)
                if offers:
                    return SearchOutcome(
                        query=query,
                        offers=_dedupe(offers),
                        attempts=attempts,
                        server=cfg.name,
                        is_sample=cfg.is_fallback,
                    )
                # Successful but empty: move on to the next server.
            except Exception as exc:  # noqa: BLE001 - failover is the whole point
                latency_ms = int((time.monotonic() - started) * 1000)
                message = f"{type(exc).__name__}: {exc}"[:300]
                attempts.append(Attempt(server=cfg.name, ok=False, error=message, latency_ms=latency_ms))
                logger.warning("MCP server %s failed (%s).", cfg.name, message)

        return SearchOutcome(query=query, offers=[], attempts=attempts)

    async def _query_server(
        self,
        cfg: ServerConfig,
        query: str,
        sites: list[str],
        limit: int,
    ) -> list[Offer]:
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        transport = StdioTransport(
            command=cfg.command,
            args=cfg.args,
            env=cfg.env,
            cwd=cfg.cwd,
        )

        # Overall guard so a hanging server can never hang the request.
        async with asyncio.timeout(cfg.timeout * max(1, len(sites)) + 15):
            async with Client(transport) as client:
                if cfg.site_tools:
                    offers: list[Offer] = []
                    errors: list[str] = []
                    attempted = 0
                    for site in sites:
                        tool = cfg.site_tools.get(site)
                        if not tool:
                            continue
                        attempted += 1
                        try:
                            result = await asyncio.wait_for(
                                client.call_tool(tool, {"query": query, "limit": limit}),
                                timeout=cfg.timeout,
                            )
                            site_offers = offers_from_payload(
                                unwrap_result(result), server=cfg.name, default_site=site
                            )
                            if not site_offers:
                                logger.info("%s returned no offers for '%s'.", cfg.name, site)
                            offers.extend(site_offers)
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"{site}: {type(exc).__name__}: {exc}")
                            logger.warning("%s / %s raised: %s", cfg.name, site, exc)

                    if not offers and errors and len(errors) == attempted:
                        raise RuntimeError("; ".join(errors)[:300])
                    return _dedupe(offers)

                if cfg.generic_tool:
                    result = await asyncio.wait_for(
                        client.call_tool(cfg.generic_tool, {"query": query, "limit": limit}),
                        timeout=cfg.timeout,
                    )
                    return _dedupe(
                        offers_from_payload(unwrap_result(result), server=cfg.name, default_site=None)
                    )

        return []
