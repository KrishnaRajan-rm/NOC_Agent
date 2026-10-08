"""Standalone Billing Resolution ADK Agent & A2A Service (Port 8002).

Implements Section 6.4 of the Prodapt AI Operations Center specification:
1. Google ADK Agent with clear instructions describing billing resolution responsibilities.
2. Three async SQL-backed tools:
   - lookup_billing_account(customer_id)
   - check_duplicate_charges(customer_id)
   - apply_billing_credit(customer_id, amount, reason)
3. Exposes the agent via to_a2a on port 8002 with agent card at /.well-known/agent-card.json.
4. Provides interactive CLI mode and uvicorn service runner.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Optional

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

from billing_agent.tools import (
    apply_billing_credit,
    check_duplicate_charges,
    lookup_billing_account,
    resolve_billing,
)

# ============================================================
# 1. ASYNC ADK TOOL WRAPPERS
# ============================================================

async def lookup_billing_account_tool(customer_id: str) -> dict[str, Any]:
    """Retrieve billing account summary, current balance, open charges, and dispute history from SQLite.

    Args:
        customer_id: Customer identifier (e.g. 'CUST-10002').
    """
    return lookup_billing_account(customer_id)


async def check_duplicate_charges_tool(customer_id: str) -> dict[str, Any]:
    """Inspect open billing charges for duplicate line items requiring resolution.

    Args:
        customer_id: Customer identifier (e.g. 'CUST-10002').
    """
    return check_duplicate_charges(customer_id)


async def apply_billing_credit_tool(
    customer_id: str,
    amount: float,
    reason: str,
    related_charge_id: Optional[str] = None,
) -> dict[str, Any]:
    """Apply or stage a billing credit in SQLite following policy limits ($50 threshold).

    Args:
        customer_id: Customer identifier (e.g. 'CUST-10002').
        amount: Dollar amount of credit to be applied.
        reason: Explanation or justification for credit.
        related_charge_id: Optional ID of charge being credited (e.g. 'CHG-50022').
    """
    return apply_billing_credit(
        customer_id=customer_id,
        amount=amount,
        reason=reason,
        related_charge_id=related_charge_id,
    )


# ============================================================
# 2. ADK AGENT DEFINITION
# ============================================================

BILLING_INSTRUCTION = """You are Prodapt's Billing Resolution Specialist.
Your responsibility is to investigate customer billing disputes, detect duplicate charges, and apply or stage credits according to corporate policy.

Rules and Guidelines:
1. Always ground your actions in live database records using your SQL tools:
   - lookup_billing_account: inspects current balance and charges (current_balance equals sum of OPEN charges; PAID rows are historical cycles).
   - check_duplicate_charges: identifies legitimate open duplicate charges and verifies that prior credits have not already resolved the dispute.
   - apply_billing_credit: records credits in SQLite and adjusts account balance if eligible.
2. Adhere strictly to the $50 auto-approval threshold from billing_disputes_policy.txt:
   - If credit amount <= $50.00: status is APPLIED and current_balance in billing_accounts is reduced.
   - If credit amount > $50.00: status is PENDING_APPROVAL and current_balance remains UNCHANGED pending supervisor review.
3. Recurring monthly plan fees in different months (e.g. July vs September) are regular recurring bills, NOT duplicates.
4. Never credit a line item that already has an APPLIED credit on record.
5. Provide a clear, professional explanation of your findings and the exact status of the customer's account balance.
"""

def create_billing_agent() -> adk.Agent:
    """Create and return the Google ADK Billing Resolution Agent."""
    return adk.Agent(
        name="billing_resolution",
        description="Prodapt Billing Resolution agent for auditing charges, checking duplicates, and applying credits.",
        instruction=BILLING_INSTRUCTION,
        model=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
        tools=[
            lookup_billing_account_tool,
            check_duplicate_charges_tool,
            apply_billing_credit_tool,
        ],
    )


# Initialize ADK Agent instance
agent = create_billing_agent()

# Create A2A Starlette ASGI Application for port 8002
app = to_a2a(agent, host="localhost", port=8002, protocol="http")


# ============================================================
# 3. INTERACTIVE CLI RUNNER (LIKE SQL_AGENT)
# ============================================================

def run_interactive_cli() -> None:
    """Run an interactive billing dispute CLI session for staff and testing."""
    print("\n" + "=" * 55)
    print("      PRODAPT BILLING RESOLUTION AGENT")
    print("=" * 55)
    print("Service: Billing Resolution (Google ADK / SQLite)")
    print("Target A2A Port: 8002")
    print("\nEnter a dispute or inquiry in plain English (or 'exit' to quit).")
    print("Example queries:")
    print("  - Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.")
    print("  - CUST-10027 Chris Dalton open duplicate International Day Pass.")
    print("  - CUST-10136 Sofia Alvarez was charged 60 dollars for a Japan Travel Pass. Is that a duplicate?")
    print("  - CUST-10172 Victor Almeida disputes 18.40 of Brazil data.")
    print("  - Lookup billing account for CUST-10008.")
    print("-" * 55)

    while True:
        try:
            query = input("\nBilling Query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q"}:
            print("Exiting Billing Resolution Agent.")
            break

        print("\nAuditing charges and processing billing dispute...")
        try:
            response = resolve_billing(query)
            print("\n" + "=" * 55)
            print("RESPONSE:")
            print("=" * 55)
            print(response)
        except Exception as err:
            print(f"\nERROR: {err}")


def run_server(host: str = "0.0.0.0", port: int = 8002) -> None:
    """Run the A2A HTTP microservice using uvicorn."""
    print(f"Starting Billing Resolution A2A service on {host}:{port}...")
    print(f"Agent Card will be available at: http://localhost:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prodapt Billing Resolution Agent")
    parser.add_argument("--server", action="store_true", help="Run as A2A HTTP microservice on port 8002")
    parser.add_argument("--port", type=int, default=8002, help="Port to listen on (default: 8002)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    if args.server:
        run_server(host=args.host, port=args.port)
    else:
        run_interactive_cli()
