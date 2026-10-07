"""ADK Service Entrypoint for Network Diagnostics (Port 8001).

Implements Section 4 and Section 6.3 of the Prodapt AI Operations Center specification.
Mounts the Google ADK Network Diagnostics agent over A2A protocol on port 8001.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure prodapt-project is on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from network_agent.agent import agent, app, run_server

if __name__ == "__main__":
    run_server(port=8001)
