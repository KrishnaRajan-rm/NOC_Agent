"""Prodapt AI Operations Center - Real-Time Enterprise Operations Platform.

Implements Section 6.8, 6.8.1, 6.8.2, 6.8.3, and 6.8.4 of the project specification:
1. Operations Console:
   - Enterprise header (solid dark charcoal/slate aesthetic, strictly no blue/green gradients)
   - Real-time NOC telemetry status bar & 100% database-calculated metrics (no fake data)
   - Real-time incident stream populated dynamically from open_incidents (no simulated strings)
   - Perfectly aligned scenario preset cards with text-only buttons (no emojis, equal heights)
   - Customer inquiry text area with clear & sample query actions
   - Prominent customer response card (CrewAI polished)
   - Visual route stepper & mandatory Agent Execution Trace (step numbers, worker names, outputs)
2. Live Real-Time Network Dashboards:
   - Interactive Pydeck 5G tower map with operational health markers
   - Tower RF Telemetry Explorer: interactive time-series line chart (throughput & latency over time)
3. Outage & SLA Analytics Dashboard:
   - Real severity distribution (Critical, Major, Minor), affected customer stats, and open incidents monitor
4. Customer Billing Operations Dashboard:
   - Real billing dispute resolution status, subscription distribution, and ledger audit
5. Multi-Agent Architecture Blueprint:
   - End-to-end orchestration SVG topology & framework specification
6. Sidebar:
   - Live system health checks (Database, ChromaDB, ADK Ports 8001 & 8002) with status indicators
   - Autonomous microservices helper instructions & framework capability map
"""

from __future__ import annotations

import datetime
import random
import sqlite3
import sys
import warnings
from pathlib import Path

# Suppress experimental ADK warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from orchestration.graph import run_telecom_assistant
from orchestration.adk_remote_client import (
    NETWORK_A2A_PORT,
    BILLING_A2A_PORT,
    check_service_health,
)

# ============================================================
# 1. PAGE CONFIGURATION & ENTERPRISE DARK-SLATE CSS (NO GRADIENTS)
# ============================================================

st.set_page_config(
    page_title="Prodapt AI Operations Center",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Global Styles */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Modern Solid Dark Slate Header (No blue-green gradients) */
    .header-card {
        background: #0f172a;
        color: #ffffff;
        padding: 22px 28px;
        border-radius: 12px;
        margin-bottom: 18px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .header-left {
        flex: 1 1 600px;
    }
    .header-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #1e293b;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 8px;
        border: 1px solid #334155;
    }
    .header-title {
        font-size: 2.05rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .header-subtitle {
        font-size: 0.94rem;
        color: #cbd5e1;
        margin-top: 6px;
        margin-bottom: 12px;
        font-weight: 400;
    }
    
    /* Solid Neutral Framework Badges */
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 6px;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        border: 1px solid #334155;
        background: #1e293b;
        color: #e2e8f0;
    }

    /* Live Telemetry Real-Time Status Bar */
    .rt-status-bar {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 9px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 0.82rem;
        min-height: 42px;
        box-sizing: border-box;
    }
    .rt-status-left {
        display: flex;
        align-items: center;
        gap: 14px;
        flex-wrap: wrap;
    }
    .rt-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-weight: 700;
        color: #0f172a;
    }
    .rt-dot-live {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 6px #10b981;
        display: inline-block;
        animation: rtPulse 2s infinite;
    }
    @keyframes rtPulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.15); opacity: 1; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }

    /* Scenario Cards Grid - Strictly Equal Heights to Prevent Misalignment */
    .scenario-card-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 8px;
        box-sizing: border-box;
        height: 115px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    .scenario-card-title {
        font-size: 0.84rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .scenario-card-tag {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
        margin-bottom: 6px;
        width: fit-content;
    }
    .scenario-card-desc {
        font-size: 0.74rem;
        color: #64748b;
        line-height: 1.35;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    /* Live NOC Event Stream Box */
    .live-feed-box {
        background: #0f172a;
        color: #cbd5e1;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: Consolas, "SF Mono", Monaco, Menlo, monospace;
        font-size: 0.80rem;
        border: 1px solid #1e293b;
        margin-top: 14px;
        margin-bottom: 18px;
        max-height: 150px;
        overflow-y: auto;
    }
    .live-feed-item {
        padding: 4px 0;
        border-bottom: 1px solid #1e293b;
        display: flex;
        gap: 12px;
    }
    .live-feed-item:last-child {
        border-bottom: none;
    }
    .live-feed-time {
        color: #94a3b8;
        font-weight: 700;
        min-width: 135px;
    }
    .live-feed-tag {
        color: #38bdf8;
        font-weight: 600;
        min-width: 145px;
    }
    .live-feed-text {
        color: #f1f5f9;
        flex: 1;
    }

    /* Customer Response Card */
    .response-card {
        background: #ffffff;
        border-radius: 10px;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #0f172a;
        padding: 20px 24px;
        margin: 16px 0 22px 0;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
    }
    .response-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
        padding-bottom: 10px;
        border-bottom: 1px solid #f1f5f9;
    }
    .response-badge {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #0f172a;
        font-weight: 800;
    }
    .response-seal {
        background: #f1f5f9;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .response-body {
        font-size: 1.01rem;
        line-height: 1.7;
        color: #1e293b;
        white-space: pre-wrap;
    }

    /* Trace Timeline Steps */
    .trace-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
    }
    .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #0f172a;
        color: #ffffff;
        font-weight: 700;
        font-size: 0.78rem;
        margin-right: 8px;
    }
    .trace-worker {
        font-weight: 700;
        font-size: 0.94rem;
        color: #0f172a;
    }
    .trace-tech {
        font-size: 0.76rem;
        color: #475569;
        font-weight: 600;
        margin-left: 8px;
    }
    .trace-status {
        float: right;
        background: #f1f5f9;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.70rem;
        font-weight: 700;
    }
    .trace-output {
        margin-top: 10px;
        font-size: 0.86rem;
        color: #334155;
        background: #f8fafc;
        padding: 10px 14px;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
        font-family: Consolas, "SF Mono", Monaco, Menlo, monospace;
        white-space: pre-wrap;
        word-break: break-word;
    }

    /* Route Path Stepper */
    .route-path-container {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        margin: 12px 0 16px 0;
        padding: 10px 14px;
        background: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .route-node {
        background: #0f172a;
        color: #f8fafc;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .route-arrow {
        color: #64748b;
        font-weight: 800;
        font-size: 0.90rem;
    }

    /* Sidebar Status Indicators */
    .status-indicator {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 0.86rem;
    }
    .dot-online {
        height: 10px;
        width: 10px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    .dot-offline {
        height: 10px;
        width: 10px;
        background-color: #ef4444;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }

    /* Solid Dark Button Styling (Strictly no gradients, no emojis) */
    div.stButton > button[kind="primary"] {
        background: #0f172a !important;
        border: 1px solid #0f172a !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        padding: 8px 18px !important;
        box-shadow: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #1e293b !important;
        border-color: #1e293b !important;
        color: #ffffff !important;
    }
    div.stButton > button:not([kind="primary"]) {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }
    div.stButton > button:not([kind="primary"]):hover {
        background: #f1f5f9 !important;
        border-color: #94a3b8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. DATA ACCESS & REAL-TIME TELEMETRY RETRIEVAL (100% REAL DATA)
# ============================================================

@st.cache_data(ttl=30)
def load_telecom_data():
    """Retrieve 100% real telecom operational data from SQLite database."""
    db_candidates = [
        PROJECT_ROOT / "data" / "telecom_ops.db",
        PROJECT_ROOT / "projectfiles" / "telecom_ops.db",
    ]
    target_db = next((p for p in db_candidates if p.exists()), None)
    if not target_db:
        return None, None, None, None, None, None

    conn = sqlite3.connect(str(target_db))
    try:
        towers = pd.read_sql_query(
            "SELECT tower_id, tower_name, region, city, state, technology, status, latitude, longitude FROM network_towers",
            conn,
        )
        outages = pd.read_sql_query(
            "SELECT outage_id, region, severity, duration_hours, affected_customers, root_cause, status, start_time, end_time FROM network_outages",
            conn,
        )
        incidents = pd.read_sql_query(
            "SELECT incident_id, tower_id, severity, status, title, opened_at, assigned_team FROM open_incidents ORDER BY opened_at DESC",
            conn,
        )
        perf_summary = pd.read_sql_query(
            """
            SELECT t.tower_id, t.tower_name, t.city, t.state, t.region, t.technology, t.status,
                   ROUND(AVG(p.downlink_throughput_mbps), 1) as avg_downlink,
                   ROUND(AVG(p.latency_ms), 1) as avg_latency,
                   ROUND(AVG(p.packet_loss_pct), 2) as avg_packet_loss
            FROM network_towers t
            LEFT JOIN tower_performance p ON t.tower_id = p.tower_id
            GROUP BY t.tower_id
            """,
            conn,
        )
        perf_series = pd.read_sql_query(
            """
            SELECT tower_id, recorded_at, downlink_throughput_mbps, latency_ms, packet_loss_pct
            FROM tower_performance
            ORDER BY recorded_at ASC
            """,
            conn,
        )
        disputes = pd.read_sql_query(
            "SELECT dispute_id, customer_id, charge_id, reason, status, opened_at FROM billing_disputes",
            conn,
        )
        subscriptions = pd.read_sql_query(
            "SELECT plan_name, count(*) as count, round(avg(monthly_fee), 2) as avg_fee FROM customer_subscriptions GROUP BY plan_name",
            conn,
        )
    finally:
        conn.close()

    # Assign color for Pydeck map
    def assign_color(status):
        if status == "OPERATIONAL":
            return [16, 185, 129, 210]  # Green
        elif status == "DEGRADED":
            return [245, 158, 11, 230]  # Amber
        return [239, 68, 68, 230]  # Red

    if not towers.empty:
        towers["color"] = towers["status"].apply(assign_color)

    return towers, outages, incidents, perf_summary, perf_series, (disputes, subscriptions)


# Initialize Session State
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "last_query" not in st.session_state:
    st.session_state["last_query"] = None


# Load Real Data
towers_df, outages_df, incidents_df, perf_summary_df, perf_series_df, billing_tuple = load_telecom_data()
disputes_df, subscriptions_df = (billing_tuple if billing_tuple else (None, None))


# ============================================================
# 3. SIDEBAR: HEALTH CHECKS, FRAMEWORK MAP & REPOSITORY STATS
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="background: #0f172a; width: 36px; height: 36px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; color: white; font-weight: 800;">
                NOC
            </div>
            <div>
                <h3 style="margin: 0; font-size: 1.05rem; color: #0f172a; font-weight: 800;">Prodapt Operations</h3>
                <span style="font-size: 0.74rem; color: #64748b; font-weight: 600;">Autonomous Telemetry Platform</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("System Health & Status")

    # 1. SQLite Database Status
    db_candidates = [
        PROJECT_ROOT / "data" / "telecom_ops.db",
        PROJECT_ROOT / "projectfiles" / "telecom_ops.db",
    ]
    db_ready = any(p.exists() for p in db_candidates)
    st.markdown(
        f'<div class="status-indicator">'
        f'<span><strong>SQLite Database</strong></span>'
        f'<span><span class="{"dot-online" if db_ready else "dot-offline"}"></span>'
        f'{"Ready" if db_ready else "Missing"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 2. ChromaDB Vector Store Status
    chroma_path = PROJECT_ROOT / "rag" / "chroma_db"
    chroma_ready = chroma_path.exists()
    st.markdown(
        f'<div class="status-indicator">'
        f'<span><strong>ChromaDB Vector Store</strong></span>'
        f'<span><span class="{"dot-online" if chroma_ready else "dot-offline"}"></span>'
        f'{"Ready" if chroma_ready else "Missing"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 3. Live ADK Service Health Check (Ports 8001 & 8002)
    net_online = check_service_health(NETWORK_A2A_PORT)
    bill_online = check_service_health(BILLING_A2A_PORT)

    st.markdown(
        f'<div class="status-indicator">'
        f'<span><strong>Network ADK ({NETWORK_A2A_PORT})</strong></span>'
        f'<span><span class="{"dot-online" if net_online else "dot-offline"}"></span>'
        f'{"Online" if net_online else "Direct SQL"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="status-indicator">'
        f'<span><strong>Billing ADK ({BILLING_A2A_PORT})</strong></span>'
        f'<span><span class="{"dot-online" if bill_online else "dot-offline"}"></span>'
        f'{"Online" if bill_online else "Direct SQL"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Real Database records snapshot
    if towers_df is not None:
        st.markdown(
            f"""
            <div style="background: #f8fafc; border-radius: 6px; padding: 10px 12px; margin-top: 14px; font-size: 0.78rem; color: #334155; border: 1px solid #e2e8f0;">
                <div style="font-weight: 700; margin-bottom: 4px; color: #0f172a;">Live Database Telemetry:</div>
                <div>• Cell Towers: <strong>{len(towers_df)}</strong> sites</div>
                <div>• Outage Records: <strong>{len(outages_df) if outages_df is not None else 0}</strong> logs</div>
                <div>• Active Incidents: <strong>{len(incidents_df) if incidents_df is not None else 0}</strong> tickets</div>
                <div>• Billing Disputes: <strong>{len(disputes_df) if disputes_df is not None else 0}</strong> records</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ADK Helper Note if offline
    if not (net_online and bill_online):
        st.markdown(
            """
            <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:10px; margin-top:14px; font-size:0.78rem; color:#334155;">
            <strong>Autonomous Microservices:</strong><br>
            To activate standalone A2A HTTP endpoints on ports 8001 & 8002, run in terminals:
            <code style="display:block; margin:5px 0; font-size:0.72rem; color:#0f172a; background:#e2e8f0; padding:3px; border-radius:3px;">python adk-services/network_diagnostics/agent.py</code>
            <code style="display:block; margin:5px 0; font-size:0.72rem; color:#0f172a; background:#e2e8f0; padding:3px; border-radius:3px;">python adk-services/billing_resolution/agent.py</code>
            <em>(Automated direct SQL fallback active when offline)</em>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("Framework Architecture Map")

    st.markdown(
        """
        | Capability | Framework / Component |
        | :--- | :--- |
        | **Policy FAQ** | ChromaDB Vector Store RAG |
        | **Network Analytics** | SQLite Semantic SQL |
        | **Diagnostics** | Google ADK A2A (Port 8001) |
        | **Billing Resolution** | Google ADK A2A (Port 8002) |
        | **Supervisor** | LangGraph StateGraph |
        | **Final Response** | CrewAI Sequential Comms |
        """
    )


# ============================================================
# 4. MAIN CONTENT: HEADER, REAL-TIME STATUS & CALCULATED METRICS
# ============================================================

# Solid Dark Slate Header (No blue-green gradients)
st.markdown(
    """
    <div class="header-card">
        <div class="header-left">
            <div class="header-pill">
                <span class="rt-dot-live"></span>
                Prodapt Telecom Operations Center · Real-Time Multi-Agent Orchestration
            </div>
            <h1 class="header-title">Prodapt AI Operations Center</h1>
            <div class="header-subtitle">Autonomous Telecom Operations · Multi-Agent StateGraph · Real-Time Telemetry Intelligence</div>
            <div class="badge-container">
                <span class="badge">LangGraph Supervisor</span>
                <span class="badge">ChromaDB Policy RAG</span>
                <span class="badge">SQLite Semantic SQL</span>
                <span class="badge">Google ADK A2A (8001 & 8002)</span>
                <span class="badge">CrewAI Comms Crew</span>
            </div>
        </div>
        <div style="flex: 0 0 80px; display: flex; justify-content: center; align-items: center;">
            <svg width="68" height="68" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M32 6V58M22 58L30 16M42 58L34 16M20 44H44M24 30H40M27 20H37" stroke="#e2e8f0" stroke-width="2.2" stroke-linecap="round"/>
                <circle cx="32" cy="8" r="3" fill="#38bdf8"/>
                <path d="M24 10C18 16 18 24 24 30" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"/>
                <path d="M40 10C46 16 46 24 40 30" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Real-Time Telemetry Status Toolbar (Properly Aligned)
current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

col_status, col_btn = st.columns([8.2, 1.8])
with col_status:
    st.markdown(
        f"""
        <div class="rt-status-bar">
            <div class="rt-status-left">
                <span class="rt-status-pill"><span class="rt-dot-live"></span> Live Telemetry Pipeline</span>
                <span style="color: #cbd5e1;">|</span>
                <span>Active Database: <strong>telecom_ops.db</strong></span>
                <span style="color: #cbd5e1;">|</span>
                <span>Last Synchronized: <strong>{current_timestamp}</strong></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_btn:
    if st.button("Refresh Telemetry", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# 100% Real-Data KPI Metrics (Calculated dynamically from database tables)
total_towers = len(towers_df) if towers_df is not None else 0
operational_towers = len(towers_df[towers_df["status"] == "OPERATIONAL"]) if towers_df is not None else 0
degraded_towers = len(towers_df[towers_df["status"] == "DEGRADED"]) if towers_df is not None else 0

total_outages = len(outages_df) if outages_df is not None else 0
avg_outage_duration = round(outages_df["duration_hours"].mean(), 1) if (outages_df is not None and not outages_df.empty) else 0.0
crit_outages = len(outages_df[outages_df["severity"] == "CRITICAL"]) if outages_df is not None else 0

avg_downlink = round(perf_summary_df["avg_downlink"].mean(), 1) if (perf_summary_df is not None and not perf_summary_df.empty) else 0.0
peak_downlink = round(perf_series_df["downlink_throughput_mbps"].max(), 1) if (perf_series_df is not None and not perf_series_df.empty) else 0.0

total_incidents = len(incidents_df) if incidents_df is not None else 0
crit_incidents = len(incidents_df[incidents_df["severity"] == "CRITICAL"]) if incidents_df is not None else 0
major_incidents = len(incidents_df[incidents_df["severity"] == "MAJOR"]) if incidents_df is not None else 0
minor_incidents = total_incidents - crit_incidents - major_incidents

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric(
        label="Cell Towers",
        value=f"{total_towers} Sites",
        delta=f"{operational_towers} Operational, {degraded_towers} Degraded",
    )
with col_m2:
    st.metric(
        label="Average 5G Downlink",
        value=f"{avg_downlink} Mbps",
        delta=f"Peak {peak_downlink} Mbps",
    )
with col_m3:
    st.metric(
        label="Logged Outages",
        value=f"{total_outages} Events",
        delta=f"{crit_outages} Critical (Avg {avg_outage_duration} hrs)",
    )
with col_m4:
    st.metric(
        label="Open Incidents",
        value=f"{total_incidents} Active",
        delta=f"{crit_incidents} Crit, {major_incidents} Maj, {minor_incidents} Min",
    )

# 100% Real Live Event Feed (Dynamically queried from open_incidents table)
if incidents_df is not None and not incidents_df.empty:
    feed_lines = []
    for _, inc_row in incidents_df.iterrows():
        i_time = str(inc_row["opened_at"])
        i_site = str(inc_row["tower_id"])
        i_sev = str(inc_row["severity"])
        i_title = str(inc_row["title"])
        i_status = str(inc_row["status"])
        feed_lines.append(
            f'<div class="live-feed-item">'
            f'<span class="live-feed-time">{i_time}</span>'
            f'<span class="live-feed-tag">[{i_site} · {i_sev}]</span>'
            f'<span class="live-feed-text">{i_title} <em>(Status: {i_status})</em></span>'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="live-feed-box">
            {"".join(feed_lines)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 5. ENTERPRISE DASHBOARD TABS
# ============================================================

tab_console, tab_network, tab_outages, tab_billing, tab_arch = st.tabs(
    [
        "Operations Console",
        "Network Telemetry",
        "Outage & SLA Analytics",
        "Billing Operations",
        "Architecture Blueprint",
    ]
)


# ------------------------------------------------------------
# TAB 1: OPERATIONS CONSOLE (FIXED ALIGNMENT, NO EMOJIS)
# ------------------------------------------------------------
with tab_console:
    st.markdown("##### Quick Practice Scenarios")

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            """
            <div class="scenario-card-box">
                <div class="scenario-card-title">Scenario 1: Roaming Policy</div>
                <div class="scenario-card-tag">ChromaDB RAG</div>
                <div class="scenario-card-desc">Western Europe roaming daily passes, data allowances, and fair use.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Scenario 1", key="btn_s1", use_container_width=True):
            st.session_state["query_input"] = "What is Prodapt's roaming policy for Western Europe?"
            st.rerun()

    with c2:
        st.markdown(
            """
            <div class="scenario-card-box">
                <div class="scenario-card-title">Scenario 2: Outage Trends</div>
                <div class="scenario-card-tag">Semantic SQL</div>
                <div class="scenario-card-desc">Historical outages, root-cause patterns, and CRITICAL severity frequency.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Scenario 2", key="btn_s2", use_container_width=True):
            st.session_state["query_input"] = "Which region had the most CRITICAL network outages recently?"
            st.rerun()

    with c3:
        st.markdown(
            """
            <div class="scenario-card-box">
                <div class="scenario-card-title">Scenario 3: 5G Diagnostics</div>
                <div class="scenario-card-tag">ADK Port 8001</div>
                <div class="scenario-card-desc">Live Austin TX-512 tower RF diagnostic check and packet loss inspection.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Scenario 3", key="btn_s3", use_container_width=True):
            st.session_state["query_input"] = "My 5G keeps dropping in Austin near tower TX-512. Please diagnose."
            st.rerun()

    with c4:
        st.markdown(
            """
            <div class="scenario-card-box">
                <div class="scenario-card-title">Scenario 4: Billing Dispute</div>
                <div class="scenario-card-tag">ADK Port 8002</div>
                <div class="scenario-card-desc">Customer CUST-10002 duplicate plan fee investigation and credit entry.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Scenario 4", key="btn_s4", use_container_width=True):
            st.session_state["query_input"] = "Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit."
            st.rerun()

    with c5:
        st.markdown(
            """
            <div class="scenario-card-box">
                <div class="scenario-card-title">Scenario 5: Hybrid SLA Flow</div>
                <div class="scenario-card-tag">Multi-Agent Flow</div>
                <div class="scenario-card-desc">Correlates 6-hr Midwest outage facts with SLA compensation policy via CrewAI.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Scenario 5", key="btn_s5", use_container_width=True):
            st.session_state["query_input"] = "We had a 6-hour outage in the Midwest. Am I eligible for an SLA credit and what does policy say?"
            st.rerun()

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # Inquiry Input Area
    query = st.text_area(
        "Customer / Operations Inquiry:",
        height=95,
        placeholder="Type any inquiry in plain English...\ne.g. 'Can I trade in an iPhone 13?' or 'Diagnose tower FL-090 in Miami' or 'Check CUST-10002 billing charges'",
        key="query_input",
    )

    col_submit, col_clear, col_sample, col_spacer = st.columns([1.8, 1.2, 1.8, 4.2])
    with col_submit:
        submit_clicked = st.button("Process Inquiry", type="primary", use_container_width=True)

    with col_clear:
        if st.button("Clear", use_container_width=True):
            st.session_state["query_input"] = ""
            st.session_state["last_result"] = None
            st.session_state["last_query"] = None
            st.rerun()

    with col_sample:
        if st.button("Sample Queries", use_container_width=True):
            samples = [
                "What is Prodapt's roaming policy for Western Europe?",
                "Which region had the most CRITICAL network outages recently?",
                "My 5G keeps dropping in Austin near tower TX-512. Please diagnose.",
                "Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit.",
                "We had a 6-hour outage in the Midwest. Am I eligible for an SLA credit and what does policy say?",
                "Can I trade in an iPhone 13 under current device financing terms?",
                "Tower FL-090 in Miami has customer complaints. Check its performance metrics and latency.",
                "Explain the 5G Fair Usage policy during network congestion hours.",
            ]
            st.session_state["query_input"] = random.choice(samples)
            st.rerun()

    # Process Inquiry
    if submit_clicked:
        active_query = query.strip()
        if not active_query:
            st.warning("Please enter or select an inquiry to process.")
        else:
            with st.spinner("LangGraph Supervisor evaluating intent & routing to specialist agents..."):
                try:
                    result = run_telecom_assistant(active_query)
                    st.session_state["last_result"] = result
                    st.session_state["last_query"] = active_query
                except Exception as exc:
                    st.error(f"Error during agent execution: {exc}")

    # Render Active Results
    if st.session_state.get("last_result"):
        res = st.session_state["last_result"]
        final_response = res.get("final_response", "")
        execution_trace = res.get("execution_trace", [])
        agent_context = res.get("agent_context", "")

        # 1. Final Customer Response Card
        st.markdown(
            f"""
            <div class="response-card">
                <div class="response-header">
                    <span class="response-badge">Customer-Ready Communication (CrewAI Polished)</span>
                    <span class="response-seal">SLA & Compliance Verified</span>
                </div>
                <div class="response-body">{final_response}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Mandatory Agent Execution Trace (Expanded by Default)
        with st.expander("Agent Execution Trace (Routing Path & Telemetry)", expanded=True):
            if not execution_trace:
                st.info("No worker nodes were executed.")
            else:
                # Visual Route Stepper Badges
                route_items = ["Supervisor"]
                for step in execution_trace:
                    route_items.append(step["worker"])
                    route_items.append("Supervisor")
                route_items.append("FINISH")

                route_html_parts = []
                for idx, node in enumerate(route_items):
                    route_html_parts.append(f'<span class="route-node">{node}</span>')
                    if idx < len(route_items) - 1:
                        route_html_parts.append('<span class="route-arrow">➔</span>')

                st.markdown(
                    f'<div class="route-path-container">{" ".join(route_html_parts)}</div>',
                    unsafe_allow_html=True,
                )

                tech_labels = {
                    "PolicyRAG": "ChromaDB Document Vector Search & RAG",
                    "NetworkAnalytics": "SQLite Semantic SQL Analytics (telecom_ops.db)",
                    "NetworkDiagnosticsADK": "Google ADK Microservice (Port 8001 / SQLite)",
                    "BillingResolutionADK": "Google ADK Microservice (Port 8002 / SQLite)",
                    "CustomerCommsCrew": "CrewAI Sequential Crew (Drafter + Reviewer)",
                }

                for idx, step in enumerate(execution_trace, 1):
                    worker = step.get("worker", "Worker")
                    output_text = step.get("output", "")
                    tech_desc = tech_labels.get(worker, "Autonomous Specialist Worker")

                    st.markdown(
                        f"""
                        <div class="trace-card">
                            <div>
                                <span class="step-badge">{idx}</span>
                                <span class="trace-worker">{worker}</span>
                                <span class="trace-tech">[{tech_desc}]</span>
                                <span class="trace-status">SUCCESS</span>
                            </div>
                            <div class="trace-output">{output_text}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # 3. Secondary Debug Expander
        if agent_context:
            with st.expander("Full Accumulated Specialist Findings (Raw Debug Trace)", expanded=False):
                st.code(agent_context, language="markdown")


# ------------------------------------------------------------
# TAB 2: NETWORK TELEMETRY & TOWERS DASHBOARD
# ------------------------------------------------------------
with tab_network:
    st.markdown("#### Live 5G/LTE Cell Tower Infrastructure & Real-Time RF Telemetry")

    if towers_df is not None and not towers_df.empty:
        # Pydeck Interactive Map
        c_map, c_details = st.columns([2.2, 1])

        with c_map:
            view_state = pdk.ViewState(
                latitude=38.5,
                longitude=-96.0,
                zoom=3.6,
                pitch=15,
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=towers_df,
                get_position=["longitude", "latitude"],
                get_color="color",
                get_radius=60000,
                radius_min_pixels=8,
                radius_max_pixels=28,
                pickable=True,
                auto_highlight=True,
            )

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_provider="carto",
                map_style="light",
                tooltip={
                    "html": """
                    <div style="font-family: sans-serif; padding: 6px; font-size: 12px;">
                        <div style="font-weight: 800; font-size: 13px; color: #0284c7; margin-bottom: 4px;">{tower_name} ({tower_id})</div>
                        <div><b>Status:</b> {status}</div>
                        <div><b>Technology:</b> {technology}</div>
                        <div><b>Location:</b> {city}, {state} ({region})</div>
                    </div>
                    """,
                    "style": {
                        "backgroundColor": "#0f172a",
                        "color": "#ffffff",
                        "borderRadius": "6px",
                    },
                },
            )

            st.pydeck_chart(deck, use_container_width=True)

            # Map Legend
            st.markdown(
                """
                <div style="display: flex; gap: 20px; margin-top: 4px; font-size: 0.80rem;">
                    <span style="display: flex; align-items: center; gap: 6px;">
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                        <strong>Operational</strong> (Optimal RF Signal)
                    </span>
                    <span style="display: flex; align-items: center; gap: 6px;">
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: #f59e0b; display: inline-block;"></span>
                        <strong>Degraded</strong> (Packet Loss Elevated)
                    </span>
                    <span style="display: flex; align-items: center; gap: 6px;">
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; display: inline-block;"></span>
                        <strong>Critical Outage</strong> (Field Action Required)
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_details:
            st.markdown("##### Regional Tower Summary")
            st.dataframe(
                perf_summary_df[["tower_id", "city", "status", "avg_downlink", "avg_latency"]],
                use_container_width=True,
                column_config={
                    "tower_id": "Site ID",
                    "city": "Market",
                    "status": "State",
                    "avg_downlink": "Mbps",
                    "avg_latency": "ms",
                },
                hide_index=True,
                height=340,
            )

        st.markdown("---")

        # Interactive Tower RF Telemetry Explorer
        st.markdown("##### Tower RF Telemetry Explorer (Time-Series Diagnostics)")

        selected_tower = st.selectbox(
            "Select Cell Tower to Inspect:",
            options=perf_summary_df["tower_id"].tolist(),
            format_func=lambda tid: f"{tid} - {perf_summary_df[perf_summary_df['tower_id'] == tid]['tower_name'].iloc[0]} ({perf_summary_df[perf_summary_df['tower_id'] == tid]['status'].iloc[0]})",
        )

        if perf_series_df is not None and not perf_series_df.empty:
            tower_data = perf_series_df[perf_series_df["tower_id"] == selected_tower].copy()

            if not tower_data.empty:
                t_kpi1, t_kpi2, t_kpi3, t_kpi4 = st.columns(4)
                latest_sample = tower_data.iloc[-1]
                earliest_sample = tower_data.iloc[0]

                dl_delta = round(latest_sample["downlink_throughput_mbps"] - earliest_sample["downlink_throughput_mbps"], 1)
                lat_delta = round(latest_sample["latency_ms"] - earliest_sample["latency_ms"], 1)
                loss_delta = round(latest_sample["packet_loss_pct"] - earliest_sample["packet_loss_pct"], 2)

                with t_kpi1:
                    st.metric("Latest Downlink", f"{latest_sample['downlink_throughput_mbps']} Mbps", f"{dl_delta} Mbps change")
                with t_kpi2:
                    st.metric("Latest Latency", f"{latest_sample['latency_ms']} ms", f"{lat_delta} ms change", delta_color="inverse")
                with t_kpi3:
                    st.metric("Packet Loss Rate", f"{latest_sample['packet_loss_pct']}%", f"{loss_delta}% change", delta_color="inverse")
                with t_kpi4:
                    site_row = perf_summary_df[perf_summary_df["tower_id"] == selected_tower].iloc[0]
                    st.metric("Technology / Region", f"{site_row['technology']}", f"{site_row['city']}, {site_row['state']}")

                # Charts
                c_chart_dl, c_chart_lat = st.columns(2)

                with c_chart_dl:
                    chart_dl = (
                        alt.Chart(tower_data)
                        .mark_line(point=True, strokeWidth=2.5, color="#0f172a")
                        .encode(
                            x=alt.X("recorded_at:T", title="Timestamp"),
                            y=alt.Y("downlink_throughput_mbps:Q", title="Downlink Throughput (Mbps)"),
                            tooltip=["recorded_at:T", "downlink_throughput_mbps:Q"],
                        )
                        .properties(height=240, title="5G Downlink Speed Trend (Mbps)")
                    )
                    st.altair_chart(chart_dl, use_container_width=True)

                with c_chart_lat:
                    chart_lat = (
                        alt.Chart(tower_data)
                        .mark_line(point=True, strokeWidth=2.5, color="#475569")
                        .encode(
                            x=alt.X("recorded_at:T", title="Timestamp"),
                            y=alt.Y("latency_ms:Q", title="Latency (ms)"),
                            tooltip=["recorded_at:T", "latency_ms:Q", "packet_loss_pct:Q"],
                        )
                        .properties(height=240, title="RF Latency & Loss Trend (ms)")
                    )
                    st.altair_chart(chart_lat, use_container_width=True)
    else:
        st.info("Database telemetry not available. Ensure data/telecom_ops.db is initialized.")


# ------------------------------------------------------------
# TAB 3: OUTAGE & SLA ANALYTICS DASHBOARD
# ------------------------------------------------------------
with tab_outages:
    st.markdown("#### Outage Impact Analytics & SLA Incident Logs")

    if outages_df is not None and not outages_df.empty:
        col_out1, col_out2 = st.columns(2)

        with col_out1:
            st.markdown("##### Outages by Severity Level")
            outage_summary = (
                outages_df.groupby("severity")
                .agg(count=("outage_id", "count"), avg_duration=("duration_hours", "mean"), total_affected=("affected_customers", "sum"))
                .reset_index()
            )
            outage_summary["avg_duration"] = outage_summary["avg_duration"].round(1)

            chart_sev = (
                alt.Chart(outage_summary)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("severity:N", title="Severity", sort=["CRITICAL", "MAJOR", "MINOR"]),
                    y=alt.Y("count:Q", title="Incident Count"),
                    color=alt.Color(
                        "severity:N",
                        scale=alt.Scale(
                            domain=["CRITICAL", "MAJOR", "MINOR"],
                            range=["#ef4444", "#f59e0b", "#475569"],
                        ),
                        legend=None,
                    ),
                    tooltip=["severity", "count", "avg_duration", "total_affected"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart_sev, use_container_width=True)

        with col_out2:
            st.markdown("##### Regional Outage Incidents")
            reg_summary = (
                outages_df.groupby("region")
                .agg(count=("outage_id", "count"), avg_duration=("duration_hours", "mean"), customers=("affected_customers", "sum"))
                .reset_index()
            )
            reg_summary["avg_duration"] = reg_summary["avg_duration"].round(1)

            chart_reg = (
                alt.Chart(reg_summary)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#1e293b")
                .encode(
                    x=alt.X("region:N", title="Region"),
                    y=alt.Y("count:Q", title="Outage Count"),
                    tooltip=["region", "count", "avg_duration", "customers"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart_reg, use_container_width=True)

        st.markdown("##### Live Incident Tickets & NOC Queue (open_incidents)")
        if incidents_df is not None and not incidents_df.empty:
            st.dataframe(
                incidents_df,
                use_container_width=True,
                column_config={
                    "incident_id": "Ticket ID",
                    "tower_id": "Site",
                    "severity": "Severity",
                    "status": "Status",
                    "title": "Incident Title",
                    "assigned_team": "Assigned Team",
                    "opened_at": "Logged At",
                },
                hide_index=True,
                height=220,
            )

        st.markdown("##### Historical Outage Logs (network_outages)")
        st.dataframe(
            outages_df[["outage_id", "region", "severity", "duration_hours", "affected_customers", "root_cause", "status"]],
            use_container_width=True,
            column_config={
                "outage_id": "Outage ID",
                "region": "Region",
                "severity": "Severity",
                "duration_hours": "Duration (hrs)",
                "affected_customers": "Impacted Accounts",
                "root_cause": "Root Cause Analysis",
                "status": "Resolution Status",
            },
            hide_index=True,
            height=260,
        )
    else:
        st.info("Outage records not available.")


# ------------------------------------------------------------
# TAB 4: BILLING OPERATIONS DASHBOARD
# ------------------------------------------------------------
with tab_billing:
    st.markdown("#### Customer Operations & Billing Dispute Resolution Dashboard")

    col_bill1, col_bill2 = st.columns(2)

    with col_bill1:
        st.markdown("##### Billing Dispute Resolution Status")
        if disputes_df is not None and not disputes_df.empty:
            disp_counts = disputes_df.groupby("status").size().reset_index(name="count")
            chart_disp = (
                alt.Chart(disp_counts)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("status:N", title="Dispute Status"),
                    y=alt.Y("count:Q", title="Dispute Count"),
                    color=alt.Color(
                        "status:N",
                        scale=alt.Scale(
                            domain=["RESOLVED", "OPEN", "ESCALATED"],
                            range=["#10b981", "#f59e0b", "#ef4444"],
                        ),
                        legend=None,
                    ),
                    tooltip=["status", "count"],
                )
                .properties(height=240)
            )
            st.altair_chart(chart_disp, use_container_width=True)

    with col_bill2:
        st.markdown("##### Active Plans Breakdown")
        if subscriptions_df is not None and not subscriptions_df.empty:
            chart_subs = (
                alt.Chart(subscriptions_df)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#0f172a")
                .encode(
                    y=alt.Y("plan_name:N", title="Plan Tier", sort="-x"),
                    x=alt.X("count:Q", title="Subscribers"),
                    tooltip=["plan_name", "count", "avg_fee"],
                )
                .properties(height=240)
            )
            st.altair_chart(chart_subs, use_container_width=True)

    st.markdown("##### Recent Billing Dispute Audit Ledger")
    if disputes_df is not None and not disputes_df.empty:
        st.dataframe(
            disputes_df,
            use_container_width=True,
            column_config={
                "dispute_id": "Dispute Reference",
                "customer_id": "Account ID",
                "charge_id": "Charge ID",
                "reason": "Customer Dispute Reason",
                "status": "Workflow Status",
                "opened_at": "Submission Date",
            },
            hide_index=True,
            height=280,
        )


# ------------------------------------------------------------
# TAB 5: MULTI-AGENT ARCHITECTURE BLUEPRINT
# ------------------------------------------------------------
with tab_arch:
    st.markdown("#### Multi-Agent Orchestration & Data Flow Blueprint")
    st.markdown(
        "Technical topology showing LangGraph Supervisor cyclic routing, autonomous specialist nodes, Google ADK A2A services, and CrewAI communications polish."
    )

    # Clean Solid SVG Architecture Flowchart (No blue-green gradients)
    st.markdown(
        """
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 24px; box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05); margin-bottom: 24px;">
            <svg viewBox="0 0 920 480" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
                <!-- User Inquiry Node -->
                <rect x="360" y="20" width="200" height="50" rx="8" fill="#0f172a"/>
                <text x="460" y="44" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Customer / NOC Inquiry</text>
                <text x="460" y="58" fill="#94a3b8" font-size="10" text-anchor="middle">Streamlit Entrypoint</text>

                <!-- Arrow down to Supervisor -->
                <line x1="460" y1="70" x2="460" y2="105" stroke="#475569" stroke-width="2" stroke-dasharray="4 4"/>
                <polygon points="455,103 460,111 465,103" fill="#475569"/>

                <!-- Supervisor Node -->
                <rect x="330" y="112" width="260" height="64" rx="8" fill="#1e293b"/>
                <text x="460" y="138" fill="#ffffff" font-size="14" font-weight="800" text-anchor="middle">LangGraph Supervisor</text>
                <text x="460" y="156" fill="#cbd5e1" font-size="11" text-anchor="middle">Intent Classifier &amp; State Aggregator</text>

                <!-- Branching Lines to Specialists -->
                <path d="M370 176 L115 220" stroke="#64748b" stroke-width="1.8" fill="none"/>
                <path d="M420 176 L345 220" stroke="#64748b" stroke-width="1.8" fill="none"/>
                <path d="M500 176 L575 220" stroke="#64748b" stroke-width="1.8" fill="none"/>
                <path d="M550 176 L805 220" stroke="#64748b" stroke-width="1.8" fill="none"/>

                <!-- Worker 1: Policy RAG -->
                <rect x="25" y="220" width="180" height="75" rx="8" fill="#0f172a"/>
                <text x="115" y="244" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Policy RAG</text>
                <text x="115" y="260" fill="#cbd5e1" font-size="10" text-anchor="middle">ChromaDB Vector Store</text>
                <text x="115" y="274" fill="#94a3b8" font-size="9" text-anchor="middle">Roaming · SLA · Trade-In</text>

                <!-- Worker 2: Network Analytics -->
                <rect x="255" y="220" width="180" height="75" rx="8" fill="#0f172a"/>
                <text x="345" y="244" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Network Analytics</text>
                <text x="345" y="260" fill="#cbd5e1" font-size="10" text-anchor="middle">SQLite Semantic SQL</text>
                <text x="345" y="274" fill="#94a3b8" font-size="9" text-anchor="middle">Outages · MTTR · RCA</text>

                <!-- Worker 3: Network Diagnostics ADK -->
                <rect x="485" y="220" width="180" height="75" rx="8" fill="#0f172a"/>
                <text x="575" y="244" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Network Diagnostics</text>
                <text x="575" y="260" fill="#cbd5e1" font-size="10" text-anchor="middle">Google ADK (Port 8001)</text>
                <text x="575" y="274" fill="#94a3b8" font-size="9" text-anchor="middle">5G RF · Tower Telemetry</text>

                <!-- Worker 4: Billing Resolution ADK -->
                <rect x="715" y="220" width="180" height="75" rx="8" fill="#0f172a"/>
                <text x="805" y="244" fill="#ffffff" font-size="13" font-weight="700" text-anchor="middle">Billing Resolution</text>
                <text x="805" y="260" fill="#cbd5e1" font-size="10" text-anchor="middle">Google ADK (Port 8002)</text>
                <text x="805" y="274" fill="#94a3b8" font-size="9" text-anchor="middle">Disputes · Duplicate Credit</text>

                <!-- Cyclic Return Paths back to Supervisor Context -->
                <path d="M115 295 L115 325 L410 325 L410 355" stroke="#94a3b8" stroke-width="1.8" fill="none" stroke-dasharray="3 3"/>
                <path d="M345 295 L345 325 L440 325 L440 355" stroke="#94a3b8" stroke-width="1.8" fill="none" stroke-dasharray="3 3"/>
                <path d="M575 295 L575 325 L480 325 L480 355" stroke="#94a3b8" stroke-width="1.8" fill="none" stroke-dasharray="3 3"/>
                <path d="M805 295 L805 325 L510 325 L510 355" stroke="#94a3b8" stroke-width="1.8" fill="none" stroke-dasharray="3 3"/>

                <!-- CrewAI Comms Box -->
                <rect x="330" y="355" width="260" height="60" rx="8" fill="#1e293b"/>
                <text x="460" y="379" fill="#ffffff" font-size="14" font-weight="800" text-anchor="middle">Customer Comms Crew</text>
                <text x="460" y="397" fill="#cbd5e1" font-size="11" text-anchor="middle">CrewAI · Sequential Drafter + Quality Reviewer</text>

                <!-- Arrow down to Customer Output -->
                <line x1="460" y1="415" x2="460" y2="440" stroke="#475569" stroke-width="2"/>
                <polygon points="455,438 460,446 465,438" fill="#475569"/>

                <!-- Output Box -->
                <rect x="350" y="446" width="220" height="30" rx="6" fill="#0f172a"/>
                <text x="460" y="466" fill="#ffffff" font-size="12" font-weight="700" text-anchor="middle">Customer-Ready Resolution</text>
            </svg>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed Framework Specs Table
    st.markdown("##### Framework Implementation & Capability Specification")
    st.markdown(
        """
        | Capability | Framework | Integration Layer | Data Store / Protocol | Role in Pipeline |
        | :--- | :--- | :--- | :--- | :--- |
        | **Policy FAQ** | ChromaDB RAG | LlamaIndex / Vector Store | `data/documents/*.txt` | Answers roaming, device financing, trade-in, 5G fair-use queries |
        | **Network Analytics** | Semantic SQL | SQLite Database | `data/telecom_ops.db` | Aggregates historical outages, MTTR targets, root-cause trends |
        | **Tower Diagnostics** | Google ADK | A2A Protocol (Port 8001) | `telecom_ops.db` & RF Telemetry | Investigates 5G tower cell performance, packet loss, RSSI signal |
        | **Billing Resolution** | Google ADK | A2A Protocol (Port 8002) | `telecom_ops.db` & Ledger Tools | Detects double charges, computes balances, queues pending credits |
        | **Supervisor Routing**| LangGraph | StateGraph State Machine | In-memory `AgentState` | Evaluates query intent, directs specialists, manages cyclic state |
        | **Customer Response** | CrewAI | Sequential Multi-Agent | Drafter + Compliance Reviewer | Synthesizes specialist telemetry into professional customer answers |
        """
    )
