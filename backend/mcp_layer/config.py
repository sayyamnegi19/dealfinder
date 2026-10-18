"""Load the MCP server pool configuration (mcp_servers.json)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


@dataclass
class ServerConfig:
    name: str
    description: str
    command: str
    args: list[str]
    cwd: str | None
    env: dict[str, str]
    site_tools: dict[str, str] = field(default_factory=dict)  # {"amazon": "search_amazon", ...}
    generic_tool: str | None = None  # single tool covering all sites
    timeout: float = 30.0
    is_fallback: bool = False
    enabled: bool = True


def _subst(value: str) -> str:
    return value.replace("{python}", sys.executable).replace("{backend}", str(BACKEND_DIR))


# Quiet the FastMCP servers' startup banner and PyPI update checks.
DEFAULT_SERVER_ENV = {
    "FASTMCP_SHOW_SERVER_BANNER": "false",
    "FASTMCP_CHECK_FOR_UPDATES": "off",
    "FASTMCP_ENABLE_RICH_LOGGING": "false",
    "FASTMCP_LOG_LEVEL": "WARNING",
}


def load_server_configs(path: str | os.PathLike[str]) -> list[ServerConfig]:
    """Parse mcp_servers.json into ServerConfig objects, preserving priority order.

    Fallback servers are always moved to the end regardless of their position.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    servers: list[ServerConfig] = []

    for entry in raw.get("servers", []):
        if not entry.get("enabled", True):
            continue
        transport = entry.get("transport", {})
        tools = entry.get("tools", {})
        env = {
            **os.environ,
            **DEFAULT_SERVER_ENV,
            **{str(k): str(v) for k, v in entry.get("env", {}).items()},
        }

        servers.append(
            ServerConfig(
                name=entry["name"],
                description=entry.get("description", ""),
                command=_subst(transport.get("command", "{python}")),
                args=[_subst(str(a)) for a in transport.get("args", [])],
                cwd=_subst(transport.get("cwd", "{backend}")),
                env=env,
                site_tools={str(k): str(v) for k, v in tools.get("search_per_site", {}).items()},
                generic_tool=tools.get("search") or tools.get("compare"),
                timeout=float(entry.get("timeout_seconds", os.getenv("MCP_TIMEOUT_SECONDS", "30"))),
                is_fallback=bool(entry.get("is_fallback", False)),
                enabled=bool(entry.get("enabled", True)),
            )
        )

    # Python's sort is stable: real servers keep their order, fallbacks go last.
    servers.sort(key=lambda cfg: cfg.is_fallback)
    return servers
