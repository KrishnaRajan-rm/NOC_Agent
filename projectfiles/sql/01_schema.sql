-- Prodapt AI Operations Center
-- SQLite schema for telecom_ops.db
--
-- Run this script FIRST, then sql/02_seed_data.sql.
-- Re-running this script drops every table and deletes all rows, including
-- credits applied during a demo. That is intentional so the database can be reset.
--
-- Monetary amounts are US dollars (REAL). Display and compare them rounded
-- to 2 decimal places.
--
-- Tables and who uses them
--   network_towers           LlamaIndex semantic SQL, Network Diagnostics ADK
--   network_outages          LlamaIndex semantic SQL
--   tower_performance        LlamaIndex semantic SQL, Network Diagnostics ADK
--   open_incidents           Network Diagnostics ADK
--   customer_subscriptions   LlamaIndex semantic SQL
--   billing_accounts         Billing Resolution ADK
--   billing_charges          Billing Resolution ADK
--   billing_credits          Billing Resolution ADK (insert on credit)
--   billing_disputes         Billing Resolution ADK
--
-- Performance interpretation used by run_connectivity_diagnostics
-- (same thresholds are written in data/documents/network_outage_procedures.txt):
--   signal_strength_dbm          acceptable >= -90; marginal -110 to -90; poor < -110
--   packet_loss_pct              normal <= 1; elevated > 2; severe > 5
--   latency_ms                   normal <= 40 on 5G; elevated > 50
--   downlink_throughput_mbps     degraded when technology is 5G, status is
--                                OPERATIONAL, and downlink is below 100
--   status OFFLINE or packet_loss_pct = 100
--                                site is down; do not troubleshoot the handset
--
-- Billing credit rule (same rule is written in billing_disputes_policy.txt):
--   amount <= 50.00  -> billing_credits.status = 'APPLIED'
--                       and billing_accounts.current_balance is reduced
--   amount >  50.00  -> billing_credits.status = 'PENDING_APPROVAL'
--                       and current_balance is left unchanged until approval
--
-- Open-bill invariant in the seed data:
--   current_balance = SUM(billing_charges.amount)
--                     WHERE invoice_status = 'OPEN'
--   PAID charges are prior-cycle history and are not part of the balance.
--   APPLIED credits in the seed point at PAID charges (already settled).
--   PENDING_APPROVAL and REJECTED credits never change current_balance.
--   A new APPLIED credit posted by a tool must subtract from current_balance.
--   A new PENDING_APPROVAL credit must not.

PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS billing_disputes;
DROP TABLE IF EXISTS billing_credits;
DROP TABLE IF EXISTS billing_charges;
DROP TABLE IF EXISTS billing_accounts;
DROP TABLE IF EXISTS customer_subscriptions;
DROP TABLE IF EXISTS open_incidents;
DROP TABLE IF EXISTS tower_performance;
DROP TABLE IF EXISTS network_outages;
DROP TABLE IF EXISTS network_towers;

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Network inventory
-- ---------------------------------------------------------------------------

CREATE TABLE network_towers (
    tower_id            TEXT PRIMARY KEY,          -- e.g. TX-512
    tower_name          TEXT NOT NULL,
    region              TEXT NOT NULL,             -- Midwest, Northeast, Southeast, Southwest, West
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,             -- two-letter US state code
    technology          TEXT NOT NULL,             -- 4G LTE, 5G, 5G mmWave
    status              TEXT NOT NULL,             -- OPERATIONAL, DEGRADED, OFFLINE, MAINTENANCE
    latitude            REAL,
    longitude           REAL,
    commissioned_date   TEXT NOT NULL,             -- ISO-8601 date
    CHECK (region IN ('Midwest', 'Northeast', 'Southeast', 'Southwest', 'West')),
    CHECK (technology IN ('4G LTE', '5G', '5G mmWave')),
    CHECK (status IN ('OPERATIONAL', 'DEGRADED', 'OFFLINE', 'MAINTENANCE'))
);

-- Historical outages. This is the analytics table for severity, duration,
-- affected customers, and root cause. It is not the live incident queue.
CREATE TABLE network_outages (
    outage_id           TEXT PRIMARY KEY,          -- e.g. OUT-2026-0912
    region              TEXT NOT NULL,
    severity            TEXT NOT NULL,             -- CRITICAL, MAJOR, MINOR
    start_time          TEXT NOT NULL,             -- ISO-8601 datetime
    end_time            TEXT,                      -- NULL while an outage is still open
    duration_hours      REAL NOT NULL,
    affected_customers  INTEGER NOT NULL,
    root_cause          TEXT NOT NULL,
    status              TEXT NOT NULL,             -- RESOLVED, ONGOING
    description         TEXT NOT NULL,
    CHECK (region IN ('Midwest', 'Northeast', 'Southeast', 'Southwest', 'West')),
    CHECK (severity IN ('CRITICAL', 'MAJOR', 'MINOR')),
    CHECK (status IN ('RESOLVED', 'ONGOING')),
    CHECK (affected_customers >= 0),
    CHECK (duration_hours >= 0)
);

-- Time series. Diagnostics must use the latest row per tower
-- (ORDER BY recorded_at DESC LIMIT 1), not an average of older samples.
CREATE TABLE tower_performance (
    performance_id              INTEGER PRIMARY KEY,
    tower_id                    TEXT NOT NULL,
    recorded_at                 TEXT NOT NULL,
    latency_ms                  REAL NOT NULL,
    packet_loss_pct             REAL NOT NULL,
    downlink_throughput_mbps    REAL NOT NULL,
    uplink_throughput_mbps      REAL NOT NULL,
    signal_strength_dbm         REAL NOT NULL,
    active_connections          INTEGER NOT NULL,
    FOREIGN KEY (tower_id) REFERENCES network_towers (tower_id),
    CHECK (packet_loss_pct >= 0 AND packet_loss_pct <= 100),
    CHECK (latency_ms >= 0),
    CHECK (downlink_throughput_mbps >= 0),
    CHECK (uplink_throughput_mbps >= 0),
    CHECK (active_connections >= 0)
);

-- Live NOC queue. Only incidents that are still active belong here.
-- Resolved historical events live in network_outages, not in this table.
CREATE TABLE open_incidents (
    incident_id     TEXT PRIMARY KEY,              -- e.g. INC-8841
    tower_id        TEXT NOT NULL,
    severity        TEXT NOT NULL,                 -- CRITICAL, MAJOR, MINOR
    status          TEXT NOT NULL,                 -- OPEN, INVESTIGATING, MONITORING
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    opened_at       TEXT NOT NULL,
    classification  TEXT NOT NULL,                 -- POWER, BACKHAUL, RADIO_ACCESS, CORE, SOFTWARE, PLANNED_MAINTENANCE
    assigned_team   TEXT NOT NULL,
    FOREIGN KEY (tower_id) REFERENCES network_towers (tower_id),
    CHECK (severity IN ('CRITICAL', 'MAJOR', 'MINOR')),
    CHECK (status IN ('OPEN', 'INVESTIGATING', 'MONITORING')),
    CHECK (classification IN (
        'POWER', 'BACKHAUL', 'RADIO_ACCESS', 'CORE', 'SOFTWARE', 'PLANNED_MAINTENANCE'
    ))
);

-- ---------------------------------------------------------------------------
-- Customers and plans (read-only analytics)
-- ---------------------------------------------------------------------------

CREATE TABLE customer_subscriptions (
    subscription_id TEXT PRIMARY KEY,              -- e.g. SUB-10002
    customer_id     TEXT NOT NULL UNIQUE,          -- e.g. CUST-10002
    customer_name   TEXT NOT NULL,
    account_type    TEXT NOT NULL,                 -- Consumer, Business, Enterprise
    plan_name       TEXT NOT NULL,
    monthly_fee     REAL NOT NULL,
    region          TEXT NOT NULL,
    city            TEXT NOT NULL,
    state           TEXT NOT NULL,
    status          TEXT NOT NULL,                 -- ACTIVE, SUSPENDED, CANCELLED
    line_count      INTEGER NOT NULL,
    start_date      TEXT NOT NULL,
    CHECK (account_type IN ('Consumer', 'Business', 'Enterprise')),
    CHECK (region IN ('Midwest', 'Northeast', 'Southeast', 'Southwest', 'West')),
    CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED')),
    CHECK (monthly_fee >= 0),
    CHECK (line_count >= 1)
);

-- ---------------------------------------------------------------------------
-- Billing (Billing Resolution ADK reads and writes these tables)
-- ---------------------------------------------------------------------------

CREATE TABLE billing_accounts (
    customer_id         TEXT PRIMARY KEY,
    customer_name       TEXT NOT NULL,
    account_type        TEXT NOT NULL,
    current_balance     REAL NOT NULL,             -- amount owed, in USD
    currency            TEXT NOT NULL DEFAULT 'USD',
    service_region      TEXT NOT NULL,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    billing_cycle       TEXT NOT NULL,
    auto_pay_enabled    INTEGER NOT NULL DEFAULT 0,
    account_status      TEXT NOT NULL,             -- ACTIVE, SUSPENDED, CLOSED
    last_updated        TEXT NOT NULL,
    CHECK (account_type IN ('Consumer', 'Business', 'Enterprise')),
    CHECK (service_region IN ('Midwest', 'Northeast', 'Southeast', 'Southwest', 'West')),
    CHECK (currency = 'USD'),
    CHECK (auto_pay_enabled IN (0, 1)),
    CHECK (account_status IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
);

CREATE TABLE billing_charges (
    charge_id           TEXT PRIMARY KEY,          -- e.g. CHG-50021
    customer_id         TEXT NOT NULL,
    description         TEXT NOT NULL,             -- e.g. Unlimited Plus
    amount              REAL NOT NULL,
    billing_period      TEXT NOT NULL,             -- YYYY-MM
    charge_date         TEXT NOT NULL,             -- ISO-8601 date
    charge_type         TEXT NOT NULL,             -- PLAN, ADDON, DEVICE, ROAMING, TAX, FEE
    is_duplicate_flag   INTEGER NOT NULL DEFAULT 0, -- 1 = billing marked this line a duplicate
    invoice_status      TEXT NOT NULL DEFAULT 'OPEN', -- OPEN = on the current balance; PAID = history
    FOREIGN KEY (customer_id) REFERENCES billing_accounts (customer_id),
    CHECK (amount >= 0),
    CHECK (is_duplicate_flag IN (0, 1)),
    CHECK (charge_type IN ('PLAN', 'ADDON', 'DEVICE', 'ROAMING', 'TAX', 'FEE')),
    CHECK (invoice_status IN ('OPEN', 'PAID'))
);

-- status APPLIED: balance was reduced by amount.
-- status PENDING_APPROVAL: amount is greater than $50; balance must stay unchanged.
-- status REJECTED: no balance change.
CREATE TABLE billing_credits (
    credit_id           INTEGER PRIMARY KEY,
    customer_id         TEXT NOT NULL,
    amount              REAL NOT NULL,
    reason              TEXT NOT NULL,
    status              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    related_charge_id   TEXT,
    FOREIGN KEY (customer_id) REFERENCES billing_accounts (customer_id),
    CHECK (amount > 0),
    CHECK (status IN ('APPLIED', 'PENDING_APPROVAL', 'REJECTED'))
);

CREATE TABLE billing_disputes (
    dispute_id          TEXT PRIMARY KEY,          -- e.g. DSP-2026-10002
    customer_id         TEXT NOT NULL,
    charge_id           TEXT,
    reason              TEXT NOT NULL,
    status              TEXT NOT NULL,             -- OPEN, RESOLVED, ESCALATED
    opened_at           TEXT NOT NULL,
    resolved_at         TEXT,
    resolution_notes    TEXT,
    FOREIGN KEY (customer_id) REFERENCES billing_accounts (customer_id),
    FOREIGN KEY (charge_id) REFERENCES billing_charges (charge_id),
    CHECK (status IN ('OPEN', 'RESOLVED', 'ESCALATED'))
);

-- ---------------------------------------------------------------------------
-- Indexes used by diagnostics, analytics, and billing lookups
-- ---------------------------------------------------------------------------

CREATE INDEX idx_towers_region ON network_towers (region);
CREATE INDEX idx_towers_status ON network_towers (status);
CREATE INDEX idx_outages_region_severity ON network_outages (region, severity);
CREATE INDEX idx_outages_duration ON network_outages (duration_hours);
CREATE INDEX idx_performance_tower_time ON tower_performance (tower_id, recorded_at);
CREATE INDEX idx_incidents_tower ON open_incidents (tower_id);
CREATE INDEX idx_subscriptions_region ON customer_subscriptions (region);
CREATE INDEX idx_subscriptions_plan ON customer_subscriptions (plan_name);
CREATE INDEX idx_charges_customer ON billing_charges (customer_id);
CREATE INDEX idx_charges_duplicate ON billing_charges (customer_id, is_duplicate_flag);
CREATE INDEX idx_charges_invoice ON billing_charges (customer_id, invoice_status);
CREATE INDEX idx_credits_customer ON billing_credits (customer_id);
CREATE INDEX idx_disputes_customer ON billing_disputes (customer_id);
