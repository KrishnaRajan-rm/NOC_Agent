"""Standalone Network Diagnostics ADK Agent & A2A Service (Port 8001).

Implements Section 6.3 of the Prodapt AI Operations Center specification:
1. Google ADK Agent with clear instructions describing NOC diagnostics responsibilities.
2. Three async SQL-backed tools:
   - check_tower_status(tower_id)
   - run_connectivity_diagnostics(tower_id, symptom)
   - get_regional_network_summary(region)
3. Exposes the agent via to_a2a on port 8001 with agent card at /.well-known/agent-card.json.
4. Provides interactive CLI mode and uvicorn service runner.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

# Ensure prodapt-project is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

import google.adk as adk
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from network_agent.tools import (
    check_tower_status,
    diagnose_network,
    get_regional_network_summary,
    run_connectivity_diagnostics,
)

# ============================================================
# 1. ASYNC ADK TOOL WRAPPERS
# ============================================================

async def check_tower_status_tool(tower_id: str) -> dict[str, Any]:
    """Check inventory, latest telemetry KPIs, and open incidents for a specific tower from SQLite.

    Args:
        tower_id: Tower identifier (e.g. 'TX-512', 'FL-090', 'IL-104').
    """
    return check_tower_status(tower_id)


async def run_connectivity_diagnostics_tool(tower_id: str, symptom: str = "") -> dict[str, Any]:
    """Diagnose connectivity issues, session drops, and latency problems on a tower using SQLite telemetry.

    Args:
        tower_id: Tower identifier (e.g. 'TX-512', 'FL-090').
        symptom: Optional customer symptom description.
    """
    return run_connectivity_diagnostics(tower_id, symptom=symptom)


async def get_regional_network_summary_tool(region: str) -> dict[str, Any]:
    """Aggregate tower status counts and active incidents for a telecom region from SQLite.

    Args:
        region: Geographic region name ('Midwest', 'Northeast', 'Southeast', 'Southwest', 'West').
    """
    return get_regional_network_summary(region)


# ============================================================
# 2. ADK AGENT DEFINITION
# ============================================================

NOC_INSTRUCTION = """You are Prodapt's Network Operations Center (NOC) Diagnostics Specialist.
Your responsibility is to diagnose network connectivity problems, tower faults, and service degradations.

Rules and Guidelines:
1. Always ground your diagnostics in live database records using your SQL tools:
   - check_tower_status: retrieves tower inventory, latest telemetry sample (signal, packet loss, latency, throughput), and active open incidents.
   - run_connectivity_diagnostics: compares KPIs against telecom standards and generates actionable NOC findings and recommendations.
   - get_regional_network_summary: provides a macro breakdown of towers and health across a region.
2. Never make up or hallucinate telemetry. Always report the latest recorded sample.
3. Adhere to NOC performance thresholds:
   - Signal strength: >= -90 dBm is acceptable; -110 to -90 dBm is marginal; < -110 dBm is poor.
   - Packet loss: <= 1.0% is normal; > 2.0% is elevated; > 5.0% is severe.
   - Latency on 5G: <= 40 ms is normal; > 50 ms is elevated.
   - Downlink throughput: degraded when 5G operational site drops below 100 Mbps.
   - OFFLINE site or 100% packet loss: site is down. Do NOT troubleshoot customer handset or advise device reset.
4. Always reference related active open incident IDs (e.g. INC-8841) to keep subscribers and field teams synchronized.
"""

def create_network_agent() -> adk.Agent:
    """Create and return the Google ADK Network Diagnostics Agent."""
    return adk.Agent(
        name="network_diagnostics",
        description="Prodapt Network Diagnostics agent for analyzing tower status, telemetry, and NOC incidents.",
        instruction=NOC_INSTRUCTION,
        model=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
        tools=[
            check_tower_status_tool,
            run_connectivity_diagnostics_tool,
            get_regional_network_summary_tool,
        ],
    )


# Initialize ADK Agent instance
agent = create_network_agent()

# Create A2A Starlette ASGI Application for port 8001
app = to_a2a(agent, host="localhost", port=8001, protocol="http")


# ============================================================
# 3. INTERACTIVE CLI RUNNER (LIKE SQL_AGENT)
# ============================================================

def run_interactive_cli() -> None:
    """Run an interactive diagnostic CLI session for staff and testing."""
    print("\n" + "=" * 55)
    print("      PRODAPT NETWORK DIAGNOSTICS AGENT (NOC)")
    print("=" * 55)
    print("Service: Network Diagnostics (Google ADK / SQLite)")
    print("Target A2A Port: 8001")
    print("\nEnter a question in plain English (or 'exit' to quit).")
    print("Example queries:")
    print("  - Diagnose 5G drops near tower TX-512 in Austin.")
    print("  - What is wrong with tower FL-090 in Miami?")
    print("  - Summarize the Southwest region.")
    print("  - What is the status of tower TX-208 in Dallas?")
    print("-" * 55)

    while True:
        try:
            query = input("\nNetwork Query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q"}:
            print("Exiting Network Diagnostics Agent.")
            break

        print("\nDiagnosing network telemetry and incidents...")
        try:
            response = diagnose_network(query)
            print("\n" + "=" * 55)
            print("RESPONSE:")
            print("=" * 55)
            print(response)
        except Exception as err:
            print(f"\nERROR: {err}")


def run_server(host: str = "0.0.0.0", port: int = 8001) -> None:
    """Run the A2A HTTP microservice using uvicorn."""
    print(f"Starting Network Diagnostics A2A service on {host}:{port}...")
    print(f"Agent Card will be available at: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prodapt Network Diagnostics Agent")
    parser.add_argument("--server", action="store_true", help="Run as A2A HTTP microservice on port 8001")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on (default: 8001)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    if args.server:
        run_server(host=args.host, port=args.port)
    else:
        run_interactive_cli()
