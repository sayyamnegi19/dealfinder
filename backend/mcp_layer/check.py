"""CLI probe for the MCP pool (Phase 1 gate).

Usage:
    python -m mcp_layer.check "sony wh-1000xm5"
    python -m mcp_layer.check "iphone 15" --sites amazon --limit 3
    python -m mcp_layer.check "laptop" --force-fallback
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

from .config import load_server_configs  # noqa: E402
from .pool import MCPPool  # noqa: E402

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"


def _fmt_price(value: float | None) -> str:
    return f"₹{value:,.0f}" if value else "—"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the Deal Finder MCP server pool.")
    parser.add_argument("query", help="Product search query")
    parser.add_argument("--sites", default="amazon,flipkart", help="Comma-separated sites (default: amazon,flipkart)")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MCP_MAX_RESULTS_DEFAULT", "5")))
    parser.add_argument("--force-fallback", action="store_true", help="Skip live servers, use the demo fallback")
    parser.add_argument("--config", default=os.getenv("MCP_SERVERS_FILE", str(ROOT_DIR / "mcp_servers.json")))
    args = parser.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    configs = load_server_configs(args.config)

    print(f"{BOLD}MCP pool:{RESET} {len(configs)} server(s) configured")
    for cfg in configs:
        kind = "fallback" if cfg.is_fallback else "live"
        print(f"  - {cfg.name} ({kind})  timeout={cfg.timeout}s  tools={cfg.site_tools or cfg.generic_tool}")
    print(f"\n{BOLD}Query:{RESET} {args.query!r}  sites={sites}  limit={args.limit}\n")

    pool = MCPPool(configs, force_fallback=args.force_fallback)
    outcome = await pool.search(args.query, sites=sites, limit=args.limit)

    print(f"{BOLD}Server attempts:{RESET}")
    for attempt in outcome.attempts:
        status = f"{GREEN}OK{RESET}" if attempt.ok else f"{RED}FAIL{RESET}"
        detail = f"{attempt.count} offers" if attempt.ok else attempt.error
        print(f"  [{status}] {attempt.server:<28} {attempt.latency_ms:>6} ms  {detail}")

    if not outcome.any_success:
        print(f"\n{RED}All MCP servers failed - no data.{RESET}")
        return 1

    if not outcome.offers:
        print(f"\n{YELLOW}Servers responded but no listings were found.{RESET}")
        return 2

    if outcome.is_sample:
        print(f"\n{YELLOW}⚠ Sample data from the demo fallback server.{RESET}")

    print(f"\n{BOLD}Offers from {outcome.server} ({len(outcome.offers)}):{RESET}")
    header = f"  {'site':<10} {'price':>10} {'mrp':>10} {'disc':>6}  title"
    print(DIM + header + RESET)
    for offer in sorted(outcome.offers, key=lambda o: (o.price is None, o.price or 0)):
        disc = f"{offer.discount_pct:.0f}%" if offer.discount_pct else "—"
        title = offer.title[:62]
        print(f"  {offer.site:<10} {_fmt_price(offer.price):>10} {_fmt_price(offer.mrp):>10} {disc:>6}  {title}")
        print(f"{DIM}             {offer.url[:100]}{RESET}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
