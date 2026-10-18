"""API views: create searches, stream agent progress (SSE), fetch results."""

from __future__ import annotations

import asyncio
import json
import logging

import django.db.utils
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from mcp_layer import load_server_configs

from . import runner
from .models import SearchQuery
from .serializers import (
    SearchQueryDetailSerializer,
    SearchQueryListSerializer,
    SearchRequestSerializer,
)

logger = logging.getLogger("deals.api")

HEARTBEAT_SECONDS = 0.75


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"


@api_view(["POST"])
def search_create(request):
    """Create a search (the agent runs when the client opens the SSE stream)."""
    serializer = SearchRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    search = SearchQuery.objects.create(
        user_query=data["query"],
        requested_sites=data.get("sites") or ["amazon", "flipkart"],
        result_limit=data.get("limit") or 5,
    )
    return Response({"id": str(search.id), "status": search.status}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def search_detail(request, search_id):
    search = (
        SearchQuery.objects.prefetch_related("groups__offers").filter(id=search_id).first()
    )
    if search is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(SearchQueryDetailSerializer(search).data)


@api_view(["GET"])
def search_list(request):
    searches = SearchQuery.objects.order_by("-created_at")[:20]
    return Response(SearchQueryListSerializer(searches, many=True).data)


async def search_stream(request, search_id):
    """SSE stream of agent progress; triggers the run for pending searches."""
    search = await runner.get_search(search_id)
    if search is None:
        return JsonResponse({"detail": "Not found."}, status=404)

    # Only one connection may start the run; others replay + tail.
    claimed = await runner.claim_search(search_id)
    if claimed:
        task = asyncio.create_task(runner.execute_search(search_id))
        runner.track_task(task)

    async def event_stream():
        current = await runner.get_status(search_id)
        yield _sse("status", {"search_id": str(search_id), "status": current or "unknown"})

        last_seq = 0
        while True:
            try:
                events = await runner.events_after(search_id, last_seq)
            except django.db.utils.Error:
                events = []

            for event in events:
                last_seq = event["seq"]
                yield _sse(event["type"], event["payload"] or {})

            current = await runner.get_status(search_id)
            if current in (SearchQuery.Status.COMPLETED, SearchQuery.Status.FAILED):
                payload = await runner.final_payload(search_id)
                yield _sse("done", {"status": current, "search": payload})
                break

            # keepalive comment frame so proxies/clients keep the connection open
            yield ": keepalive\n\n"
            await asyncio.sleep(HEARTBEAT_SECONDS)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


async def mcp_health(request):
    """MCP pool status. Add ?probe=1 to actually connect to each server."""
    configs = load_server_configs(settings.MCP_SERVERS_FILE)

    async def describe(cfg) -> dict:
        entry = {
            "name": cfg.name,
            "description": cfg.description,
            "kind": "fallback" if cfg.is_fallback else "live",
            "timeout_seconds": cfg.timeout,
            "tools": cfg.site_tools or cfg.generic_tool,
        }
        if request.GET.get("probe"):
            from fastmcp import Client
            from fastmcp.client.transports import StdioTransport

            import time

            started = time.monotonic()
            try:
                transport = StdioTransport(command=cfg.command, args=cfg.args, env=cfg.env, cwd=cfg.cwd)
                async with asyncio.timeout(cfg.timeout):
                    async with Client(transport) as client:
                        tools = await client.list_tools()
                entry["probe"] = {
                    "ok": True,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "tools": [t.name for t in tools],
                }
            except Exception as exc:  # noqa: BLE001
                entry["probe"] = {
                    "ok": False,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                }
        return entry

    servers = [await describe(cfg) for cfg in configs]
    return JsonResponse({"servers": servers})
