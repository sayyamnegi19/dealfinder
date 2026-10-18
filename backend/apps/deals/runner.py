"""Bridge between Django and the Pydantic AI agent run.

Responsibilities:
  * claim a pending search atomically (so only one runner starts it),
  * persist agent stream events (for replay over SSE),
  * run the agent, persist the structured result, and update status.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from asgiref.sync import sync_to_async
from django.utils import timezone

from agent.finder import DealSearchResult, run_deal_search
from mcp_layer import default_pool

from .models import AgentEvent, AgentRun, Offer, ProductGroup, SearchQuery

logger = logging.getLogger("agent.runner")

# Keep strong references to background tasks so they are not garbage collected.
_background_tasks: set[asyncio.Task] = set()


def track_task(task: asyncio.Task) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# --- small sync helpers, wrapped for async callers ---------------------------


@sync_to_async
def get_search(search_id) -> Optional[SearchQuery]:
    return SearchQuery.objects.filter(id=search_id).first()


@sync_to_async
def get_status(search_id) -> Optional[str]:
    return SearchQuery.objects.filter(id=search_id).values_list("status", flat=True).first()


@sync_to_async
def claim_search(search_id) -> bool:
    """Atomically move pending -> running. Returns True when this caller claimed it."""
    updated = SearchQuery.objects.filter(id=search_id, status=SearchQuery.Status.PENDING).update(
        status=SearchQuery.Status.RUNNING
    )
    return updated == 1


@sync_to_async
def events_after(search_id, last_seq: int) -> list[dict[str, Any]]:
    run = AgentRun.objects.filter(search_id=search_id).order_by("-id").first()
    if run is None:
        return []
    return list(run.events.filter(seq__gt=last_seq).values("seq", "type", "payload"))


@sync_to_async
def final_payload(search_id) -> dict:
    from .serializers import SearchQueryDetailSerializer

    search = (
        SearchQuery.objects.prefetch_related("groups__offers").filter(id=search_id).first()
    )
    if search is None:
        return {}
    return dict(SearchQueryDetailSerializer(search).data)


@sync_to_async
def _create_run(search: SearchQuery) -> AgentRun:
    return AgentRun.objects.create(search_id=search.id, status=AgentRun.Status.RUNNING)


@sync_to_async
def _save_event(run_id, seq: int, event_type: str, payload: dict) -> None:
    AgentEvent.objects.create(run_id=run_id, seq=seq, type=event_type, payload=payload)


@sync_to_async
def _mark_failed(search_id, run_id, error: str) -> None:
    SearchQuery.objects.filter(id=search_id).update(
        status=SearchQuery.Status.FAILED,
        error=error[:2000],
        completed_at=timezone.now(),
    )
    AgentRun.objects.filter(id=run_id).update(status=AgentRun.Status.FAILED, error=error[:2000])


# --- result persistence -------------------------------------------------------


def _persist_result_sync(search: SearchQuery, run: AgentRun, result: DealSearchResult) -> None:
    report = result.report
    offer_rows: dict[int, Offer] = {}

    def create_offer(group: ProductGroup, index: int) -> None:
        source = result.offers[index]
        row = Offer.objects.create(
            group=group,
            site=source.site,
            title=source.title[:600],
            price=source.price,
            mrp=source.mrp,
            discount_pct=source.discount_pct,
            rating=source.rating,
            reviews=source.reviews,
            url=(source.url or "https://example.invalid")[:1200],
            image_url=(source.image_url or "")[:1200],
            seller=(source.seller or "")[:240],
            in_stock=source.in_stock,
            source_server=(source.source_server or "")[:80],
            is_sample=source.is_sample,
            raw=source.raw if isinstance(source.raw, dict) else {},
        )
        offer_rows[index] = row

    used_ids: set[int] = set()

    for rank, group in enumerate(report.groups):
        group_row = ProductGroup.objects.create(
            search=search,
            rank=rank,
            canonical_name=group.canonical_name[:500],
            note=(group.note or "")[:1000],
            attributes={},
        )
        created = 0
        for offer_id in group.offer_ids:
            if not (0 <= offer_id < len(result.offers)) or offer_id in used_ids:
                continue
            create_offer(group_row, offer_id)
            used_ids.add(offer_id)
            created += 1
        if created == 0:
            group_row.delete()

    # Keep any listings the agent saw but did not group, so nothing is lost.
    leftovers = [i for i in range(len(result.offers)) if i not in used_ids and result.offers[i].price]
    if leftovers:
        other = ProductGroup.objects.create(
            search=search,
            rank=len(report.groups),
            canonical_name="Other listings",
            attributes={},
        )
        for offer_id in leftovers:
            create_offer(other, offer_id)

    if report.best_deal and report.best_deal.offer_id in offer_rows:
        best_row = offer_rows[report.best_deal.offer_id]
        best_row.group.best_offer = best_row
        best_row.group.save(update_fields=["best_offer"])

    SearchQuery.objects.filter(id=search.id).update(
        status=SearchQuery.Status.COMPLETED,
        normalized_query=(report.query_understood or "")[:500],
        summary=report.summary or "",
        best_deal_reason=(report.best_deal.reason if report.best_deal else ""),
        caveats=report.caveats or [],
        model_used=(result.model_used or "")[:120],
        latency_ms=result.latency_ms,
        source_servers=result.servers_used or [],
        is_sample=result.is_sample,
        error="",
        completed_at=timezone.now(),
    )

    AgentRun.objects.filter(id=run.id).update(
        status=AgentRun.Status.COMPLETED,
        model_used=(result.model_used or "")[:120],
        latency_ms=result.latency_ms,
        tokens_in=result.input_tokens,
        tokens_out=result.output_tokens,
    )


_persist_result = sync_to_async(_persist_result_sync)


# --- main entry point ---------------------------------------------------------


async def execute_search(search_id) -> None:
    """Run the agent for a claimed search and persist everything."""
    search = await get_search(search_id)
    if search is None:
        logger.warning("execute_search: search %s not found", search_id)
        return

    run = await _create_run(search)
    seq = {"value": 0}

    async def emit(event_type: str, payload: dict) -> None:
        # Text deltas are not persisted (structured output rarely streams text).
        if event_type == "agent_text":
            return
        seq["value"] += 1
        try:
            await _save_event(run.id, seq["value"], event_type, payload)
        except Exception:  # noqa: BLE001 - persistence must not kill the run
            logger.exception("Failed to persist event %s", event_type)

    try:
        result = await run_deal_search(
            search.user_query,
            sites=list(search.requested_sites or []) or None,
            limit=search.result_limit or 5,
            emit=emit,
            pool=default_pool(),
        )
        await _persist_result(search, run, result)
        logger.info(
            "Search %s completed: %d groups, model=%s, %d ms",
            search_id,
            len(result.report.groups),
            result.model_used,
            result.latency_ms,
        )
    except Exception as exc:  # noqa: BLE001 - any failure must mark the search failed
        logger.exception("Search %s failed", search_id)
        seq["value"] += 1
        try:
            await _save_event(run.id, seq["value"], "error", {"message": str(exc)[:500]})
        except Exception:  # noqa: BLE001
            pass
        await _mark_failed(search_id, run.id, f"{type(exc).__name__}: {exc}")
