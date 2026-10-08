"""Deterministic Confidence Scoring and Financial Grounding Judge Check.

Implements real-signal confidence scoring and financial hallucination judge checks:
1. Score is derived from REAL SIGNALS (retrieval cosine similarity from ChromaDB,
   whether SQLite queries returned rows, and grounding entity verification),
   rather than numbers fabricated by an LLM.
2. Low confidence score (< 70%) or failed judge check triggers "Needs Human Review".
3. The Judge Check deterministically catches any dollar amount in the final customer
   letter that is not present in the retrieved operational data or customer inquiry.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def extract_dollar_amounts(text: str) -> list[str]:
    """Extract all formatted dollar amounts from text (e.g. ['$65.99', '$131.98', '$50'])."""
    if not text:
        return []
    # Matches patterns like $65.99, $131, $1,250.50, $0.00, etc.
    pattern = r"\$\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
    matches = re.findall(pattern, text)
    return [m.replace(" ", "") for m in matches]


def normalize_dollar_value(val_str: str) -> float:
    """Normalize a dollar amount string to a round float (e.g. '$65.99' -> 65.99)."""
    cleaned = val_str.replace("$", "").replace(",", "").strip()
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def run_judge_check(
    final_response: str,
    retrieved_data: str,
    user_query: str = "",
) -> dict[str, Any]:
    """Catches any dollar amount in the final letter that is not in the retrieved data.

    Deterministic fact-checking judge guardrail:
    - Extracts all dollar amounts from the final customer communication.
    - Extracts all dollar amounts from the retrieved operational context & original query.
    - Verifies that every single dollar amount in the response is grounded in the retrieved data.
    - If any dollar amount in the final response is missing from the retrieved data, flags hallucination.
    """
    response_amounts = extract_dollar_amounts(final_response)
    grounding_corpus = f"{retrieved_data}\n{user_query}"
    retrieved_amounts = extract_dollar_amounts(grounding_corpus)

    # Normalized float sets for value equivalence (e.g. $50 == $50.00)
    retrieved_values = {normalize_dollar_value(a) for a in retrieved_amounts}

    unverified_amounts: list[str] = []
    matched_amounts: list[str] = []

    for amt in response_amounts:
        val = normalize_dollar_value(amt)
        if val in retrieved_values:
            matched_amounts.append(amt)
        else:
            unverified_amounts.append(amt)

    passed = len(unverified_amounts) == 0

    if not response_amounts:
        details = "No financial figures present in customer letter; grounding check passed."
    elif passed:
        unique_matched = sorted(list(set(matched_amounts)))
        details = (
            f"All financial figures ({', '.join(unique_matched)}) verified "
            f"against retrieved database records."
        )
    else:
        unique_unverified = sorted(list(set(unverified_amounts)))
        details = (
            f"Hallucination detected: Dollar amount(s) {', '.join(unique_unverified)} in customer letter "
            f"were NOT found in retrieved operational data. Flagged for human review."
        )

    return {
        "passed": passed,
        "response_amounts": list(set(response_amounts)),
        "retrieved_amounts": list(set(retrieved_amounts)),
        "matched_amounts": list(set(matched_amounts)),
        "unverified_amounts": list(set(unverified_amounts)),
        "details": details,
    }


def evaluate_query_confidence(
    user_query: str,
    execution_trace: list[dict[str, Any]],
    agent_context: str,
    final_response: str,
) -> dict[str, Any]:
    """Calculate deterministic confidence score from real signals plus judge check.

    Real signals:
    1. Retrieval similarity (from ChromaDB distance if PolicyRAG ran).
    2. SQL returned rows (whether SQLite queries found matching records or returned 0 rows).
    3. Operational grounding (tower IDs, incident tickets, customer accounts verified).
    4. Judge check (financial figures in final letter grounded in retrieved context).

    A low score (< 0.70) or failed judge check triggers 'Needs Human Review'.
    """
    # 1. Run Judge Check on financial amounts
    judge = run_judge_check(
        final_response=final_response,
        retrieved_data=agent_context,
        user_query=user_query,
    )

    # 2. Extract real signals from execution trace
    workers_run = [step.get("worker", "") for step in execution_trace]

    retrieval_similarity: Optional[float] = None
    sql_rows_signal: Optional[float] = None
    sql_records_found = 0
    review_reasons: list[str] = []

    # Check PolicyRAG real signals
    rag_steps = [s for s in execution_trace if s.get("worker") == "PolicyRAG"]
    if rag_steps:
        meta = rag_steps[0].get("metadata", {})
        top_dist = meta.get("top_distance")
        chunks_count = meta.get("chunks_count", 0)

        if top_dist is not None:
            # ChromaDB cosine distance d in [0, 2]; similarity = 1 - d/2
            similarity = max(0.0, min(1.0, 1.0 - (float(top_dist) / 2.0)))
            retrieval_similarity = round(similarity, 3)
        elif chunks_count > 0:
            retrieval_similarity = 0.85
        else:
            # Check if output contains policy error or no docs
            rag_output = rag_steps[0].get("output", "").lower()
            if "could not retrieve" in rag_output or "error" in rag_output:
                retrieval_similarity = 0.25
                review_reasons.append("Policy document retrieval error")
            else:
                retrieval_similarity = 0.75

        if retrieval_similarity is not None and retrieval_similarity < 0.60:
            review_reasons.append(f"Low semantic retrieval similarity ({int(retrieval_similarity * 100)}%)")

    # Check SQL / Diagnostics / Billing real signals
    sql_workers = {"NetworkAnalytics", "NetworkDiagnosticsADK", "BillingResolutionADK"}
    sql_steps = [s for s in execution_trace if s.get("worker") in sql_workers]

    if sql_steps:
        total_steps = len(sql_steps)
        positive_steps = 0

        for step in sql_steps:
            output = step.get("output", "")
            meta = step.get("metadata", {})
            out_lower = output.lower()

            # Check if SQL returned 0 rows / not found
            is_not_found = (
                "was not found" in out_lower
                or "not found" in out_lower
                or "no account found" in out_lower
                or "0 rows" in out_lower
                or "no results found" in out_lower
                or out_lower.startswith("error:")
            )

            has_rows_explicit = meta.get("sql_rows_returned")
            if has_rows_explicit is False or is_not_found:
                review_reasons.append(f"{step.get('worker')} query returned 0 rows / record not found in database")
            else:
                positive_steps += 1
                sql_records_found += 1

        sql_rows_signal = round(positive_steps / total_steps, 2) if total_steps > 0 else 0.0

    # 3. Grounding & Identity Verification Signal
    grounding_score = 0.90
    q_lower = user_query.lower()

    # Check if specific entities mentioned in query were grounded in context
    cust_id_match = re.search(r"\bCUST-\d{5}\b", user_query, re.IGNORECASE)
    tower_id_match = re.search(r"\b(?!CU)[A-Z]{2}-\d{3}\b", user_query)

    if cust_id_match:
        cid = cust_id_match.group(0).upper()
        if (cid in agent_context or "<PII_ENCRYPTED_CUSTOMER_ID" in agent_context) and "not found" not in agent_context.lower():
            grounding_score = max(grounding_score, 0.95)
        else:
            grounding_score = 0.35
            review_reasons.append(f"Customer ID {cid} could not be verified in database records")

    if tower_id_match:
        tid = tower_id_match.group(0).upper()
        if tid in agent_context and "not found" not in agent_context.lower():
            grounding_score = max(grounding_score, 0.95)
        else:
            grounding_score = 0.35
            review_reasons.append(f"Tower ID {tid} could not be verified in database records")

    # 4. Compute composite confidence score based on route type
    has_rag = retrieval_similarity is not None
    has_sql = sql_rows_signal is not None

    if has_rag and has_sql:
        # Multi-agent hybrid flow (e.g. Scenario 5: Outage SQL + SLA Policy RAG)
        raw_score = (
            0.45 * (sql_rows_signal if sql_rows_signal is not None else 0.5)
            + 0.45 * (retrieval_similarity if retrieval_similarity is not None else 0.5)
            + 0.10 * grounding_score
        )
        grounding_type = "Multi-Agent Hybrid (SQL Telemetry + Policy RAG)"
    elif has_sql:
        # Relational SQL / ADK flow (Scenarios 2, 3, 4)
        raw_score = (
            0.65 * (sql_rows_signal if sql_rows_signal is not None else 0.5)
            + 0.35 * grounding_score
        )
        grounding_type = "Relational SQL Grounding (telecom_ops.db)"
    elif has_rag:
        # Document RAG flow (Scenario 1)
        raw_score = (
            0.75 * (retrieval_similarity if retrieval_similarity is not None else 0.5)
            + 0.25 * grounding_score
        )
        grounding_type = "ChromaDB Document Vector Store (Policy Documents)"
    else:
        raw_score = 0.50
        grounding_type = "General System Telemetry"

    # 5. Apply Judge Check Impact
    # If the judge check caught an unverified dollar amount, enforce a severe penalty
    if not judge["passed"]:
        raw_score = min(raw_score * 0.45, 0.42)
        review_reasons.append(
            f"Judge Check FAILED: Unverified dollar amount(s) {', '.join(judge['unverified_amounts'])} in final response"
        )

    # If SQL returned 0 rows, ensure score is below threshold
    if sql_rows_signal is not None and sql_rows_signal < 0.5:
        raw_score = min(raw_score, 0.48)

    confidence_score = round(max(0.05, min(0.99, raw_score)), 2)
    confidence_percent = int(confidence_score * 100)

    # 6. Determine threshold & human review status
    CONFIDENCE_THRESHOLD = 0.70
    needs_human_review = (confidence_score < CONFIDENCE_THRESHOLD) or (not judge["passed"])

    if confidence_score >= 0.85:
        confidence_level = "HIGH"
    elif confidence_score >= 0.70:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    if needs_human_review:
        confidence_status = "Needs Human Review"
    else:
        confidence_status = "Autonomous Resolution Approved"

    return {
        "confidence_score": confidence_score,
        "confidence_percent": confidence_percent,
        "confidence_level": confidence_level,
        "confidence_status": confidence_status,
        "needs_human_review": needs_human_review,
        "review_reasons": review_reasons,
        "grounding_type": grounding_type,
        "signals": {
            "retrieval_similarity": retrieval_similarity,
            "retrieval_similarity_pct": int(retrieval_similarity * 100) if retrieval_similarity is not None else None,
            "sql_rows_signal": sql_rows_signal,
            "sql_rows_returned": (sql_rows_signal is not None and sql_rows_signal >= 0.5),
            "sql_records_found": sql_records_found,
            "grounding_score": round(grounding_score, 2),
            "judge_passed": judge["passed"],
        },
        "judge_check": judge,
    }
