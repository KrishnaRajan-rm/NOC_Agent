"""LangGraph multi-agent supervisor orchestration graph.

Implements Section 6.7, 6.8.4, 8.1, 8.2, and Section 9 (Scenarios 1-5) of the project specification:
1. Supervisor node routing requests based on intent and accumulated execution trace.
2. Worker nodes:
   - PolicyRAG (ChromaDB Document RAG via rag module)
   - NetworkAnalytics (SQLite Semantic SQL via sql_agent module)
   - NetworkDiagnosticsADK (Google ADK A2A client)
   - BillingResolutionADK (Google ADK A2A client)
   - CustomerCommsCrew (CrewAI Communications + Quality Reviewer)
3. Cyclic graph with worker-to-supervisor returns and FINISH conditional edge to END.
4. Exported run_telecom_assistant(user_query: str) -> dict contract for Streamlit UI.
"""

from __future__ import annotations

import os
import re
import sys
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Literal

warnings.filterwarnings("ignore", category=UserWarning)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from orchestration.state import AgentState, WorkerNode
from orchestration.adk_remote_client import (
    query_billing_resolution_remote,
    query_network_diagnostics_remote,
)
from orchestration.crew_nodes import run_customer_comms_crew
from rag.query import get_collection
from rag.llm import rag_query
from sql_agent.semantic_search import ask_sql

logger = logging.getLogger(__name__)

_rag_collection = None

def ask_policy(user_query: str) -> str:
    """Query policy documents using the project's ChromaDB RAG module."""
    global _rag_collection
    try:
        if _rag_collection is None:
            _rag_collection = get_collection()
        answer, _ = rag_query(_rag_collection, user_query)
        return answer
    except Exception as exc:
        logger.error(f"Policy RAG execution error: {exc}")
        return f"Policy RAG could not retrieve documents: {exc}"



# ============================================================
# 1. SUPERVISOR ROUTING LOGIC (SECTION 9.6 MATRIX)
# ============================================================

def classify_intent(query: str, executed_workers: set[str]) -> WorkerNode:
    """Evaluate customer query and state to determine next worker node.

    Follows Section 9.6 Supervisor Routing Decision Matrix and Scenarios 1-5.
    """
    q_lower = query.lower()

    # If CustomerCommsCrew has already completed, end the graph
    if "CustomerCommsCrew" in executed_workers:
        return "FINISH"

    # ---------------------------------------------------------
    # Scenario 5: Combined Multi-Worker Flow (Outage Facts + SLA Policy)
    # e.g., "We had a 6-hour outage in the Midwest. Am I eligible for an SLA credit and what does policy say?"
    # ---------------------------------------------------------
    is_sla_or_policy = any(k in q_lower for k in ["sla", "credit", "policy", "eligible", "eligibility"])
    is_outage_fact = any(k in q_lower for k in ["outage", "6-hour", "6 hour", "midwest", "duration", "hours"])

    if is_sla_or_policy and is_outage_fact:
        if "NetworkAnalytics" not in executed_workers:
            return "NetworkAnalytics"
        if "PolicyRAG" not in executed_workers:
            return "PolicyRAG"
        return "CustomerCommsCrew"

    # ---------------------------------------------------------
    # Scenario 4 & Billing Inquiries: BillingResolutionADK
    # Signals: CUST- prefix, charged twice, double-charge, dispute, balance, credit, plan fee
    # ---------------------------------------------------------
    is_cust_id = bool(re.search(r"\b(?:cust|customer|acct|account)?[-_\s#:]*\d{5}\b", q_lower))
    is_pure_policy = any(p in q_lower for p in ["policy", "faq", "terms", "rules", "guidelines", "handbook"]) and not is_cust_id and not any(w in q_lower for w in ["alex romero", "investigate", "apply credit", "twice", "charged twice", "duplicate", "dispute"])
    billing_signals = [
        "charge", "charged", "bill", "billing", "dispute", "duplicate",
        "twice", "double", "credit", "balance", "travel pass zone c",
        "alex romero", "maya chen", "derek holt", "chris dalton",
        "sofia alvarez", "victor almeida", "grace kim", "ben carter",
    ]
    if (is_cust_id or any(s in q_lower for s in billing_signals)) and not is_outage_fact and not is_pure_policy:
        if "BillingResolutionADK" not in executed_workers:
            return "BillingResolutionADK"
        return "CustomerCommsCrew"

    # ---------------------------------------------------------
    # Scenario 3 & Network Diagnostics: NetworkDiagnosticsADK
    # Signals: tower ID (e.g. TX-512, FL-090, TX-208), diagnose, drops, signal, dBm, OFFLINE, INC-
    # ---------------------------------------------------------
    has_tower_id = bool(re.search(r"\b[a-z]{2}-\d{3}\b", q_lower))
    has_incident_id = bool(re.search(r"\binc-\d{4}\b", q_lower))
    diagnostic_signals = [
        "drop", "dropping", "diagnos", "tower", "symptom", "packet loss right now",
        "latency", "rf", "telemetry", "offline", "site down", "kpi",
    ]
    # Distinguish specific tower diagnostic from general SQL ranking
    is_ranking = any(w in q_lower for w in ["highest", "worst", "top", "rank", "count", "which region", "how many"])
    if (has_tower_id or has_incident_id or (any(s in q_lower for s in diagnostic_signals) and not is_ranking)):
        if "NetworkDiagnosticsADK" not in executed_workers:
            return "NetworkDiagnosticsADK"
        return "CustomerCommsCrew"

    # ---------------------------------------------------------
    # Scenario 2 & Network Analytics from SQL: NetworkAnalytics
    # Signals: outage trends, packet loss ranking, critical outages, which region, how many
    # ---------------------------------------------------------
    analytics_signals = [
        "critical outage", "outages", "outage count", "which region", "highest packet loss",
        "how many towers", "longest outage", "how long was", "affected customers", "root cause",
        "analytics", "trends",
    ]
    if any(s in q_lower for s in analytics_signals) or is_ranking or is_outage_fact:
        if "NetworkAnalytics" not in executed_workers:
            return "NetworkAnalytics"
        return "CustomerCommsCrew"

    # ---------------------------------------------------------
    # Scenario 1 & Policy / FAQ: PolicyRAG
    # Signals: roaming, international, trade-in, iphone 13, 5g indoor, upgrade, policy, terms
    # ---------------------------------------------------------
    policy_signals = [
        "roaming", "japan", "europe", "uk", "france", "germany", "travel pass",
        "spend cap", "zone a", "zone b", "zone c", "zone d", "iphone 13", "upgrade",
        "trade in", "trade-in", "installment", "5g indoor", "slow indoor", "faq",
        "rules", "procedure",
    ]
    if any(s in q_lower for s in policy_signals) or "policy" in q_lower:
        if "PolicyRAG" not in executed_workers:
            return "PolicyRAG"
        return "CustomerCommsCrew"

    # Default fallback
    if not executed_workers:
        return "PolicyRAG"
    return "CustomerCommsCrew"


# ============================================================
# 2. LANGGRAPH NODES
# ============================================================

def supervisor_node(state: AgentState) -> dict:
    """Supervisor router node: determines the next worker node or FINISH."""
    user_query = state.get("user_query", "")
    trace = state.get("execution_trace", [])
    executed_workers = {t["worker"] for t in trace}

    decision = classify_intent(user_query, executed_workers)

    return {
        "next": decision,
    }


def policy_rag_node(state: AgentState) -> dict:
    """Worker node: Queries policy documents using LlamaIndex VectorStoreIndex."""
    user_query = state.get("user_query", "")
    logger.info("Executing PolicyRAG worker...")

    result_text = ask_policy(user_query)

    curr_ctx = state.get("agent_context", "")
    new_ctx = f"{curr_ctx}\n\n[PolicyRAG Findings]:\n{result_text}".strip()

    trace_entry = {
        "worker": "PolicyRAG",
        "output": result_text,
    }

    return {
        "agent_context": new_ctx,
        "execution_trace": state.get("execution_trace", []) + [trace_entry],
        "messages": [AIMessage(content=f"[PolicyRAG]: {result_text}")],
    }


def network_analytics_node(state: AgentState) -> dict:
    """Worker node: Queries telecom database using LlamaIndex Semantic SQL."""
    user_query = state.get("user_query", "")
    logger.info("Executing NetworkAnalytics worker...")

    result_text = ask_sql(user_query)

    curr_ctx = state.get("agent_context", "")
    new_ctx = f"{curr_ctx}\n\n[NetworkAnalytics Findings]:\n{result_text}".strip()

    trace_entry = {
        "worker": "NetworkAnalytics",
        "output": result_text,
    }

    return {
        "agent_context": new_ctx,
        "execution_trace": state.get("execution_trace", []) + [trace_entry],
        "messages": [AIMessage(content=f"[NetworkAnalytics]: {result_text}")],
    }


def network_diagnostics_adk_node(state: AgentState) -> dict:
    """Worker node: Queries Google ADK Network Diagnostics service (Port 8001)."""
    user_query = state.get("user_query", "")
    logger.info("Executing NetworkDiagnosticsADK worker...")

    result_text = query_network_diagnostics_remote(user_query)

    curr_ctx = state.get("agent_context", "")
    new_ctx = f"{curr_ctx}\n\n[NetworkDiagnosticsADK Findings]:\n{result_text}".strip()

    trace_entry = {
        "worker": "NetworkDiagnosticsADK",
        "output": result_text,
    }

    return {
        "agent_context": new_ctx,
        "execution_trace": state.get("execution_trace", []) + [trace_entry],
        "messages": [AIMessage(content=f"[NetworkDiagnosticsADK]: {result_text}")],
    }


def billing_resolution_adk_node(state: AgentState) -> dict:
    """Worker node: Queries Google ADK Billing Resolution service (Port 8002)."""
    user_query = state.get("user_query", "")
    logger.info("Executing BillingResolutionADK worker...")

    result_text = query_billing_resolution_remote(user_query)

    curr_ctx = state.get("agent_context", "")
    new_ctx = f"{curr_ctx}\n\n[BillingResolutionADK Findings]:\n{result_text}".strip()

    trace_entry = {
        "worker": "BillingResolutionADK",
        "output": result_text,
    }

    return {
        "agent_context": new_ctx,
        "execution_trace": state.get("execution_trace", []) + [trace_entry],
        "messages": [AIMessage(content=f"[BillingResolutionADK]: {result_text}")],
    }


def customer_comms_crew_node(state: AgentState) -> dict:
    """Worker node: Runs CrewAI communications specialist and quality reviewer."""
    user_query = state.get("user_query", "")
    agent_context = state.get("agent_context", "")
    logger.info("Executing CustomerCommsCrew worker...")

    pii_audit: dict[str, str] = {}
    final_text = run_customer_comms_crew(
        user_query=user_query,
        agent_context=agent_context,
        pii_audit=pii_audit,
    )

    trace_entry = {
        "worker": "CustomerCommsCrew",
        "output": final_text,
    }
    trace_entries = state.get("execution_trace", []) + [trace_entry]
    if pii_audit.get("output"):
        trace_entries.append({
            "worker": "PIILayer",
            "output": pii_audit["output"],
        })

    return {
        "final_response": final_text,
        "execution_trace": trace_entries,
        "messages": [AIMessage(content=f"[CustomerCommsCrew]: {final_text}")],
    }


# ============================================================
# 3. GRAPH CONSTRUCTION
# ============================================================

def build_telecom_graph() -> StateGraph:
    """Construct and compile the supervisor state graph."""
    builder = StateGraph(AgentState)

    # Add all nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("policy_rag", policy_rag_node)
    builder.add_node("network_analytics", network_analytics_node)
    builder.add_node("network_diagnostics_adk", network_diagnostics_adk_node)
    builder.add_node("billing_resolution_adk", billing_resolution_adk_node)
    builder.add_node("customer_comms_crew", customer_comms_crew_node)

    # Edge from START to supervisor
    builder.add_edge(START, "supervisor")

    # Conditional router from supervisor
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "PolicyRAG": "policy_rag",
            "NetworkAnalytics": "network_analytics",
            "NetworkDiagnosticsADK": "network_diagnostics_adk",
            "BillingResolutionADK": "billing_resolution_adk",
            "CustomerCommsCrew": "customer_comms_crew",
            "FINISH": END,
        },
    )

    # All workers loop back to the supervisor (Section 8.2 Supervisor Loop)
    builder.add_edge("policy_rag", "supervisor")
    builder.add_edge("network_analytics", "supervisor")
    builder.add_edge("network_diagnostics_adk", "supervisor")
    builder.add_edge("billing_resolution_adk", "supervisor")
    builder.add_edge("customer_comms_crew", "supervisor")

    return builder.compile()


# Compile the graph singleton
telecom_graph = build_telecom_graph()


# ============================================================
# 4. PUBLIC ENTRYPOINT (DATA CONTRACT FOR STREAMLIT / CALLERS)
# ============================================================

def run_telecom_assistant(user_query: str) -> dict[str, Any]:
    """Execute the full multi-agent orchestration on a customer query.

    Returns dictionary matching Section 6.8.4 Data Contract:
      - final_response: str
      - execution_trace: list[dict] where each item is {"worker": "<name>", "output": "<truncated text>"}
      - agent_context: str
    """
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_query)],
        "next": "",
        "user_query": user_query,
        "agent_context": "",
        "execution_trace": [],
        "final_response": "",
    }

    try:
        final_state = telecom_graph.invoke(initial_state)

        final_response = final_state.get("final_response")
        if not final_response:
            # Fallback to agent context if final_response was not populated
            final_response = final_state.get("agent_context", "Inquiry processed successfully.")

        return {
            "final_response": final_response,
            "execution_trace": final_state.get("execution_trace", []),
            "agent_context": final_state.get("agent_context", ""),
        }
    except Exception as exc:
        logger.error(f"Error executing telecom assistant: {exc}", exc_info=True)
        return {
            "final_response": f"An error occurred while processing your request: {exc}",
            "execution_trace": [{"worker": "Error", "output": str(exc)}],
            "agent_context": str(exc),
        }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING TELECOM ASSISTANT ORCHESTRATION")
    print("=" * 60)

    test_queries = [
        "What is Prodapt's roaming policy for Western Europe?",
        "Which region had the most CRITICAL network outages recently?",
        "My 5G keeps dropping in Austin near tower TX-512. Please diagnose.",
        "Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.",
        "We had a 6-hour outage in the Midwest. Am I eligible for an SLA credit and what does policy say?",
    ]

    for q in test_queries:
        print(f"\nUser Query: {q}")
        res = run_telecom_assistant(q)
        print("Execution Trace:")
        for step_num, step in enumerate(res["execution_trace"], 1):
            print(f"  Step {step_num}: {step['worker']} -> {step['output'][:100]}...")
        print(f"Final Response ({len(res['final_response'])} chars):\n{res['final_response'][:200]}...")
        print("-" * 60)
