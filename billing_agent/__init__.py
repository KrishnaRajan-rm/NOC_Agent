"""billing_agent — Google ADK Billing Resolution Agent for Prodapt AI Operations Center.

Implements Section 6.4 of the project specification:
1. Google ADK Agent exposing SQL-backed tools over A2A protocol (port 8002).
2. Billing audits and credits against telecom_ops.db (billing_accounts, billing_charges, billing_credits).
3. Enforces the $50 auto-approval threshold from billing_disputes_policy.txt.
4. Natural language dispute router resolve_billing(query).
"""

from .tools import (
    DATABASE_PATH,
    apply_billing_credit,
    check_duplicate_charges,
    get_connection,
    lookup_billing_account,
    resolve_billing,
)
from .agent import agent, app, create_billing_agent, run_server

__all__ = [
    "DATABASE_PATH",
    "get_connection",
    "lookup_billing_account",
    "check_duplicate_charges",
    "apply_billing_credit",
    "resolve_billing",
    "agent",
    "app",
    "create_billing_agent",
    "run_server",
]
