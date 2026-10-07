"""ADK Service Entrypoint for Billing Resolution (Port 8002).

Implements Section 4 and Section 6.4 of the Prodapt AI Operations Center specification.
Mounts the Google ADK Billing Resolution agent over A2A protocol on port 8002.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure prodapt-project is on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from billing_agent.agent import agent, app, run_server

if __name__ == "__main__":
    run_server(port=8002)
