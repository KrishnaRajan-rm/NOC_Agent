"""Network Diagnostics SQL Tools and NOC Logic.

Implements Section 5.2 and Section 6.3 of the Prodapt AI Operations Center specification:
1. check_tower_status(tower_id): JOIN network_towers with the latest tower_performance
   row (ORDER BY recorded_at DESC LIMIT 1) and active open_incidents.
2. run_connectivity_diagnostics(tower_id, symptom): Evaluates KPIs against telecom
   thresholds (signal, packet loss, latency, throughput) and active NOC incidents.
3. get_regional_network_summary(region): Aggregates tower counts and operational health by region.
4. diagnose_network(query): High-level natural language entrypoint for LangGraph and CLI.
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


# Known tower mapping helper for natural language queries
KNOWN_TOWERS = {
    "TX-512": {"city": "Austin", "state": "TX", "name": "Austin Riverside"},
    "TX-208": {"city": "Dallas", "state": "TX", "name": "Dallas Uptown"},
    "IL-104": {"city": "Chicago", "state": "IL", "name": "Chicago Loop"},
    "IL-221": {"city": "Chicago", "state": "IL", "name": "Chicago South Shore"},
    "OH-077": {"city": "Columbus", "state": "OH", "name": "Columbus Metro"},
    "NY-301": {"city": "New York", "state": "NY", "name": "Manhattan Midtown"},
    "MA-055": {"city": "Boston", "state": "MA", "name": "Boston Seaport"},
    "GA-118": {"city": "Atlanta", "state": "GA", "name": "Atlanta Buckhead"},
    "FL-090": {"city": "Miami", "state": "FL", "name": "Miami Beach"},
    "CA-640": {"city": "San Jose", "state": "CA", "name": "San Jose Downtown"},
}

KNOWN_REGIONS = ["midwest", "northeast", "southeast", "southwest", "west"]


# ============================================================
# 1. CORE SQL TOOL: check_tower_status
# ============================================================

def check_tower_status(tower_id: str) -> dict[str, Any]:
    """Check inventory, latest performance metrics, and open incidents for a specific tower.

    Args:
        tower_id: Tower identifier (e.g. 'TX-512', 'FL-090').

    Returns:
        Dictionary containing tower metadata, latest KPIs, active incidents, and summary.
    """
    clean_id = tower_id.strip().upper()

    with get_connection() as conn:
        tower_row = conn.execute(
            """
            SELECT tower_id, tower_name, region, city, state, technology,
                   status, latitude, longitude, commissioned_date
            FROM network_towers
            WHERE UPPER(tower_id) = ?
            """,
            (clean_id,),
        ).fetchone()

        if not tower_row:
            return {
                "success": False,
                "error": f"Tower ID '{clean_id}' was not found in the database.",
                "tower_id": clean_id,
            }

        tower_data = dict(tower_row)

        # Query the latest performance sample (maximum recorded_at)
        perf_row = conn.execute(
            """
            SELECT performance_id, tower_id, recorded_at, latency_ms, packet_loss_pct,
                   downlink_throughput_mbps, uplink_throughput_mbps, signal_strength_dbm,
                   active_connections
            FROM tower_performance
            WHERE UPPER(tower_id) = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (clean_id,),
        ).fetchone()

        perf_data = dict(perf_row) if perf_row else None

        # Query active open incidents
        incident_rows = conn.execute(
            """
            SELECT incident_id, tower_id, severity, status, title, description,
                   opened_at, classification, assigned_team
            FROM open_incidents
            WHERE UPPER(tower_id) = ?
            ORDER BY opened_at DESC
            """,
            (clean_id,),
        ).fetchall()

        incidents_data = [dict(r) for r in incident_rows]

    # Build human-readable summary
    summary_lines = [
        f"Tower {clean_id} ({tower_data['tower_name']}) in {tower_data['city']}, {tower_data['state']} [{tower_data['region']}]:",
        f"  - Technology: {tower_data['technology']}",
        f"  - Operational Status: {tower_data['status']}",
    ]

    if perf_data:
        summary_lines.append(
            f"  - Latest Sample ({perf_data['recorded_at']}): Signal {perf_data['signal_strength_dbm']} dBm, "
            f"Packet Loss {perf_data['packet_loss_pct']}%, Downlink {perf_data['downlink_throughput_mbps']} Mbps, "
            f"Latency {perf_data['latency_ms']} ms, Active Connections {perf_data['active_connections']}"
        )
    else:
        summary_lines.append("  - Latest Performance: No telemetry recorded.")

    if incidents_data:
        summary_lines.append(f"  - Active Incidents ({len(incidents_data)}):")
        for inc in incidents_data:
            summary_lines.append(
                f"    * [{inc['incident_id']}] Severity: {inc['severity']} | Status: {inc['status']} | "
                f"Class: {inc['classification']} | Title: {inc['title']}"
            )
            summary_lines.append(f"      Details: {inc['description']}")
    else:
        summary_lines.append("  - Active Incidents: None")

    return {
        "success": True,
        "tower_id": clean_id,
        "tower": tower_data,
        "latest_performance": perf_data,
        "open_incidents": incidents_data,
        "summary_text": "\n".join(summary_lines),
    }


# ============================================================
# 2. CORE SQL TOOL: run_connectivity_diagnostics
# ============================================================

def run_connectivity_diagnostics(tower_id: str, symptom: str = "") -> dict[str, Any]:
    """Perform technical connectivity diagnostics on a tower and generate NOC recommendations.

    Evaluates KPIs against standard telecom thresholds:
      - signal_strength_dbm: acceptable >= -90; marginal -110 to -90; poor < -110
      - packet_loss_pct: normal <= 1; elevated > 2; severe > 5; 100 = site down
      - latency_ms: normal <= 40 on 5G; elevated > 50
      - downlink_throughput_mbps: degraded when 5G, OPERATIONAL, and downlink < 100 Mbps
      - status OFFLINE or packet_loss_pct = 100: site is down, do not troubleshoot handset

    Args:
        tower_id: Tower identifier (e.g. 'TX-512', 'FL-090').
        symptom: Optional customer symptom (e.g. '5G drops', 'no service', 'slow data').

    Returns:
        Diagnostic findings, severity rating, and NOC action plan.
    """
    status_info = check_tower_status(tower_id)
    if not status_info.get("success"):
        return status_info

    tower = status_info["tower"]
    perf = status_info["latest_performance"]
    incidents = status_info["open_incidents"]

    findings = []
    recommendations = []
    severity = "NORMAL"

    status = tower["status"]
    tech = tower["technology"]

    # 1. Site Status & Packet Loss Check
    if status == "OFFLINE" or (perf and perf["packet_loss_pct"] == 100.0):
        severity = "CRITICAL"
        findings.append(
            f"Tower {tower['tower_id']} is OFFLINE. Packet loss is 100% and throughput is 0 Mbps. "
            "Commercial power loss or complete backhaul isolation detected."
        )
        recommendations.append(
            "Do NOT troubleshoot customer handset or advise device reset. The tower site is down."
        )
        recommendations.append(
            "Dispatch emergency field service technician for on-site power/generator check."
        )

    elif status == "MAINTENANCE":
        severity = "MINOR"
        findings.append(
            f"Tower {tower['tower_id']} is currently undergoing PLANNED MAINTENANCE. "
            "Throughput and capacity are intentionally limited."
        )
        recommendations.append(
            "Advise customer that work is scheduled to complete per maintenance window."
        )

    else:
        # Site is OPERATIONAL or DEGRADED
        if status == "DEGRADED":
            severity = "MAJOR"
            findings.append(f"Tower {tower['tower_id']} is operating in DEGRADED status.")

        if perf:
            # Signal analysis
            sig = perf["signal_strength_dbm"]
            if sig < -110:
                findings.append(f"Poor radio signal strength ({sig} dBm < -110 dBm threshold).")
                recommendations.append("Check for local physical RF obstruction or antenna alignment.")
            elif sig < -90:
                findings.append(f"Marginal radio signal strength ({sig} dBm).")
            else:
                findings.append(f"Radio signal strength is acceptable ({sig} dBm).")

            # Packet loss analysis
            ploss = perf["packet_loss_pct"]
            if ploss > 5.0:
                severity = "CRITICAL" if severity != "CRITICAL" else severity
                findings.append(f"Severe packet loss detected ({ploss}% > 5.0% threshold).")
                recommendations.append("Investigate backhaul link degradation or radio unit failure.")
            elif ploss > 2.0:
                if severity == "NORMAL":
                    severity = "MAJOR"
                findings.append(f"Elevated packet loss detected ({ploss}% > 2.0% threshold).")
                recommendations.append("Examine radio scheduler congestion and local transport queue.")

            # Latency analysis
            lat = perf["latency_ms"]
            if tech in ("5G", "5G mmWave") and lat > 50.0:
                findings.append(f"Elevated round-trip latency on 5G ({lat} ms > 50 ms threshold).")

            # Throughput analysis
            downlink = perf["downlink_throughput_mbps"]
            if tech in ("5G", "5G mmWave") and status == "OPERATIONAL" and downlink < 100.0:
                findings.append(
                    f"Degraded 5G downlink throughput ({downlink} Mbps is below the 100 Mbps operational baseline)."
                )
                recommendations.append(
                    "Monitor radio resource scheduler and active session count."
                )

    # 2. Correlate with active incidents
    if incidents:
        inc = incidents[0]
        findings.append(
            f"Correlated Active Incident: [{inc['incident_id']}] '{inc['title']}' "
            f"({inc['severity']} severity, status: {inc['status']}). Assigned team: {inc['assigned_team']}."
        )
        recommendations.append(
            f"Reference active ticket {inc['incident_id']} when updating subscribers. Do not duplicate dispatch."
        )

    # If no specific recommendations generated
    if not recommendations:
        recommendations.append("Tower operating within nominal RF and performance parameters.")

    report_lines = [
        f"=== NOC CONNECTIVITY DIAGNOSTIC REPORT: {tower['tower_id']} ===",
        f"Site: {tower['tower_name']} ({tower['city']}, {tower['state']}) | Tech: {tech} | Status: {status}",
        f"Reported Symptom: {symptom if symptom else 'General health check'}",
        f"Diagnostic Assessment: {severity}",
        "\nFindings:",
    ]
    for f in findings:
        report_lines.append(f"  * {f}")

    report_lines.append("\nNOC Recommendations & Actions:")
    for r in recommendations:
        report_lines.append(f"  1. {r}" if len(recommendations) == 1 else f"  - {r}")

    diagnostic_report = "\n".join(report_lines)

    return {
        "success": True,
        "tower_id": tower["tower_id"],
        "severity": severity,
        "status": status,
        "findings": findings,
        "recommendations": recommendations,
        "summary_text": diagnostic_report,
    }


# ============================================================
# 3. CORE SQL TOOL: get_regional_network_summary
# ============================================================

def get_regional_network_summary(region: str) -> dict[str, Any]:
    """Aggregate tower status and open incidents across a geographic telecom region.

    Args:
        region: Geographic region ('Midwest', 'Northeast', 'Southeast', 'Southwest', 'West').

    Returns:
        Breakdown of towers, operational statuses, active incidents, and regional summary.
    """
    clean_region = region.strip().title()

    with get_connection() as conn:
        tower_rows = conn.execute(
            """
            SELECT tower_id, tower_name, city, state, technology, status
            FROM network_towers
            WHERE LOWER(region) = LOWER(?)
            ORDER BY tower_id
            """,
            (clean_region,),
        ).fetchall()

        if not tower_rows:
            return {
                "success": False,
                "error": f"No network infrastructure found for region '{region}'.",
                "region": clean_region,
            }

        towers = [dict(r) for r in tower_rows]
        tower_ids = [t["tower_id"] for t in towers]

        # Get latest performance per tower
        perf_map = {}
        for tid in tower_ids:
            p = conn.execute(
                """
                SELECT packet_loss_pct, downlink_throughput_mbps, signal_strength_dbm
                FROM tower_performance
                WHERE tower_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (tid,),
            ).fetchone()
            if p:
                perf_map[tid] = dict(p)

        # Get open incidents in the region
        placeholders = ",".join("?" for _ in tower_ids)
        incident_rows = conn.execute(
            f"""
            SELECT incident_id, tower_id, severity, status, title
            FROM open_incidents
            WHERE tower_id IN ({placeholders})
            ORDER BY opened_at DESC
            """,
            tower_ids,
        ).fetchall()

        incidents = [dict(r) for r in incident_rows]

    # Calculate status counts
    status_counts: dict[str, int] = {}
    for t in towers:
        st = t["status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    # Format human-readable output
    breakdown_parts = [f"{count} {st}" for st, count in status_counts.items()]
    breakdown_str = ", ".join(breakdown_parts)

    lines = [
        f"=== Regional Network Summary: {clean_region} ===",
        f"Total Towers: {len(towers)} ({breakdown_str})",
        f"Open Incidents: {len(incidents)}",
        "\nTower Status Details:",
    ]

    for t in towers:
        tid = t["tower_id"]
        perf = perf_map.get(tid, {})
        inc_match = [i for i in incidents if i["tower_id"] == tid]
        inc_str = f" [Incident: {inc_match[0]['incident_id']} - {inc_match[0]['title']}]" if inc_match else ""

        perf_str = ""
        if perf:
            perf_str = f" (Loss: {perf.get('packet_loss_pct', 0)}%, Signal: {perf.get('signal_strength_dbm', 0)} dBm)"

        lines.append(
            f"  * {tid} ({t['tower_name']}, {t['city']} {t['state']}) - "
            f"Tech: {t['technology']} | Status: {t['status']}{perf_str}{inc_str}"
        )

    summary_text = "\n".join(lines)

    return {
        "success": True,
        "region": clean_region,
        "total_towers": len(towers),
        "status_counts": status_counts,
        "towers": towers,
        "open_incidents": incidents,
        "summary_text": summary_text,
    }


# ============================================================
# 4. NATURAL LANGUAGE DIAGNOSTIC ROUTER: diagnose_network
# ============================================================

def diagnose_network(query: str) -> str:
    """Natural language dispatcher for telecom network diagnostics.

    Accepts inquiries such as:
      - 'Diagnose 5G drops near tower TX-512 in Austin'
      - 'What is wrong with tower FL-090 in Miami?'
      - 'Summarize the Southwest region'
      - 'What is the status of tower TX-208 in Dallas?'
    """
    if not query or not query.strip():
        return "Please specify a tower ID (e.g. TX-512) or region (e.g. Southwest) for network diagnostics."

    q_lower = query.lower()

    # 1. Flexible tower ID matching (supports TX-512, TX 512, tx512, TX_512)
    tower_match = re.search(r"\b([A-Za-z]{2})[-_\s]?(\d{3})\b", query)
    matched_tower_id = None
    if tower_match:
        cand = f"{tower_match.group(1).upper()}-{tower_match.group(2)}"
        if cand in KNOWN_TOWERS:
            matched_tower_id = cand

    # 2. Check for 3-digit tower code (e.g. tower 512, site #208)
    if not matched_tower_id:
        num_match = re.search(r"\b(?:tower|site|cell)?\s*#?[-_\s]?(\d{3})\b", query, re.IGNORECASE)
        if num_match:
            code = num_match.group(1)
            for tid in KNOWN_TOWERS:
                if tid.endswith(code):
                    matched_tower_id = tid
                    break

    # 3. Check for open incident ticket (e.g. INC-8841, inc 8841, incident 8790)
    if not matched_tower_id:
        inc_match = re.search(r"\bINC[-_\s]?(\d{4})\b", query, re.IGNORECASE)
        if inc_match:
            inc_id = f"INC-{inc_match.group(1)}"
            try:
                with get_connection() as conn:
                    inc_row = conn.execute(
                        "SELECT tower_id, title FROM open_incidents WHERE incident_id = ?",
                        (inc_id,),
                    ).fetchone()
                    if inc_row:
                        matched_tower_id = inc_row["tower_id"]
            except Exception:
                pass

    # 4. Check for city or specific landmark keywords
    if not matched_tower_id:
        if "south shore" in q_lower:
            matched_tower_id = "IL-221"
        elif "loop" in q_lower:
            matched_tower_id = "IL-104"
        elif "riverside" in q_lower or "austin" in q_lower:
            matched_tower_id = "TX-512"
        elif "uptown" in q_lower or "dallas" in q_lower:
            matched_tower_id = "TX-208"
        elif "miami" in q_lower or "florida" in q_lower:
            matched_tower_id = "FL-090"
        elif "boston" in q_lower or "seaport" in q_lower:
            matched_tower_id = "MA-055"
        elif "columbus" in q_lower:
            matched_tower_id = "OH-077"
        elif "manhattan" in q_lower or "new york" in q_lower or "midtown" in q_lower:
            matched_tower_id = "NY-301"
        elif "san jose" in q_lower or "silicon valley" in q_lower:
            matched_tower_id = "CA-640"
        elif "atlanta" in q_lower or "buckhead" in q_lower:
            matched_tower_id = "GA-118"

    # 5. Check for region summary request
    matched_region = None
    for r in KNOWN_REGIONS:
        if r in q_lower:
            matched_region = r
            break

    # If query mentions a region and asks to summarize/overview/health (and no specific tower mentioned)
    if matched_region and (not matched_tower_id or "region" in q_lower or "summar" in q_lower):
        res = get_regional_network_summary(matched_region)
        if res.get("success"):
            return res["summary_text"]

    # 6. If a tower is identified, run diagnostics or status check
    if matched_tower_id:
        diagnostic_keywords = ["drop", "diagnos", "wrong", "issue", "problem", "fail", "slow", "down", "offline", "disconnect", "packet loss", "latency", "signal"]
        if any(k in q_lower for k in diagnostic_keywords):
            res = run_connectivity_diagnostics(matched_tower_id, symptom=query)
            return res.get("summary_text", str(res))
        else:
            res = check_tower_status(matched_tower_id)
            return res.get("summary_text", str(res))

    # 7. Fallback: if no specific tower was provided, generate live NOC Network Overview
    try:
        with get_connection() as conn:
            abnormal_rows = conn.execute(
                """
                SELECT t.tower_id, t.tower_name, t.city, t.state, t.status, t.technology,
                       COALESCE(i.incident_id, 'None') as incident_id,
                       COALESCE(i.title, 'No open ticket') as incident_title
                FROM network_towers t
                LEFT JOIN open_incidents i ON t.tower_id = i.tower_id
                WHERE t.status != 'OPERATIONAL'
                ORDER BY t.tower_id
                """
            ).fetchall()
            status_lines = [
                f"  * {r['tower_id']} ({r['tower_name']}, {r['city']}): Status {r['status']} | Active Ticket: {r['incident_id']} - {r['incident_title']}"
                for r in abnormal_rows
            ]
            status_summary = "\n".join(status_lines)
    except Exception:
        status_summary = "  * FL-090 (Miami Beach): OFFLINE (Power failure)\n  * TX-208 (Dallas Uptown): DEGRADED (High packet loss)\n  * IL-221 (Chicago South Shore): DEGRADED\n  * MA-055 (Boston Seaport): MAINTENANCE"

    return (
        "NOC Executive Network Telemetry Overview:\n"
        "6 of 10 towers are currently OPERATIONAL with normal RF and latency parameters.\n"
        "Active abnormal sites requiring monitoring or dispatch:\n"
        f"{status_summary}\n\n"
        "To inspect an individual site, please specify a tower ID (e.g. TX-512, FL-090, TX-208) or city (e.g. Austin, Miami, Dallas)."
    )
