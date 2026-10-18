"""Convenience helpers for the MCP layer."""

from __future__ import annotations

import os
from pathlib import Path

from .config import ServerConfig, load_server_configs
from .pool import MCPPool
from .types import Attempt, DEFAULT_SITES, Offer, SearchOutcome, SITE_LABELS, site_from_label

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SERVERS_FILE = ROOT_DIR / "mcp_servers.json"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def default_pool(force_fallback: bool | None = None) -> MCPPool:
    """Build the configured MCP pool (used by the agent and the API)."""
    servers_file = os.getenv("MCP_SERVERS_FILE", str(DEFAULT_SERVERS_FILE))
    configs = load_server_configs(servers_file)
    if force_fallback is None:
        force_fallback = _truthy(os.getenv("MCP_FORCE_FALLBACK"))
    return MCPPool(configs, force_fallback=force_fallback)


__all__ = [
    "Attempt",
    "DEFAULT_SITES",
    "DEFAULT_SERVERS_FILE",
    "MCPPool",
    "Offer",
    "SearchOutcome",
    "ServerConfig",
    "SITE_LABELS",
    "default_pool",
    "load_server_configs",
    "site_from_label",
]
