"""network_agent — Google ADK Network Diagnostics Agent for Prodapt AI Operations Center.

Implements Section 6.3 of the project specification:
1. Google ADK Agent exposing SQL-backed tools over A2A protocol (port 8001).
2. Diagnostic checks against telecom_ops.db (network_towers, tower_performance, open_incidents).
3. Natural language diagnostic router diagnose_network(query).
"""

from .tools import (
    DATABASE_PATH,
    check_tower_status,
    diagnose_network,
    get_connection,
    get_regional_network_summary,
    run_connectivity_diagnostics,
)
from .agent import agent, app, create_network_agent, run_server

__all__ = [
    "DATABASE_PATH",
    "get_connection",
    "check_tower_status",
    "run_connectivity_diagnostics",
    "get_regional_network_summary",
    "diagnose_network",
    "agent",
    "app",
    "create_network_agent",
    "run_server",
]
