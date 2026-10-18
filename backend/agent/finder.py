"""The Deal Finder agent: instructions, tool wiring, and the run entry point."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

from pydantic_ai import Agent, AgentRunResultEvent, RunContext
from pydantic_ai.messages import (
    AgentStreamEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
)

from mcp_layer import DEFAULT_SITES, Offer, default_pool
from mcp_layer.types import Attempt

from .llm import build_model
from .schemas import DealReport
from .tools import AgentDeps

logger = logging.getLogger("agent.finder")

try:  # text deltas (structured output usually produces none, but stay safe)
    from pydantic_ai.messages import TextPartDelta
except ImportError:  # pragma: no cover
    TextPartDelta = None  # type: ignore[assignment]


INSTRUCTIONS = """\
You are Deal Finder, a careful and honest shopping assistant for Indian e-commerce.

Your job: find where a product is sold for the best total deal across Amazon India and Flipkart.

Workflow:
1. Call `search_marketplaces` once with clean, specific search terms derived from the user's request.
   Include brand and model number when the user gives them. Call it a second time with different
   terms ONLY if the first results are clearly irrelevant or the user asked for a specific variant.
2. Review the returned listings. Group listings that refer to the same product
   (same model and variant; ignore colour differences unless they materially change the price).
3. Choose the best deal: the lowest price among trustworthy listings for the product the user
   actually wants. Prefer listings with meaningful ratings or review counts.
4. Reference listings strictly by their `id`. Never invent products, prices, or URLs.
5. Write the summary in plain, friendly language with INR prices: what was found, the price range,
   and the recommended deal.

Rules:
- If a marketplace is missing from the results (e.g. Amazon was blocked), add a caveat saying so.
- If listings are sample data (`is_sample: true`), state clearly that live marketplace data was
  unavailable and the listings are illustrative samples.
- If nothing relevant was found, set `best_deal` to null and explain in the summary.
- Keep `summary` to 2-4 sentences. Keep `caveats` short.
"""


@dataclass
class DealSearchResult:
    """Full outcome of one agent run (report + raw data + telemetry)."""

    query: str
    report: DealReport
    offers: list[Offer]
    attempts: list[Attempt]
    servers_used: list[str] = field(default_factory=list)
    is_sample: bool = False
    model_used: str = ""
    latency_ms: int = 0
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


def _env_chain() -> list[str]:
    raw = os.getenv("LLM_CHAIN", "google:gemini-3.5-flash-lite,groq:openai/gpt-oss-120b")
    return [spec.strip() for spec in raw.split(",") if spec.strip()]


def build_agent(model) -> Agent[AgentDeps, DealReport]:
    """Create the agent and register its tool."""
    agent: Agent[AgentDeps, DealReport] = Agent(
        model,
        deps_type=AgentDeps,
        output_type=DealReport,
        instructions=INSTRUCTIONS,
        retries=2,
    )

    @agent.tool
    async def search_marketplaces(ctx: RunContext[AgentDeps], query: str) -> list[dict]:
        """Search Amazon India and Flipkart for a product and return matching listings.

        Each returned listing has: `id` (use this when referring to it), `site`, `title`,
        `price` (INR), optional `mrp`, `discount_pct`, `rating`, `url`, and `is_sample`
        when the data is demo data. Returns an empty list when nothing was found.

        Args:
            query: Product search terms, e.g. "Sony WH-1000XM5" or "iphone 15 128gb".
        """
        deps = ctx.deps

        if deps.tool_calls >= deps.max_tool_calls:
            logger.warning("Tool call limit reached; returning what we already have.")
            return deps.compact_listings()
        deps.tool_calls += 1

        await deps.notify("tool_started", {"query": query, "sites": deps.sites})

        outcome = await deps.pool.search(query, sites=deps.sites, limit=deps.max_results)
        deps.attempts.extend(outcome.attempts)

        new_ids = deps.add_offers(outcome.offers)

        if outcome.is_sample:
            deps.is_sample = True

        await deps.notify(
            "search_completed",
            {
                "query": query,
                "server": outcome.server,
                "attempts": [
                    {
                        "server": attempt.server,
                        "ok": attempt.ok,
                        "count": attempt.count,
                        "error": attempt.error,
                        "latency_ms": attempt.latency_ms,
                    }
                    for attempt in outcome.attempts
                ],
                "new_listings": len(new_ids),
                "total_listings": len(deps.offers),
                "is_sample": outcome.is_sample,
            },
        )

        listings = deps.compact_listings()
        logger.info(
            "search_marketplaces(%r): %d new, %d total listings (served by %s)",
            query,
            len(new_ids),
            len(listings),
            outcome.server,
        )
        return listings

    return agent


async def _forward_stream_event(event: AgentStreamEvent, deps: AgentDeps) -> None:
    """Map pydantic-ai stream events to our own event vocabulary."""
    if TextPartDelta is not None and isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
        delta = event.delta.content_delta
        if delta and delta.strip():
            await deps.notify("agent_text", {"delta": delta})
    elif isinstance(event, FunctionToolCallEvent):
        name = getattr(event, "tool_name", "") or getattr(getattr(event, "part", None), "tool_name", "")
        await deps.notify("llm_tool_call", {"tool": name})
    elif isinstance(event, FunctionToolResultEvent):
        name = getattr(event, "tool_name", "") or getattr(getattr(event, "part", None), "tool_name", "")
        await deps.notify("llm_tool_result", {"tool": name})


async def run_deal_search(
    user_query: str,
    *,
    chain: list[str] | None = None,
    sites: list[str] | None = None,
    limit: int = 5,
    emit=None,
    pool=None,
) -> DealSearchResult:
    """Run the full agent flow for one user query."""
    chain = chain or _env_chain()
    sites = sites or list(DEFAULT_SITES)
    pool = pool or default_pool()

    deps = AgentDeps(pool=pool, sites=sites, max_results=limit, emit=emit)
    model = build_model(chain)
    agent = build_agent(model)

    await deps.notify("agent_started", {"query": user_query, "chain": chain, "sites": sites})

    started = time.monotonic()
    run_result = None

    async with agent.run_stream_events(user_query, deps=deps) as events:
        async for event in events:
            if isinstance(event, AgentRunResultEvent):
                run_result = event.result
            else:
                await _forward_stream_event(event, deps)

    if run_result is None:
        raise RuntimeError("Agent finished without producing a result.")

    latency_ms = int((time.monotonic() - started) * 1000)
    usage = run_result.usage() if callable(getattr(run_result, "usage", None)) else getattr(run_result, "usage", None)
    model_used = getattr(getattr(run_result, "response", None), "model_name", "") or ""

    # Metadata events for the pool attempts recorded before any live server worked.
    report: DealReport = run_result.output

    await deps.notify(
        "result_ready",
        {
            "report": report.model_dump(),
            "listings": len(deps.offers),
            "servers_used": deps.servers_used,
            "is_sample": deps.is_sample,
            "model_used": model_used,
            "latency_ms": latency_ms,
        },
    )

    return DealSearchResult(
        query=user_query,
        report=report,
        offers=deps.offers,
        attempts=deps.attempts,
        servers_used=deps.servers_used,
        is_sample=deps.is_sample,
        model_used=model_used,
        latency_ms=latency_ms,
        requests=getattr(usage, "requests", 0) or 0,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
    )
