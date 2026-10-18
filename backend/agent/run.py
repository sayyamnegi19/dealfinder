"""CLI: run the Deal Finder agent end to end (Phase 2 gate).

Usage:
    python -m agent.run "sony wh-1000xm5"
    python -m agent.run "iphone 15 128gb" --limit 4
    python -m agent.run "laptop under 60000" --force-fallback
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

from mcp_layer import default_pool  # noqa: E402

from .finder import run_deal_search  # noqa: E402

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

ICONS = {
    "agent_started": "🚀",
    "tool_started": "🔎",
    "search_completed": "📦",
    "llm_tool_call": "🧠",
    "llm_tool_result": "↩️",
    "agent_text": "💬",
    "result_ready": "✅",
}


async def emit(event_type: str, payload: dict) -> None:
    icon = ICONS.get(event_type, "•")
    if event_type == "agent_text":
        print(payload.get("delta", ""), end="", flush=True)
        return

    if event_type == "tool_started":
        print(f"{icon} Searching: {payload.get('query')!r} on {', '.join(payload.get('sites', []))}")
    elif event_type == "search_completed":
        server = payload.get("server") or "none"
        verdict = f"{payload.get('new_listings', 0)} new listings" if server != "none" else "no listings"
        tag = f" {YELLOW}[sample data]{RESET}" if payload.get("is_sample") else ""
        print(f"{icon} MCP result via {server}: {verdict}{tag}")
        for attempt in payload.get("attempts", []):
            status = f"{GREEN}ok{RESET}" if attempt["ok"] else f"fail: {attempt['error'][:80]}"
            print(f"{DIM}    - {attempt['server']:<28} {attempt['latency_ms']:>6} ms  {status}{RESET}")
    elif event_type == "result_ready":
        print(f"{icon} Agent finished in {payload.get('latency_ms')} ms using {payload.get('model_used')}")
    else:
        print(f"{icon} {event_type}: {json.dumps(payload)[:200]}")


def _fmt_price(value) -> str:
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def print_report(result) -> None:
    report = result.report
    print()
    print(f"{BOLD}{'=' * 78}{RESET}")
    print(f"{BOLD}Query understood:{RESET} {report.query_understood}")
    print(f"{BOLD}{'=' * 78}{RESET}")

    print(f"\n{BOLD}Listings seen by the agent ({len(result.offers)}):{RESET}")
    for index, offer in enumerate(result.offers):
        marker = ""
        if report.best_deal and report.best_deal.offer_id == index:
            marker = f" {GREEN}◀ BEST DEAL{RESET}"
        sample = f" {YELLOW}[sample]{RESET}" if offer.is_sample else ""
        print(
            f"  [{index:>2}] {offer.site:<9} {_fmt_price(offer.price):>10}  "
            f"{offer.title[:58]}{sample}{marker}"
        )

    print(f"\n{BOLD}Groups:{RESET}")
    for gi, group in enumerate(report.groups):
        ids = ", ".join(str(i) for i in group.offer_ids)
        print(f"  ({gi}) {group.canonical_name}  {DIM}[offers: {ids}]{RESET}")
        if group.note:
            print(f"{DIM}       {group.note}{RESET}")

    print(f"\n{BOLD}Best deal:{RESET}")
    if report.best_deal:
        best = report.best_deal
        offer = result.offers[best.offer_id]
        print(f"  {CYAN}{offer.title}{RESET}")
        print(f"  {_fmt_price(offer.price)} on {offer.site}  ({offer.url})")
        print(f"  Why: {best.reason}")
    else:
        print("  (none)")

    print(f"\n{BOLD}Summary:{RESET} {report.summary}")
    if report.caveats:
        print(f"\n{BOLD}Caveats:{RESET}")
        for caveat in report.caveats:
            print(f"  - {caveat}")

    print(
        f"\n{DIM}model={result.model_used}  latency={result.latency_ms} ms  "
        f"requests={result.requests}  tokens={result.input_tokens}in/{result.output_tokens}out  "
        f"servers={result.servers_used or '—'}{RESET}"
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Deal Finder agent for a query.")
    parser.add_argument("query", help="What the user wants to buy")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MCP_MAX_RESULTS_DEFAULT", "5")))
    parser.add_argument("--sites", default="amazon,flipkart")
    parser.add_argument("--force-fallback", action="store_true", help="Use only the demo fallback MCP server")
    parser.add_argument("--json", action="store_true", help="Dump the raw result as JSON instead of a report")
    args = parser.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    pool = default_pool(force_fallback=True if args.force_fallback else None)

    result = await run_deal_search(args.query, sites=sites, limit=args.limit, emit=emit, pool=pool)

    if args.json:
        print(json.dumps({"report": result.report.model_dump(), "offers": [o.compact() for o in result.offers]}, indent=2))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
