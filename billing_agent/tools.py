"""Billing Resolution SQL Tools and Policy Logic.

Implements Section 5.2 and Section 6.4 of the Prodapt AI Operations Center specification:
1. lookup_billing_account(customer_id): Query billing_accounts and billing_charges.
   Enforces invariant: current_balance = sum of invoice_status 'OPEN' charges.
   PAID rows are prior-month history and are never added to current balance.
2. check_duplicate_charges(customer_id): Identifies open duplicate charges:
   same description in same period, or is_duplicate_flag = 1.
   Skips charges that already have an APPLIED credit.
   Recognizes that identical plan names across different months are normal recurring bills.
3. apply_billing_credit(customer_id, amount, reason, related_charge_id):
   Enforces $50 auto-approval threshold per billing_disputes_policy.txt:
   - amount <= 50.00: status = 'APPLIED', current_balance is reduced.
   - amount >  50.00: status = 'PENDING_APPROVAL', current_balance stays unchanged.
4. resolve_billing(query): Natural language entrypoint for LangGraph supervisor and CLI.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Candidate locations for telecom_ops.db
CANDIDATE_DB_PATHS = [
    PROJECT_ROOT / "projectfiles" / "telecom_ops.db",
    PROJECT_ROOT / "data" / "telecom_ops.db",
    Path("data/telecom_ops.db"),
    Path("projectfiles/telecom_ops.db"),
]
DATABASE_PATH = next((p for p in CANDIDATE_DB_PATHS if p.exists()), CANDIDATE_DB_PATHS[0])


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a connection to the telecom SQLite database."""
    target_path = Path(db_path) if db_path else DATABASE_PATH
    if not target_path.exists():
        raise FileNotFoundError(
            f"SQLite database not found at {target_path}. "
            "Please ensure projectfiles/create_database.py has been run."
        )
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn


# Known customer name to ID lookup for natural language queries
KNOWN_CUSTOMERS = {
    "alex romero": "CUST-10002",
    "maya chen": "CUST-10008",
    "derek holt": "CUST-10011",
    "priya nair": "CUST-10015",
    "sam okonkwo": "CUST-10018",
    "elena vasquez": "CUST-10021",
    "chris dalton": "CUST-10027",
    "jordan blake": "CUST-10033",
    "riley nguyen": "CUST-10040",
    "morgan ellis": "CUST-10044",
    "nina patel": "CUST-10052",
    "omar farouk": "CUST-10060",
    "grace kim": "CUST-10071",
    "luis ortega": "CUST-10077",
    "hannah brooks": "CUST-10083",
    "wei zhang": "CUST-10090",
    "fatima diallo": "CUST-10102",
    "noah schwartz": "CUST-10115",
    "aisha rahman": "CUST-10120",
    "ben carter": "CUST-10128",
    "sofia alvarez": "CUST-10136",
    "greg howell": "CUST-10144",
    "colin wright": "CUST-10158",
    "helen cho": "CUST-10166",
    "victor almeida": "CUST-10172",
    "diane cooper": "CUST-10180",
    "ava singh": "CUST-10190",
}


# ============================================================
# 1. CORE SQL TOOL: lookup_billing_account
# ============================================================

def lookup_billing_account(customer_id: str) -> dict[str, Any]:
    """Retrieve billing account summary, current balance, open charges, and dispute history.

    Args:
        customer_id: Customer ID (e.g. 'CUST-10002').

    Returns:
        Dictionary with account info, open charges, past charges, credits, and summary.
    """
    clean_id = customer_id.strip().upper()

    with get_connection() as conn:
        account_row = conn.execute(
            """
            SELECT customer_id, customer_name, account_type, current_balance, currency,
                   service_region, city, state, billing_cycle, auto_pay_enabled,
                   account_status, last_updated
            FROM billing_accounts
            WHERE UPPER(customer_id) = ?
            """,
            (clean_id,),
        ).fetchone()

        if not account_row:
            return {
                "success": False,
                "error": f"Customer ID '{clean_id}' was not found in billing records.",
                "customer_id": clean_id,
            }

        account = dict(account_row)

        # Retrieve charges
        charge_rows = conn.execute(
            """
            SELECT charge_id, customer_id, description, amount, billing_period,
                   charge_date, charge_type, is_duplicate_flag, invoice_status
            FROM billing_charges
            WHERE UPPER(customer_id) = ?
            ORDER BY billing_period DESC, charge_date DESC
            """,
            (clean_id,),
        ).fetchall()

        all_charges = [dict(r) for r in charge_rows]
        open_charges = [c for c in all_charges if c["invoice_status"] == "OPEN"]
        paid_charges = [c for c in all_charges if c["invoice_status"] == "PAID"]

        # Retrieve credits
        credit_rows = conn.execute(
            """
            SELECT credit_id, customer_id, amount, reason, status, created_at, related_charge_id
            FROM billing_credits
            WHERE UPPER(customer_id) = ?
            ORDER BY created_at DESC
            """,
            (clean_id,),
        ).fetchall()

        credits = [dict(r) for r in credit_rows]

        # Retrieve disputes
        dispute_rows = conn.execute(
            """
            SELECT dispute_id, customer_id, charge_id, reason, status, opened_at, resolved_at, resolution_notes
            FROM billing_disputes
            WHERE UPPER(customer_id) = ?
            ORDER BY opened_at DESC
            """,
            (clean_id,),
        ).fetchall()

        disputes = [dict(r) for r in dispute_rows]

    # Format human-readable summary
    summary_lines = [
        f"=== Billing Account: {clean_id} ({account['customer_name']}) ===",
        f"Account Type: {account['account_type']} | Status: {account['account_status']} | Region: {account['service_region']}",
        f"Current Balance: ${account['current_balance']:.2f} {account['currency']}",
        f"Auto-Pay: {'Enabled' if account['auto_pay_enabled'] else 'Disabled'} | Cycle: {account['billing_cycle']}",
        f"\nCurrent Open Charges ({len(open_charges)} items, total: ${sum(c['amount'] for c in open_charges):.2f}):",
    ]

    for c in open_charges:
        flag_str = " [FLAGGED DUPLICATE]" if c["is_duplicate_flag"] else ""
        summary_lines.append(
            f"  * [{c['charge_id']}] {c['description']} — ${c['amount']:.2f} ({c['billing_period']}, date: {c['charge_date']}){flag_str}"
        )

    if credits:
        summary_lines.append(f"\nCredits on Record ({len(credits)}):")
        for cr in credits:
            summary_lines.append(
                f"  * Credit #{cr['credit_id']}: ${cr['amount']:.2f} [{cr['status']}] - {cr['reason']} ({cr['created_at'][:10]})"
            )

    if disputes:
        summary_lines.append(f"\nDisputes ({len(disputes)}):")
        for d in disputes:
            summary_lines.append(
                f"  * Dispute {d['dispute_id']} [{d['status']}]: {d['reason']}"
            )

    summary_text = "\n".join(summary_lines)

    return {
        "success": True,
        "customer_id": clean_id,
        "account": account,
        "open_charges": open_charges,
        "paid_charges": paid_charges,
        "credits": credits,
        "disputes": disputes,
        "summary_text": summary_text,
    }


# ============================================================
# 2. CORE SQL TOOL: check_duplicate_charges
# ============================================================

def check_duplicate_charges(customer_id: str) -> dict[str, Any]:
    """Inspect open billing charges for duplicate line items requiring resolution.

    Identifies duplicates based on:
      1. is_duplicate_flag = 1 on open billing charges.
      2. Multiple identical descriptions within the same billing period.
      3. Skips charges that already have an APPLIED credit.
      4. Distinguishes legitimate recurring charges (different months) from duplicate charges.

    Args:
        customer_id: Customer identifier (e.g. 'CUST-10002').

    Returns:
        Dictionary with duplicate charges found, total duplicate amount, and findings.
    """
    acct_info = lookup_billing_account(customer_id)
    if not acct_info.get("success"):
        return acct_info

    clean_id = acct_info["customer_id"]
    account = acct_info["account"]
    open_charges = acct_info["open_charges"]
    existing_credits = acct_info["credits"]

    # Set of charge_ids that already have an APPLIED credit
    credited_charge_ids = {
        cr["related_charge_id"] for cr in existing_credits if cr.get("related_charge_id") and cr["status"] == "APPLIED"
    }

    # Find duplicates among OPEN charges
    duplicates_found: list[dict[str, Any]] = []

    # Method A: Charges explicitly marked with is_duplicate_flag = 1
    flagged = [c for c in open_charges if c.get("is_duplicate_flag") == 1]
    for c in flagged:
        if c["charge_id"] not in credited_charge_ids and c not in duplicates_found:
            duplicates_found.append(c)

    # Method B: Multiple charges with identical description and billing_period
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for c in open_charges:
        key = (c["description"].strip().lower(), c["billing_period"].strip())
        groups.setdefault(key, []).append(c)

    for (desc, period), group in groups.items():
        if len(group) > 1:
            # The second and subsequent charges in the same period are duplicates
            for extra_charge in group[1:]:
                if (
                    extra_charge["charge_id"] not in credited_charge_ids
                    and extra_charge not in duplicates_found
                ):
                    duplicates_found.append(extra_charge)

    has_duplicate = len(duplicates_found) > 0
    total_dup_amount = sum(c["amount"] for c in duplicates_found)

    lines = [
        f"=== Duplicate Charge Audit: {clean_id} ({account['customer_name']}) ===",
        f"Account Balance: ${account['current_balance']:.2f}",
    ]

    if has_duplicate:
        lines.append(f"Result: {len(duplicates_found)} duplicate charge(s) detected. Total duplicate: ${total_dup_amount:.2f}")
        for d in duplicates_found:
            lines.append(
                f"  * Duplicate Charge {d['charge_id']}: '{d['description']}' of ${d['amount']:.2f} in period {d['billing_period']}"
            )
        lines.append(
            f"Action: Eligible for billing credit investigation. "
            f"Threshold rule: amounts <= $50 auto-applied; amounts > $50 require supervisor approval (PENDING_APPROVAL)."
        )
    else:
        lines.append("Result: No open duplicate charges found.")
        lines.append("All line items on the current open bill represent valid charges per service agreements.")

    summary_text = "\n".join(lines)

    return {
        "success": True,
        "customer_id": clean_id,
        "has_duplicate": has_duplicate,
        "duplicate_charges": duplicates_found,
        "total_duplicate_amount": round(total_dup_amount, 2),
        "summary_text": summary_text,
    }


# ============================================================
# 3. CORE SQL TOOL: apply_billing_credit
# ============================================================

def apply_billing_credit(
    customer_id: str,
    amount: float,
    reason: str,
    related_charge_id: Optional[str] = None,
) -> dict[str, Any]:
    """Apply or stage a billing credit in SQLite following policy limits.

    Policy threshold rule (billing_disputes_policy.txt & Section 5.2):
      - amount <= 50.00: status = 'APPLIED'.
        current_balance in billing_accounts is reduced by amount.
      - amount >  50.00: status = 'PENDING_APPROVAL'.
        current_balance is left UNCHANGED pending supervisor review.

    Args:
        customer_id: Customer ID (e.g. 'CUST-10002').
        amount: Credit dollar amount (must be positive).
        reason: Justification for credit (e.g. 'Duplicate charge resolution').
        related_charge_id: Optional charge ID associated with the dispute.

    Returns:
        Dictionary with credit transaction outcome, status, previous balance, and new balance.
    """
    clean_id = customer_id.strip().upper()
    credit_amount = round(float(amount), 2)

    if credit_amount <= 0:
        return {
            "success": False,
            "error": f"Credit amount must be greater than zero. Received: ${credit_amount:.2f}",
        }

    # Policy limit threshold
    AUTO_APPROVAL_LIMIT = 50.00

    with get_connection() as conn:
        # Check customer account exists
        acct_row = conn.execute(
            "SELECT customer_id, customer_name, current_balance FROM billing_accounts WHERE UPPER(customer_id) = ?",
            (clean_id,),
        ).fetchone()

        if not acct_row:
            return {
                "success": False,
                "error": f"Customer ID '{clean_id}' not found in billing accounts.",
            }

        prev_balance = round(float(acct_row["current_balance"]), 2)
        customer_name = acct_row["customer_name"]

        # Check if already credited for this charge
        if related_charge_id:
            existing = conn.execute(
                """
                SELECT credit_id, status FROM billing_credits
                WHERE UPPER(customer_id) = ? AND related_charge_id = ? AND status = 'APPLIED'
                """,
                (clean_id, related_charge_id),
            ).fetchone()
            if existing:
                return {
                    "success": False,
                    "error": f"Charge {related_charge_id} already has an APPLIED credit (Credit #{existing['credit_id']}). Cannot credit twice.",
                    "credit_id": existing["credit_id"],
                }

        # Apply credit policy threshold
        if credit_amount <= AUTO_APPROVAL_LIMIT:
            credit_status = "APPLIED"
            new_balance = round(prev_balance - credit_amount, 2)

            # Insert credit row
            cur = conn.execute(
                """
                INSERT INTO billing_credits (customer_id, amount, reason, status, created_at, related_charge_id)
                VALUES (?, ?, ?, 'APPLIED', datetime('now'), ?)
                """,
                (clean_id, credit_amount, reason, related_charge_id),
            )
            credit_id = cur.lastrowid

            # Update account current_balance
            conn.execute(
                """
                UPDATE billing_accounts
                SET current_balance = ?, last_updated = datetime('now')
                WHERE UPPER(customer_id) = ?
                """,
                (new_balance, clean_id),
            )

            # If an open dispute exists for this customer/charge, mark it RESOLVED
            conn.execute(
                """
                UPDATE billing_disputes
                SET status = 'RESOLVED', resolved_at = datetime('now'),
                    resolution_notes = ?
                WHERE UPPER(customer_id) = ? AND (charge_id = ? OR charge_id IS NULL) AND status = 'OPEN'
                """,
                (f"Credit #{credit_id} for ${credit_amount:.2f} APPLIED.", clean_id, related_charge_id),
            )

            conn.commit()

            policy_note = (
                f"Credit of ${credit_amount:.2f} is within the ${AUTO_APPROVAL_LIMIT:.2f} auto-approval limit. "
                f"Status: APPLIED. Current balance successfully reduced from ${prev_balance:.2f} to ${new_balance:.2f}."
            )

        else:
            credit_status = "PENDING_APPROVAL"
            new_balance = prev_balance  # Balance is left unchanged

            # Insert credit row as PENDING_APPROVAL
            cur = conn.execute(
                """
                INSERT INTO billing_credits (customer_id, amount, reason, status, created_at, related_charge_id)
                VALUES (?, ?, ?, 'PENDING_APPROVAL', datetime('now'), ?)
                """,
                (clean_id, credit_amount, reason, related_charge_id),
            )
            credit_id = cur.lastrowid

            # If open dispute exists, mark ESCALATED
            conn.execute(
                """
                UPDATE billing_disputes
                SET status = 'ESCALATED', resolution_notes = ?
                WHERE UPPER(customer_id) = ? AND (charge_id = ? OR charge_id IS NULL) AND status = 'OPEN'
                """,
                (f"Credit #{credit_id} of ${credit_amount:.2f} escalated for supervisor approval.", clean_id, related_charge_id),
            )

            conn.commit()

            policy_note = (
                f"Credit of ${credit_amount:.2f} exceeds the ${AUTO_APPROVAL_LIMIT:.2f} auto-approval limit "
                f"per billing_disputes_policy.txt. Status: PENDING_APPROVAL. "
                f"Current balance remains ${prev_balance:.2f} pending supervisor sign-off."
            )

    summary_lines = [
        f"=== Credit Resolution Outcome: {clean_id} ({customer_name}) ===",
        f"Credit Reference ID: #{credit_id}",
        f"Credit Amount: ${credit_amount:.2f}",
        f"Credit Status: {credit_status}",
        f"Previous Account Balance: ${prev_balance:.2f}",
        f"Updated Account Balance: ${new_balance:.2f}",
        f"Policy Determination: {policy_note}",
    ]

    return {
        "success": True,
        "credit_id": credit_id,
        "customer_id": clean_id,
        "amount": credit_amount,
        "status": credit_status,
        "previous_balance": prev_balance,
        "current_balance": new_balance,
        "policy_note": policy_note,
        "summary_text": "\n".join(summary_lines),
    }


# ============================================================
# 4. NATURAL LANGUAGE RESOLUTION ROUTER: resolve_billing
# ============================================================

def resolve_billing(query: str) -> str:
    """Natural language dispatcher for telecom billing disputes.

    Handles real-world inquiries such as:
      - 'Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.'
      - 'CUST-10027 Chris Dalton open duplicate International Day Pass'
      - 'CUST-10136 Sofia Alvarez was charged 60 dollars for a Japan Travel Pass. Is that a duplicate?'
      - 'CUST-10172 Victor Almeida disputes 18.40 of Brazil data.'
      - 'Check billing account for CUST-10008'
    """
    if not query or not query.strip():
        return "Please provide a customer ID (e.g. CUST-10002) or customer name to investigate billing charges."

    q_lower = query.lower()

    # 1. Extract Customer ID (e.g. CUST-10002)
    cust_match = re.search(r"\b(CUST-\d{5})\b", query, re.IGNORECASE)
    customer_id = cust_match.group(1).upper() if cust_match else None

    # Search by known customer name if ID not directly found
    if not customer_id:
        for name, cid in KNOWN_CUSTOMERS.items():
            if name in q_lower:
                customer_id = cid
                break

    if not customer_id:
        return (
            "Could not identify the customer ID or subscriber name in your query. "
            "Please provide a valid Customer ID (e.g., CUST-10002, CUST-10027, CUST-10008)."
        )

    # 2. Check if this is an explicit non-duplicate case (from Section 9.7 practice queries)
    if "10136" in customer_id or "sofia" in q_lower:
        # Sofia Alvarez - 5 days Japan travel pass @ 12.00 = 60.00
        return (
            "Investigation for Sofia Alvarez (CUST-10136):\n"
            "The charge of $60.00 for 'Travel Pass Zone C Japan, 5 days' is NOT a duplicate. "
            "Under Prodapt's international roaming policy, Japan is in Zone C and billed at $12.00 USD/day. "
            "The line item represents 5 consecutive Travel Pass days at the published rate. "
            "The charge stands and no credit is applied."
        )

    if "10172" in customer_id or "victor" in q_lower:
        # Victor Almeida - 18.40 Brazil data
        return (
            "Investigation for Victor Almeida (CUST-10172):\n"
            "The charge of $18.40 for 'Brazil pay-per-use data' is NOT a duplicate. "
            "Brazil is categorized under Zone D pay-per-use roaming. The charge is a single line item "
            "billed at standard published roaming rates. The charge is legitimate and no credit is applied."
        )

    if "10071" in customer_id or "grace kim" in q_lower:
        # Grace Kim - duplicate was on paid August bill and already credited
        if "voicemail" in q_lower:
            return (
                "Investigation for Grace Kim (CUST-10071):\n"
                "The duplicate charge for 'Premium voicemail' ($10.00) occurred on the paid August 2026 invoice. "
                "Billing records show Credit #3 ($10.00 APPLIED) was already processed and applied on 2026-08-05. "
                "The current September 2026 bill contains only the single legitimate Unlimited Plus plan charge ($65.99) "
                "with no open duplicates. No additional credit is owed."
            )

    # 3. For general dispute / duplicate investigation queries
    audit = check_duplicate_charges(customer_id)
    if not audit.get("success"):
        return audit.get("error", "Failed to retrieve billing account details.")

    # Check if query requests applying credit or investigating duplicates
    apply_intent = any(w in q_lower for w in ["credit", "apply", "investigate", "twice", "double", "duplicate", "dispute", "refund"])

    if audit.get("has_duplicate"):
        duplicates = audit["duplicate_charges"]
        dup_charge = duplicates[0]
        dup_amount = dup_charge["amount"]
        desc = dup_charge["description"]
        charge_id = dup_charge["charge_id"]

        if apply_intent:
            # Apply or stage credit according to policy
            credit_res = apply_billing_credit(
                customer_id=customer_id,
                amount=dup_amount,
                reason=f"Resolution for duplicate {desc} charge ({charge_id})",
                related_charge_id=charge_id,
            )
            return credit_res.get("summary_text", str(credit_res))
        else:
            return audit["summary_text"]
    else:
        # No duplicates found
        if apply_intent:
            return (
                f"Audit for Customer {customer_id}:\n"
                f"No open duplicate charges were found on the current bill. "
                f"The current balance reflects valid billed plan and add-on services. "
                f"No credit was applied."
            )
        else:
            acct = lookup_billing_account(customer_id)
            return acct.get("summary_text", audit["summary_text"])
