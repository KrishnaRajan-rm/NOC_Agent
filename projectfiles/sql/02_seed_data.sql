-- Prodapt AI Operations Center
-- Seed data for telecom_ops.db
--
-- Run sql/01_schema.sql first. This script expects empty tables.
-- Business clock: 23 September 2026. Generated so the demo scenarios stay
-- unambiguous even when the history around them is large.
--
-- Scenario anchors (do not change these values)
--
--   Towers                 exactly 10, including TX-512.
--
--   Scenario 2             CRITICAL outages, all time:
--                          Midwest 6, Northeast 2, Southeast 1,
--                          Southwest 0, West 0.
--                          September 2026 only: Midwest 2, Southeast 1.
--                          Midwest is ahead on both cuts.
--
--   Scenario 3             TX-512 Austin, Southwest, 5G, OPERATIONAL.
--                          Latest sample 2026-09-23 08:15:00 only:
--                          signal -72 dBm, packet loss 3.8, latency 58 ms,
--                          downlink 85 Mbps. Earlier samples the same week
--                          are healthier. Use the latest row, not an average.
--                          Open incident INC-8841, INVESTIGATING.
--                          Highest latest packet loss is FL-090 at 100,
--                          then TX-208 at 8.6, then IL-221 at 5.4.
--                          FL-090 is offline only on the latest sample.
--
--   Scenario 4             CUST-10002 Alex Romero, Consumer, Unlimited Plus.
--                          Open charges CHG-50021 and CHG-50022, both
--                          Unlimited Plus 65.99 for 2026-09. CHG-50022 has
--                          is_duplicate_flag = 1. current_balance = 131.98.
--                          No open credit. 65.99 is above the 50.00 limit,
--                          so apply_billing_credit must insert
--                          PENDING_APPROVAL and leave 131.98 unchanged.
--
--   Scenario 5             OUT-2026-0912 is the only outage with
--                          duration_hours = 6. Midwest, CRITICAL, 8500
--                          customers, fiber backhaul cut, 2026-09-12
--                          02:10 through 08:10, RESOLVED. It is also the
--                          longest outage in the table. SLA rules are only
--                          in sla_policy.txt (Business 4 hours, Consumer
--                          8 hours, Enterprise 2 hours).
--
--   Other credit paths     still open, no credit posted yet:
--                          CUST-10027 duplicate 12.00 (under the limit)
--                          CUST-10008 duplicate 36.00 (under the limit)
--                          CUST-10128 duplicate 50.00 (equal to the limit,
--                          so a correct tool sets APPLIED)
--                          CUST-10011 duplicate 80.00 (over the limit)
--
--   Balance invariant
--                          current_balance = sum of invoice_status OPEN
--                          charges. PAID rows are prior cycles. Seeded
--                          APPLIED credits point at PAID charges and must
--                          not be subtracted again.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- network_towers: exactly 10 rows
INSERT INTO network_towers (
    tower_id, tower_name, region, city, state, technology, status, latitude, longitude, commissioned_date
) VALUES
    ('TX-512', 'Austin Riverside', 'Southwest', 'Austin', 'TX', '5G', 'OPERATIONAL', 30.2672, -97.7431, '2023-04-18'),
    ('TX-208', 'Dallas Uptown', 'Southwest', 'Dallas', 'TX', '5G', 'DEGRADED', 32.8025, -96.8028, '2021-11-02'),
    ('IL-104', 'Chicago Loop', 'Midwest', 'Chicago', 'IL', '5G', 'OPERATIONAL', 41.8781, -87.6298, '2022-06-09'),
    ('IL-221', 'Chicago South Shore', 'Midwest', 'Chicago', 'IL', '4G LTE', 'DEGRADED', 41.7606, -87.5581, '2018-03-22'),
    ('OH-077', 'Columbus Metro', 'Midwest', 'Columbus', 'OH', '5G', 'OPERATIONAL', 39.9612, -82.9988, '2024-01-15'),
    ('NY-301', 'Manhattan Midtown', 'Northeast', 'New York', 'NY', '5G mmWave', 'OPERATIONAL', 40.7549, -73.984, '2023-09-01'),
    ('MA-055', 'Boston Seaport', 'Northeast', 'Boston', 'MA', '5G', 'MAINTENANCE', 42.3467, -71.042, '2022-12-11'),
    ('GA-118', 'Atlanta Buckhead', 'Southeast', 'Atlanta', 'GA', '5G', 'OPERATIONAL', 33.838, -84.379, '2021-05-27'),
    ('FL-090', 'Miami Beach', 'Southeast', 'Miami', 'FL', '4G LTE', 'OFFLINE', 25.7907, -80.13, '2017-08-19'),
    ('CA-640', 'San Jose Downtown', 'West', 'San Jose', 'CA', '5G', 'OPERATIONAL', 37.3382, -121.8863, '2024-05-03');

-- network_outages
INSERT INTO network_outages (
    outage_id, region, severity, start_time, end_time, duration_hours, affected_customers, root_cause, status, description
) VALUES
    ('OUT-2026-0912', 'Midwest', 'CRITICAL', '2026-09-12 02:10:00', '2026-09-12 08:10:00', 6.0, 8500, 'Fiber backhaul cut on the Chicago metro ring', 'RESOLVED', 'Complete loss of 4G and 5G voice and data across the Midwest after a fiber cut on the Chicago metro ring. Continuous duration 6 hours. 8500 customers affected. This is the only 6-hour outage in the log. The CRITICAL MTTR target is 4 hours; this event missed it.'),
    ('OUT-2026-0908', 'Midwest', 'CRITICAL', '2026-09-08 01:00:00', '2026-09-08 03:00:00', 2.0, 5200, 'Bad software push on the Midwest packet gateway', 'RESOLVED', 'A software push took the Midwest packet gateway down. 5200 customers lost voice and data for 2 hours. CRITICAL because more than 5000 customers were affected. Not the 6-hour fiber event.'),
    ('OUT-2026-0811', 'Midwest', 'CRITICAL', '2026-08-11 11:00:00', '2026-08-11 14:30:00', 3.5, 4200, 'Power failure at the Chicago packet gateway', 'RESOLVED', 'Chicago packet gateway lost utility and generator power. 4200 Midwest customers lost voice and data for 3.5 hours. CRITICAL because a regional packet gateway failed.'),
    ('OUT-2026-0702', 'Midwest', 'CRITICAL', '2026-07-02 19:15:00', '2026-07-02 21:30:00', 2.25, 2100, 'Software fault on the regional mobility controller', 'RESOLVED', 'A bad configuration on the Midwest mobility controller dropped registration for 2100 customers for 2.25 hours. CRITICAL because the regional controller failed.'),
    ('OUT-2026-0614', 'Midwest', 'CRITICAL', '2026-06-14 04:00:00', '2026-06-14 05:12:00', 1.2, 5600, 'Metro fiber ring flap in Chicago', 'RESOLVED', 'The Chicago metro ring flapped. 5600 customers lost service for 1.2 hours. CRITICAL because the customer count was over 5000. Restored inside the 4-hour MTTR target.'),
    ('OUT-2026-0402', 'Midwest', 'CRITICAL', '2026-04-02 13:00:00', '2026-04-02 16:00:00', 3.0, 3000, 'Packet gateway hardware failure in Columbus', 'RESOLVED', 'A Columbus packet gateway card failed. 3000 customers lost service for 3 hours. CRITICAL because a regional gateway failed, even though the customer count was under 5000.'),
    ('OUT-2026-0819', 'Northeast', 'CRITICAL', '2026-08-19 01:00:00', '2026-08-19 05:00:00', 4.0, 6100, 'Manhattan fiber splice failure', 'RESOLVED', 'A failed splice in Manhattan took Midtown and nearby sectors offline for 4 hours. 6100 Northeast customers lost voice and data.'),
    ('OUT-2026-0312', 'Northeast', 'CRITICAL', '2026-03-12 06:30:00', '2026-03-12 09:00:00', 2.5, 1500, 'Regional mobility controller restart in New York', 'RESOLVED', 'The Northeast mobility controller restarted uncleanly. 1500 customers could not register for 2.5 hours. CRITICAL because the regional controller failed.'),
    ('OUT-2026-0901', 'Southeast', 'CRITICAL', '2026-09-01 16:20:00', '2026-09-01 17:50:00', 1.5, 1800, 'Commercial power loss and generator fail-to-start in Miami', 'RESOLVED', 'Miami Beach and adjacent sectors lost power for 1.5 hours. 1800 customers had no voice or data. Declared CRITICAL because restoration was expected to exceed 60 minutes and service was fully down. Separate from the later open incident on FL-090.'),
    ('OUT-2026-0903', 'Midwest', 'MAJOR', '2026-09-03 06:00:00', '2026-09-03 11:00:00', 5.0, 900, 'Backhaul congestion at Columbus Metro', 'RESOLVED', 'MAJOR Midwest event. Backhaul congestion at Columbus Metro. Duration 5.0 hours. 900 customers affected. Status RESOLVED.'),
    ('OUT-2026-0728', 'Midwest', 'MAJOR', '2026-07-28 15:00:00', '2026-07-28 19:30:00', 4.5, 1100, 'Chicago South Shore backhaul congestion', 'RESOLVED', 'MAJOR Midwest event. Chicago South Shore backhaul congestion. Duration 4.5 hours. 1100 customers affected. Status RESOLVED.'),
    ('OUT-2026-0507', 'Midwest', 'MAJOR', '2026-05-07 08:00:00', '2026-05-07 10:30:00', 2.5, 800, 'Columbus sector radio reboot', 'RESOLVED', 'MAJOR Midwest event. Columbus sector radio reboot. Duration 2.5 hours. 800 customers affected. Status RESOLVED.'),
    ('OUT-2026-0916', 'Midwest', 'MINOR', '2026-09-16 12:00:00', '2026-09-16 13:00:00', 1.0, 220, 'Brief interference near Chicago Loop', 'RESOLVED', 'MINOR Midwest event. Brief interference near Chicago Loop. Duration 1.0 hours. 220 customers affected. Status RESOLVED.'),
    ('OUT-2026-0829', 'Midwest', 'MINOR', '2026-08-29 07:10:00', '2026-08-29 07:28:00', 0.3, 45, 'Short microwave fade outside Chicago', 'RESOLVED', 'MINOR Midwest event. Short microwave fade outside Chicago. Duration 0.3 hours. 45 customers affected. Status RESOLVED.'),
    ('OUT-2026-0601', 'Midwest', 'MINOR', '2026-06-01 09:00:00', '2026-06-01 09:30:00', 0.5, 90, 'Brief microwave fade on a rural spur', 'RESOLVED', 'MINOR Midwest event. Brief microwave fade on a rural spur. Duration 0.5 hours. 90 customers affected. Status RESOLVED.'),
    ('OUT-2026-0218', 'Midwest', 'MINOR', '2026-02-18 18:00:00', '2026-02-18 18:48:00', 0.8, 140, 'Ice on a Columbus microwave dish', 'RESOLVED', 'MINOR Midwest event. Ice on a Columbus microwave dish. Duration 0.8 hours. 140 customers affected. Status RESOLVED.'),
    ('OUT-2026-0115', 'Midwest', 'MINOR', '2026-01-15 11:00:00', '2026-01-15 11:24:00', 0.4, 60, 'Maintenance window overrun of 24 minutes in Chicago', 'RESOLVED', 'MINOR Midwest event. Maintenance window overrun of 24 minutes in Chicago. Duration 0.4 hours. 60 customers affected. Status RESOLVED.'),
    ('OUT-2026-0914', 'Northeast', 'MAJOR', '2026-09-14 17:00:00', '2026-09-14 18:30:00', 1.5, 700, 'Manhattan Midtown sector congestion', 'RESOLVED', 'MAJOR Northeast event. Manhattan Midtown sector congestion. Duration 1.5 hours. 700 customers affected. Status RESOLVED.'),
    ('OUT-2026-0625', 'Northeast', 'MAJOR', '2026-06-25 13:00:00', '2026-06-25 15:00:00', 2.0, 650, 'Boston backhaul card replacement overrun', 'RESOLVED', 'MAJOR Northeast event. Boston backhaul card replacement overrun. Duration 2.0 hours. 650 customers affected. Status RESOLVED.'),
    ('OUT-2026-0220', 'Northeast', 'MAJOR', '2026-02-20 09:00:00', '2026-02-20 12:00:00', 3.0, 900, 'New York transport ring congestion', 'RESOLVED', 'MAJOR Northeast event. New York transport ring congestion. Duration 3.0 hours. 900 customers affected. Status RESOLVED.'),
    ('OUT-2026-0802', 'Northeast', 'MINOR', '2026-08-02 10:00:00', '2026-08-02 10:24:00', 0.4, 55, 'Short power blip at a Boston sector', 'RESOLVED', 'MINOR Northeast event. Short power blip at a Boston sector. Duration 0.4 hours. 55 customers affected. Status RESOLVED.'),
    ('OUT-2026-0715', 'Northeast', 'MINOR', '2026-07-15 13:10:00', '2026-07-15 13:40:00', 0.5, 120, 'Boston Seaport antenna swap ran past the announced window', 'RESOLVED', 'MINOR Northeast event. Boston Seaport antenna swap ran past the announced window. Duration 0.5 hours. 120 customers affected. Status RESOLVED.'),
    ('OUT-2026-0418', 'Northeast', 'MINOR', '2026-04-18 16:00:00', '2026-04-18 16:36:00', 0.6, 100, 'Localized interference in Midtown', 'RESOLVED', 'MINOR Northeast event. Localized interference in Midtown. Duration 0.6 hours. 100 customers affected. Status RESOLVED.'),
    ('OUT-2026-0110', 'Northeast', 'MINOR', '2026-01-10 08:20:00', '2026-01-10 08:50:00', 0.5, 70, 'Snow on a Manhattan antenna', 'RESOLVED', 'MINOR Northeast event. Snow on a Manhattan antenna. Duration 0.5 hours. 70 customers affected. Status RESOLVED.'),
    ('OUT-2026-0917', 'Southeast', 'MAJOR', '2026-09-17 19:00:00', '2026-09-17 20:12:00', 1.2, 540, 'Atlanta Buckhead evening congestion', 'RESOLVED', 'MAJOR Southeast event. Atlanta Buckhead evening congestion. Duration 1.2 hours. 540 customers affected. Status RESOLVED.'),
    ('OUT-2026-0719', 'Southeast', 'MAJOR', '2026-07-19 14:00:00', '2026-07-19 17:30:00', 3.5, 1200, 'Atlanta transport microwave fade', 'RESOLVED', 'MAJOR Southeast event. Atlanta transport microwave fade. Duration 3.5 hours. 1200 customers affected. Status RESOLVED.'),
    ('OUT-2026-0322', 'Southeast', 'MAJOR', '2026-03-22 11:00:00', '2026-03-22 13:12:00', 2.2, 800, 'Storm damage to an Atlanta sector', 'RESOLVED', 'MAJOR Southeast event. Storm damage to an Atlanta sector. Duration 2.2 hours. 800 customers affected. Status RESOLVED.'),
    ('OUT-2026-0910', 'Southeast', 'MINOR', '2026-09-10 08:00:00', '2026-09-10 09:00:00', 1.0, 200, 'Atlanta Buckhead sector tilt after a storm', 'RESOLVED', 'MINOR Southeast event. Atlanta Buckhead sector tilt after a storm. Duration 1.0 hours. 200 customers affected. Status RESOLVED.'),
    ('OUT-2026-0825', 'Southeast', 'MINOR', '2026-08-25 15:30:00', '2026-08-25 16:24:00', 0.9, 150, 'Miami sector alarm cleared by reset', 'RESOLVED', 'MINOR Southeast event. Miami sector alarm cleared by reset. Duration 0.9 hours. 150 customers affected. Status RESOLVED.'),
    ('OUT-2026-0512', 'Southeast', 'MINOR', '2026-05-12 06:00:00', '2026-05-12 06:30:00', 0.5, 60, 'Short generator test that dropped one Miami sector', 'RESOLVED', 'MINOR Southeast event. Short generator test that dropped one Miami sector. Duration 0.5 hours. 60 customers affected. Status RESOLVED.'),
    ('OUT-2026-0130', 'Southeast', 'MINOR', '2026-01-30 20:00:00', '2026-01-30 20:42:00', 0.7, 90, 'Evening interference in Atlanta', 'RESOLVED', 'MINOR Southeast event. Evening interference in Atlanta. Duration 0.7 hours. 90 customers affected. Status RESOLVED.'),
    ('OUT-2026-0906', 'Southwest', 'MAJOR', '2026-09-06 18:00:00', '2026-09-06 19:48:00', 1.8, 820, 'Dallas Uptown capacity exhaust', 'RESOLVED', 'MAJOR Southwest event. Dallas Uptown capacity exhaust. Duration 1.8 hours. 820 customers affected. Status RESOLVED.'),
    ('OUT-2026-0822', 'Southwest', 'MAJOR', '2026-08-22 18:00:00', '2026-08-22 20:00:00', 2.0, 740, 'Dallas Uptown radio unit reboot loop', 'RESOLVED', 'MAJOR Southwest event. Dallas Uptown radio unit reboot loop. Duration 2.0 hours. 740 customers affected. Status RESOLVED.'),
    ('OUT-2026-0708', 'Southwest', 'MAJOR', '2026-07-08 12:00:00', '2026-07-08 16:00:00', 4.0, 1500, 'Austin backhaul congestion across two sectors', 'RESOLVED', 'MAJOR Southwest event. Austin backhaul congestion across two sectors. Duration 4.0 hours. 1500 customers affected. Status RESOLVED.'),
    ('OUT-2026-0318', 'Southwest', 'MAJOR', '2026-03-18 09:30:00', '2026-03-18 11:30:00', 2.0, 600, 'Dallas transport card fault', 'RESOLVED', 'MAJOR Southwest event. Dallas transport card fault. Duration 2.0 hours. 600 customers affected. Status RESOLVED.'),
    ('OUT-2026-0920', 'Southwest', 'MINOR', '2026-09-20 07:00:00', '2026-09-20 07:36:00', 0.6, 95, 'Short Austin Riverside alarm, service stayed up', 'RESOLVED', 'MINOR Southwest event. Short Austin Riverside alarm, service stayed up. Duration 0.6 hours. 95 customers affected. Status RESOLVED.'),
    ('OUT-2026-0815', 'Southwest', 'MINOR', '2026-08-15 21:00:00', '2026-08-15 21:18:00', 0.3, 35, 'Brief Dallas sector reset', 'RESOLVED', 'MINOR Southwest event. Brief Dallas sector reset. Duration 0.3 hours. 35 customers affected. Status RESOLVED.'),
    ('OUT-2026-0519', 'Southwest', 'MINOR', '2026-05-19 13:00:00', '2026-05-19 13:48:00', 0.8, 110, 'Wind misalignment on a Dallas antenna', 'RESOLVED', 'MINOR Southwest event. Wind misalignment on a Dallas antenna. Duration 0.8 hours. 110 customers affected. Status RESOLVED.'),
    ('OUT-2026-0204', 'Southwest', 'MINOR', '2026-02-04 10:00:00', '2026-02-04 10:24:00', 0.4, 40, 'Localized interference in north Austin', 'RESOLVED', 'MINOR Southwest event. Localized interference in north Austin. Duration 0.4 hours. 40 customers affected. Status RESOLVED.'),
    ('OUT-2026-0918', 'West', 'MAJOR', '2026-09-18 12:00:00', '2026-09-18 13:00:00', 1.0, 400, 'San Jose Downtown backhaul maintenance overrun', 'RESOLVED', 'MAJOR West event. San Jose Downtown backhaul maintenance overrun. Duration 1.0 hours. 400 customers affected. Status RESOLVED.'),
    ('OUT-2026-0909', 'West', 'MAJOR', '2026-09-09 16:00:00', '2026-09-09 18:06:00', 2.1, 640, 'San Jose evening capacity exhaust', 'RESOLVED', 'MAJOR West event. San Jose evening capacity exhaust. Duration 2.1 hours. 640 customers affected. Status RESOLVED.'),
    ('OUT-2026-0610', 'West', 'MAJOR', '2026-06-10 11:00:00', '2026-06-10 14:12:00', 3.2, 980, 'San Jose transport ring congestion', 'RESOLVED', 'MAJOR West event. San Jose transport ring congestion. Duration 3.2 hours. 980 customers affected. Status RESOLVED.'),
    ('OUT-2026-0303', 'West', 'MAJOR', '2026-03-03 08:00:00', '2026-03-03 10:24:00', 2.4, 700, 'San Jose radio software rollback', 'RESOLVED', 'MAJOR West event. San Jose radio software rollback. Duration 2.4 hours. 700 customers affected. Status RESOLVED.'),
    ('OUT-2026-0921', 'West', 'MINOR', '2026-09-21 09:00:00', '2026-09-21 09:18:00', 0.3, 40, 'Short interference near San Jose Downtown', 'RESOLVED', 'MINOR West event. Short interference near San Jose Downtown. Duration 0.3 hours. 40 customers affected. Status RESOLVED.'),
    ('OUT-2026-0808', 'West', 'MINOR', '2026-08-08 07:00:00', '2026-08-08 07:45:00', 0.75, 80, 'Localized interference near San Jose Downtown', 'RESOLVED', 'MINOR West event. Localized interference near San Jose Downtown. Duration 0.75 hours. 80 customers affected. Status RESOLVED.'),
    ('OUT-2026-0722', 'West', 'MINOR', '2026-07-22 19:10:00', '2026-07-22 19:52:00', 0.7, 130, 'Evening noise rise in San Jose', 'RESOLVED', 'MINOR West event. Evening noise rise in San Jose. Duration 0.7 hours. 130 customers affected. Status RESOLVED.'),
    ('OUT-2026-0428', 'West', 'MINOR', '2026-04-28 06:30:00', '2026-04-28 06:54:00', 0.4, 80, 'Fog fade on a San Jose microwave hop', 'RESOLVED', 'MINOR West event. Fog fade on a San Jose microwave hop. Duration 0.4 hours. 80 customers affected. Status RESOLVED.'),
    ('OUT-2026-0118', 'West', 'MINOR', '2026-01-18 14:00:00', '2026-01-18 14:30:00', 0.5, 50, 'Short power blip at San Jose Downtown', 'RESOLVED', 'MINOR West event. Short power blip at San Jose Downtown. Duration 0.5 hours. 50 customers affected. Status RESOLVED.'),
    ('OUT-2026-0922', 'West', 'MINOR', '2026-09-22 22:00:00', NULL, 0.5, 30, 'Interference under investigation near San Jose', 'ONGOING', 'MINOR West event still open. Interference under investigation near San Jose. Duration so far 0.5 hours. 30 customers affected. Not a full regional outage.');

-- tower_performance: 8 samples per tower. Query the max recorded_at per tower.
INSERT INTO tower_performance (
    performance_id, tower_id, recorded_at, latency_ms, packet_loss_pct, downlink_throughput_mbps, uplink_throughput_mbps, signal_strength_dbm, active_connections
) VALUES
    (1, 'TX-512', '2026-09-21 08:15:00', 24, 0.4, 720, 48, -74, 380),
    (2, 'TX-512', '2026-09-21 14:15:00', 25, 0.5, 700, 46, -73, 400),
    (3, 'TX-512', '2026-09-21 20:15:00', 26, 0.6, 680, 44, -74, 420),
    (4, 'TX-512', '2026-09-22 02:15:00', 28, 0.7, 650, 42, -75, 450),
    (5, 'TX-512', '2026-09-22 08:15:00', 30, 0.9, 600, 40, -74, 480),
    (6, 'TX-512', '2026-09-22 14:15:00', 38, 1.8, 380, 28, -73, 520),
    (7, 'TX-512', '2026-09-22 20:15:00', 46, 2.6, 180, 18, -72, 590),
    (8, 'TX-512', '2026-09-23 08:15:00', 58, 3.8, 85, 12, -72, 640),
    (9, 'TX-208', '2026-09-21 08:15:00', 60, 6.1, 70, 10, -94, 200),
    (10, 'TX-208', '2026-09-21 14:15:00', 64, 6.4, 66, 9, -95, 210),
    (11, 'TX-208', '2026-09-21 20:15:00', 68, 6.8, 60, 8, -95, 220),
    (12, 'TX-208', '2026-09-22 02:15:00', 70, 7.0, 58, 8, -96, 230),
    (13, 'TX-208', '2026-09-22 08:15:00', 74, 7.4, 52, 7, -96, 240),
    (14, 'TX-208', '2026-09-22 14:15:00', 78, 7.9, 48, 6, -97, 245),
    (15, 'TX-208', '2026-09-22 20:15:00', 82, 8.2, 44, 6, -97, 250),
    (16, 'TX-208', '2026-09-23 08:15:00', 88, 8.6, 40, 5, -98, 260),
    (17, 'IL-104', '2026-09-21 08:15:00', 22, 0.2, 740, 55, -67, 760),
    (18, 'IL-104', '2026-09-21 14:15:00', 23, 0.2, 730, 54, -68, 780),
    (19, 'IL-104', '2026-09-21 20:15:00', 23, 0.3, 720, 53, -68, 800),
    (20, 'IL-104', '2026-09-22 02:15:00', 24, 0.3, 710, 52, -68, 820),
    (21, 'IL-104', '2026-09-22 08:15:00', 24, 0.3, 710, 52, -68, 800),
    (22, 'IL-104', '2026-09-22 14:15:00', 25, 0.3, 700, 50, -69, 830),
    (23, 'IL-104', '2026-09-22 20:15:00', 25, 0.4, 695, 50, -69, 850),
    (24, 'IL-104', '2026-09-23 08:15:00', 26, 0.4, 690, 49, -69, 860),
    (25, 'IL-221', '2026-09-21 08:15:00', 50, 3.2, 28, 8, -92, 160),
    (26, 'IL-221', '2026-09-21 14:15:00', 54, 3.5, 26, 7, -93, 165),
    (27, 'IL-221', '2026-09-21 20:15:00', 58, 3.8, 24, 7, -94, 170),
    (28, 'IL-221', '2026-09-22 02:15:00', 62, 4.1, 22, 6, -95, 175),
    (29, 'IL-221', '2026-09-22 08:15:00', 66, 4.4, 20, 6, -95, 180),
    (30, 'IL-221', '2026-09-22 14:15:00', 68, 4.8, 18, 5, -96, 182),
    (31, 'IL-221', '2026-09-22 20:15:00', 71, 5.1, 16, 5, -96, 186),
    (32, 'IL-221', '2026-09-23 08:15:00', 74, 5.4, 15, 4, -97, 190),
    (33, 'OH-077', '2026-09-21 08:15:00', 20, 0.1, 780, 58, -65, 280),
    (34, 'OH-077', '2026-09-21 14:15:00', 21, 0.1, 770, 57, -65, 290),
    (35, 'OH-077', '2026-09-21 20:15:00', 21, 0.2, 760, 56, -66, 300),
    (36, 'OH-077', '2026-09-22 02:15:00', 22, 0.2, 760, 56, -66, 300),
    (37, 'OH-077', '2026-09-22 08:15:00', 22, 0.2, 750, 55, -66, 305),
    (38, 'OH-077', '2026-09-22 14:15:00', 22, 0.2, 745, 55, -67, 310),
    (39, 'OH-077', '2026-09-22 20:15:00', 23, 0.2, 740, 54, -67, 315),
    (40, 'OH-077', '2026-09-23 08:15:00', 23, 0.2, 740, 54, -67, 320),
    (41, 'NY-301', '2026-09-21 08:15:00', 11, 0.1, 1500, 96, -70, 500),
    (42, 'NY-301', '2026-09-21 14:15:00', 12, 0.2, 1460, 94, -70, 520),
    (43, 'NY-301', '2026-09-21 20:15:00', 12, 0.2, 1420, 92, -71, 540),
    (44, 'NY-301', '2026-09-22 02:15:00', 12, 0.2, 1400, 90, -71, 540),
    (45, 'NY-301', '2026-09-22 08:15:00', 13, 0.2, 1380, 88, -72, 560),
    (46, 'NY-301', '2026-09-22 14:15:00', 13, 0.3, 1360, 86, -72, 580),
    (47, 'NY-301', '2026-09-22 20:15:00', 14, 0.3, 1340, 85, -73, 600),
    (48, 'NY-301', '2026-09-23 08:15:00', 14, 0.3, 1320, 84, -73, 610),
    (49, 'MA-055', '2026-09-21 08:15:00', 28, 0.4, 520, 32, -74, 90),
    (50, 'MA-055', '2026-09-21 14:15:00', 28, 0.4, 510, 30, -74, 80),
    (51, 'MA-055', '2026-09-21 20:15:00', 29, 0.5, 500, 30, -75, 40),
    (52, 'MA-055', '2026-09-22 02:15:00', 30, 0.5, 480, 28, -75, 35),
    (53, 'MA-055', '2026-09-22 08:15:00', 30, 0.5, 400, 22, -76, 30),
    (54, 'MA-055', '2026-09-22 14:15:00', 32, 0.5, 250, 16, -77, 22),
    (55, 'MA-055', '2026-09-22 20:15:00', 34, 0.6, 120, 12, -77, 16),
    (56, 'MA-055', '2026-09-23 08:15:00', 35, 0.6, 80, 10, -78, 12),
    (57, 'GA-118', '2026-09-21 08:15:00', 24, 0.3, 720, 52, -69, 420),
    (58, 'GA-118', '2026-09-21 14:15:00', 25, 0.3, 710, 51, -69, 430),
    (59, 'GA-118', '2026-09-21 20:15:00', 26, 0.4, 700, 50, -70, 440),
    (60, 'GA-118', '2026-09-22 02:15:00', 27, 0.4, 690, 49, -70, 450),
    (61, 'GA-118', '2026-09-22 08:15:00', 27, 0.4, 680, 48, -70, 450),
    (62, 'GA-118', '2026-09-22 14:15:00', 28, 0.4, 670, 47, -71, 460),
    (63, 'GA-118', '2026-09-22 20:15:00', 28, 0.5, 665, 47, -71, 465),
    (64, 'GA-118', '2026-09-23 08:15:00', 29, 0.5, 660, 46, -71, 470),
    (65, 'FL-090', '2026-09-21 08:15:00', 38, 0.9, 58, 8, -86, 180),
    (66, 'FL-090', '2026-09-21 14:15:00', 40, 1.0, 55, 8, -87, 190),
    (67, 'FL-090', '2026-09-21 20:15:00', 36, 0.8, 60, 9, -88, 175),
    (68, 'FL-090', '2026-09-22 02:15:00', 42, 1.1, 52, 7, -87, 200),
    (69, 'FL-090', '2026-09-22 08:15:00', 40, 1.0, 55, 8, -88, 188),
    (70, 'FL-090', '2026-09-22 14:15:00', 44, 1.4, 48, 7, -89, 170),
    (71, 'FL-090', '2026-09-22 20:15:00', 41, 1.2, 50, 8, -88, 160),
    (72, 'FL-090', '2026-09-23 08:15:00', 0, 100.0, 0, 0, -120, 0),
    (73, 'CA-640', '2026-09-21 08:15:00', 19, 0.2, 830, 62, -64, 340),
    (74, 'CA-640', '2026-09-21 14:15:00', 20, 0.2, 820, 61, -64, 350),
    (75, 'CA-640', '2026-09-21 20:15:00', 20, 0.2, 810, 60, -65, 360),
    (76, 'CA-640', '2026-09-22 02:15:00', 21, 0.3, 800, 60, -65, 370),
    (77, 'CA-640', '2026-09-22 08:15:00', 21, 0.3, 800, 60, -65, 380),
    (78, 'CA-640', '2026-09-22 14:15:00', 21, 0.3, 795, 59, -66, 385),
    (79, 'CA-640', '2026-09-22 20:15:00', 22, 0.3, 792, 59, -66, 390),
    (80, 'CA-640', '2026-09-23 08:15:00', 22, 0.3, 790, 58, -66, 400);

-- open_incidents
INSERT INTO open_incidents (
    incident_id, tower_id, severity, status, title, description, opened_at, classification, assigned_team
) VALUES
    ('INC-8841', 'TX-512', 'MAJOR', 'INVESTIGATING', 'Intermittent 5G session drops at Austin Riverside', 'Tower TX-512 remains OPERATIONAL. The latest signal is -72 dBm, which is acceptable, but packet loss has climbed through the week to 3.8 percent and 5G downlink has fallen to 85 Mbps. Subscribers report sessions dropping near this site. Suspected radio scheduler or backhaul congestion. Not a full site outage and not a handset-only fault. Yesterday''s samples were still near normal.', '2026-09-22 14:40:00', 'RADIO_ACCESS', 'NOC Southwest'),
    ('INC-8790', 'TX-208', 'MAJOR', 'OPEN', 'Dallas Uptown degraded capacity', 'TX-208 is DEGRADED. Latest packet loss is 8.6 percent and signal is -98 dBm, which is marginal. Loss has been severe all week, so this is not a one-sample blip. Field dispatch is waiting on a replacement radio unit. Customers in Uptown Dallas should expect slow or dropping 5G until the unit is swapped.', '2026-09-20 09:05:00', 'RADIO_ACCESS', 'NOC Southwest'),
    ('INC-8702', 'FL-090', 'CRITICAL', 'OPEN', 'Miami Beach site offline after power failure', 'FL-090 is OFFLINE as of the 2026-09-23 08:15 sample. Packet loss is 100 percent, throughput is zero, and signal is -120 dBm. Earlier samples that week still showed the 4G LTE site carrying traffic, so an average across the week hides the outage. Commercial power failed and the generator did not start. A field technician is on site. This is a new failure, separate from resolved outage OUT-2026-0901 on 1 September. Nearby Atlanta capacity does not cover Miami Beach.', '2026-09-23 06:50:00', 'POWER', 'NOC Southeast'),
    ('INC-8810', 'IL-221', 'MINOR', 'MONITORING', 'Chicago South Shore LTE packet loss', 'IL-221 is a 4G LTE site in DEGRADED status. Latest packet loss is 5.4 percent and downlink is 15 Mbps. The site is still carrying traffic. Monitoring before a truck roll. This is not the 12 September Midwest regional outage OUT-2026-0912 and it is not the Chicago Loop 5G site IL-104, which is healthy.', '2026-09-21 22:15:00', 'BACKHAUL', 'NOC Midwest'),
    ('INC-8820', 'MA-055', 'MINOR', 'MONITORING', 'Planned maintenance at Boston Seaport', 'MA-055 is in MAINTENANCE for a scheduled radio software upgrade announced 72 hours ahead. The window runs through 2026-09-23 18:00:00. Throughput and active connections are intentionally low. This is not an unplanned outage and does not by itself qualify customers for an SLA credit.', '2026-09-23 05:00:00', 'PLANNED_MAINTENANCE', 'NOC Northeast'),
    ('INC-8833', 'OH-077', 'MINOR', 'MONITORING', 'Columbus Metro alarm watch after a cleared power dip', 'OH-077 is OPERATIONAL. Latest samples are healthy: packet loss 0.2 percent, downlink about 740 Mbps, signal -67 dBm. A power dip cleared on its own. The incident stays in MONITORING until 2026-09-24 08:00:00. Do not tell the customer the Columbus site is down.', '2026-09-22 04:10:00', 'POWER', 'NOC Midwest'),
    ('INC-8850', 'CA-640', 'MINOR', 'INVESTIGATING', 'San Jose Downtown external interference', 'CA-640 is OPERATIONAL and the latest sample is healthy (packet loss 0.3 percent, downlink about 790 Mbps, signal -66 dBm). A separate ONGOING minor outage OUT-2026-0922 is investigating intermittent interference that has not yet moved the latest KPIs out of the normal range. Keep watching the next sample before dispatching.', '2026-09-22 22:05:00', 'RADIO_ACCESS', 'NOC West');

-- customer_subscriptions
INSERT INTO customer_subscriptions (
    subscription_id, customer_id, customer_name, account_type, plan_name, monthly_fee, region, city, state, status, line_count, start_date
) VALUES
    ('SUB-10002', 'CUST-10002', 'Alex Romero', 'Consumer', 'Unlimited Plus', 65.99, 'Southwest', 'Austin', 'TX', 'ACTIVE', 1, '2024-02-01'),
    ('SUB-10008', 'CUST-10008', 'Maya Chen', 'Consumer', 'Unlimited Plus', 65.99, 'Northeast', 'Boston', 'MA', 'ACTIVE', 1, '2023-11-01'),
    ('SUB-10011', 'CUST-10011', 'Derek Holt', 'Business', 'Business Unlimited', 89.99, 'Midwest', 'Indianapolis', 'IN', 'ACTIVE', 6, '2022-08-15'),
    ('SUB-10015', 'CUST-10015', 'Priya Nair', 'Business', 'Business Unlimited', 89.99, 'Midwest', 'Chicago', 'IL', 'ACTIVE', 8, '2023-06-15'),
    ('SUB-10018', 'CUST-10018', 'Sam Okonkwo', 'Enterprise', 'Enterprise Mobile', 249.0, 'Midwest', 'Columbus', 'OH', 'ACTIVE', 40, '2022-01-10'),
    ('SUB-10021', 'CUST-10021', 'Elena Vasquez', 'Consumer', 'Unlimited Essential', 45.0, 'Northeast', 'New York', 'NY', 'ACTIVE', 1, '2025-03-01'),
    ('SUB-10027', 'CUST-10027', 'Chris Dalton', 'Consumer', '5G Home', 50.0, 'Southeast', 'Miami', 'FL', 'ACTIVE', 1, '2024-11-20'),
    ('SUB-10033', 'CUST-10033', 'Jordan Blake', 'Business', 'Business Unlimited', 89.99, 'West', 'San Jose', 'CA', 'ACTIVE', 5, '2023-09-01'),
    ('SUB-10040', 'CUST-10040', 'Riley Nguyen', 'Consumer', 'Unlimited Plus', 65.99, 'Midwest', 'Chicago', 'IL', 'ACTIVE', 2, '2025-01-12'),
    ('SUB-10044', 'CUST-10044', 'Morgan Ellis', 'Consumer', 'Unlimited Essential', 45.0, 'Southwest', 'Dallas', 'TX', 'ACTIVE', 1, '2024-07-08'),
    ('SUB-10052', 'CUST-10052', 'Nina Patel', 'Consumer', 'Unlimited Essential', 45.0, 'West', 'Sacramento', 'CA', 'SUSPENDED', 1, '2024-04-01'),
    ('SUB-10060', 'CUST-10060', 'Omar Farouk', 'Enterprise', 'Enterprise Mobile', 249.0, 'Northeast', 'New York', 'NY', 'ACTIVE', 25, '2021-05-01'),
    ('SUB-10071', 'CUST-10071', 'Grace Kim', 'Consumer', 'Unlimited Plus', 65.99, 'Southeast', 'Atlanta', 'GA', 'ACTIVE', 1, '2023-02-14'),
    ('SUB-10077', 'CUST-10077', 'Luis Ortega', 'Consumer', 'Unlimited Plus', 65.99, 'Southwest', 'Austin', 'TX', 'ACTIVE', 1, '2025-06-01'),
    ('SUB-10083', 'CUST-10083', 'Hannah Brooks', 'Business', 'Business Unlimited', 89.99, 'Southeast', 'Atlanta', 'GA', 'ACTIVE', 4, '2024-01-20'),
    ('SUB-10090', 'CUST-10090', 'Wei Zhang', 'Consumer', '5G Home', 50.0, 'Midwest', 'Chicago', 'IL', 'ACTIVE', 1, '2025-09-01'),
    ('SUB-10102', 'CUST-10102', 'Fatima Diallo', 'Consumer', 'Unlimited Essential', 45.0, 'Midwest', 'Columbus', 'OH', 'ACTIVE', 1, '2024-10-01'),
    ('SUB-10115', 'CUST-10115', 'Noah Schwartz', 'Business', 'Business Unlimited', 89.99, 'Northeast', 'Boston', 'MA', 'ACTIVE', 3, '2023-12-01'),
    ('SUB-10120', 'CUST-10120', 'Aisha Rahman', 'Enterprise', 'Enterprise Mobile', 249.0, 'Southwest', 'Dallas', 'TX', 'ACTIVE', 18, '2022-07-01'),
    ('SUB-10128', 'CUST-10128', 'Ben Carter', 'Consumer', 'Unlimited Plus', 65.99, 'West', 'San Jose', 'CA', 'ACTIVE', 1, '2024-03-18'),
    ('SUB-10136', 'CUST-10136', 'Sofia Alvarez', 'Consumer', 'Unlimited Plus', 65.99, 'Southeast', 'Miami', 'FL', 'ACTIVE', 1, '2025-02-02'),
    ('SUB-10144', 'CUST-10144', 'Greg Howell', 'Consumer', 'Unlimited Essential', 45.0, 'Northeast', 'New York', 'NY', 'CANCELLED', 1, '2023-01-09'),
    ('SUB-10158', 'CUST-10158', 'Colin Wright', 'Consumer', 'Unlimited Plus', 65.99, 'Southwest', 'Houston', 'TX', 'ACTIVE', 1, '2024-08-22'),
    ('SUB-10166', 'CUST-10166', 'Helen Cho', 'Business', 'Business Unlimited', 89.99, 'Midwest', 'Detroit', 'MI', 'ACTIVE', 7, '2022-11-11'),
    ('SUB-10172', 'CUST-10172', 'Victor Almeida', 'Consumer', 'Unlimited Plus', 65.99, 'Southeast', 'Orlando', 'FL', 'ACTIVE', 1, '2025-05-05'),
    ('SUB-10180', 'CUST-10180', 'Diane Cooper', 'Enterprise', 'Enterprise Mobile', 249.0, 'West', 'San Jose', 'CA', 'ACTIVE', 12, '2021-09-30'),
    ('SUB-10190', 'CUST-10190', 'Ava Singh', 'Consumer', 'Unlimited Essential', 45.0, 'Northeast', 'New York', 'NY', 'ACTIVE', 1, '2026-09-01');

-- billing_accounts. current_balance equals the OPEN charges for that customer.
INSERT INTO billing_accounts (
    customer_id, customer_name, account_type, current_balance, currency, service_region, city, state, billing_cycle, auto_pay_enabled, account_status, last_updated
) VALUES
    ('CUST-10002', 'Alex Romero', 'Consumer', 131.98, 'USD', 'Southwest', 'Austin', 'TX', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10008', 'Maya Chen', 'Consumer', 137.99, 'USD', 'Northeast', 'Boston', 'MA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10011', 'Derek Holt', 'Business', 249.99, 'USD', 'Midwest', 'Indianapolis', 'IN', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10015', 'Priya Nair', 'Business', 89.99, 'USD', 'Midwest', 'Chicago', 'IL', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10018', 'Sam Okonkwo', 'Enterprise', 249.0, 'USD', 'Midwest', 'Columbus', 'OH', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10021', 'Elena Vasquez', 'Consumer', 45.0, 'USD', 'Northeast', 'New York', 'NY', 'Monthly, closes on the 1st', 0, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10027', 'Chris Dalton', 'Consumer', 74.0, 'USD', 'Southeast', 'Miami', 'FL', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10033', 'Jordan Blake', 'Business', 89.99, 'USD', 'West', 'San Jose', 'CA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10040', 'Riley Nguyen', 'Consumer', 65.99, 'USD', 'Midwest', 'Chicago', 'IL', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10044', 'Morgan Ellis', 'Consumer', 45.0, 'USD', 'Southwest', 'Dallas', 'TX', 'Monthly, closes on the 1st', 0, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10052', 'Nina Patel', 'Consumer', 75.0, 'USD', 'West', 'Sacramento', 'CA', 'Monthly, closes on the 1st', 0, 'SUSPENDED', '2026-09-23 00:05:00'),
    ('CUST-10060', 'Omar Farouk', 'Enterprise', 249.0, 'USD', 'Northeast', 'New York', 'NY', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10071', 'Grace Kim', 'Consumer', 65.99, 'USD', 'Southeast', 'Atlanta', 'GA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10077', 'Luis Ortega', 'Consumer', 65.99, 'USD', 'Southwest', 'Austin', 'TX', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10083', 'Hannah Brooks', 'Business', 89.99, 'USD', 'Southeast', 'Atlanta', 'GA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10090', 'Wei Zhang', 'Consumer', 50.0, 'USD', 'Midwest', 'Chicago', 'IL', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10102', 'Fatima Diallo', 'Consumer', 45.0, 'USD', 'Midwest', 'Columbus', 'OH', 'Monthly, closes on the 1st', 0, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10115', 'Noah Schwartz', 'Business', 89.99, 'USD', 'Northeast', 'Boston', 'MA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10120', 'Aisha Rahman', 'Enterprise', 249.0, 'USD', 'Southwest', 'Dallas', 'TX', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10128', 'Ben Carter', 'Consumer', 165.99, 'USD', 'West', 'San Jose', 'CA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10136', 'Sofia Alvarez', 'Consumer', 125.99, 'USD', 'Southeast', 'Miami', 'FL', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10144', 'Greg Howell', 'Consumer', 0.0, 'USD', 'Northeast', 'New York', 'NY', 'Monthly, closes on the 1st', 0, 'CLOSED', '2026-08-31 00:05:00'),
    ('CUST-10158', 'Colin Wright', 'Consumer', 71.4, 'USD', 'Southwest', 'Houston', 'TX', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10166', 'Helen Cho', 'Business', 89.99, 'USD', 'Midwest', 'Detroit', 'MI', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10172', 'Victor Almeida', 'Consumer', 84.39, 'USD', 'Southeast', 'Orlando', 'FL', 'Monthly, closes on the 1st', 0, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10180', 'Diane Cooper', 'Enterprise', 249.0, 'USD', 'West', 'San Jose', 'CA', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00'),
    ('CUST-10190', 'Ava Singh', 'Consumer', 45.0, 'USD', 'Northeast', 'New York', 'NY', 'Monthly, closes on the 1st', 1, 'ACTIVE', '2026-09-23 00:05:00');

-- billing_charges. OPEN rows are the September bill. PAID rows are history.
-- A monthly plan charge in a new period is not a duplicate of last month.
INSERT INTO billing_charges (
    charge_id, customer_id, description, amount, billing_period, charge_date, charge_type, is_duplicate_flag, invoice_status
) VALUES
    ('CHG-50021', 'CUST-10002', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50022', 'CUST-10002', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 1, 'OPEN'),
    ('CHG-50030', 'CUST-10015', 'Business Unlimited', 89.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50040', 'CUST-10018', 'Enterprise Mobile', 249.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50050', 'CUST-10021', 'Unlimited Essential', 45.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50060', 'CUST-10027', '5G Home', 50.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50061', 'CUST-10027', 'International Day Pass', 12.0, '2026-09', '2026-09-15', 'ADDON', 0, 'OPEN'),
    ('CHG-50062', 'CUST-10027', 'International Day Pass', 12.0, '2026-09', '2026-09-15', 'ADDON', 1, 'OPEN'),
    ('CHG-50070', 'CUST-10033', 'Business Unlimited', 89.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50080', 'CUST-10040', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-50090', 'CUST-10044', 'Unlimited Essential', 45.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51008', 'CUST-10008', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51009', 'CUST-10008', 'Japan pay-per-use data', 36.0, '2026-09', '2026-09-18', 'ROAMING', 0, 'OPEN'),
    ('CHG-51010', 'CUST-10008', 'Japan pay-per-use data', 36.0, '2026-09', '2026-09-18', 'ROAMING', 1, 'OPEN'),
    ('CHG-51011', 'CUST-10011', 'Business Unlimited', 89.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51012', 'CUST-10011', 'Device installment', 80.0, '2026-09', '2026-09-01', 'DEVICE', 0, 'OPEN'),
    ('CHG-51013', 'CUST-10011', 'Device installment', 80.0, '2026-09', '2026-09-01', 'DEVICE', 1, 'OPEN'),
    ('CHG-51052', 'CUST-10052', 'Unlimited Essential', 45.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51053', 'CUST-10052', 'Late fee', 30.0, '2026-09', '2026-09-05', 'FEE', 0, 'OPEN'),
    ('CHG-51060', 'CUST-10060', 'Enterprise Mobile', 249.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51071', 'CUST-10071', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51077', 'CUST-10077', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51083', 'CUST-10083', 'Business Unlimited', 89.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51090', 'CUST-10090', '5G Home', 50.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51102', 'CUST-10102', 'Unlimited Essential', 45.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51115', 'CUST-10115', 'Business Unlimited', 89.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51120', 'CUST-10120', 'Enterprise Mobile', 249.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51128', 'CUST-10128', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51129', 'CUST-10128', 'Travel Pass Zone B 5-day bundle', 50.0, '2026-09', '2026-09-10', 'ADDON', 0, 'OPEN'),
    ('CHG-51130', 'CUST-10128', 'Travel Pass Zone B 5-day bundle', 50.0, '2026-09', '2026-09-10', 'ADDON', 1, 'OPEN'),
    ('CHG-51136', 'CUST-10136', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51137', 'CUST-10136', 'Travel Pass Zone C Japan, 5 days', 60.0, '2026-09', '2026-09-12', 'ROAMING', 0, 'OPEN'),
    ('CHG-51158', 'CUST-10158', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51159', 'CUST-10158', 'Texas sales tax', 5.41, '2026-09', '2026-09-01', 'TAX', 0, 'OPEN'),
    ('CHG-51166', 'CUST-10166', 'Business Unlimited', 89.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51172', 'CUST-10172', 'Unlimited Plus', 65.99, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51173', 'CUST-10172', 'Brazil pay-per-use data', 18.4, '2026-09', '2026-09-08', 'ROAMING', 0, 'OPEN'),
    ('CHG-51180', 'CUST-10180', 'Enterprise Mobile', 249.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-51190', 'CUST-10190', 'Unlimited Essential', 45.0, '2026-09', '2026-09-01', 'PLAN', 0, 'OPEN'),
    ('CHG-H07-10002', 'CUST-10002', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10002', 'CUST-10002', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10008', 'CUST-10008', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10008', 'CUST-10008', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10011', 'CUST-10011', 'Business Unlimited', 89.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10011', 'CUST-10011', 'Business Unlimited', 89.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10015', 'CUST-10015', 'Business Unlimited', 89.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10015', 'CUST-10015', 'Business Unlimited', 89.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10018', 'CUST-10018', 'Enterprise Mobile', 249.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10018', 'CUST-10018', 'Enterprise Mobile', 249.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10021', 'CUST-10021', 'Unlimited Essential', 45.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10021', 'CUST-10021', 'Unlimited Essential', 45.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10027', 'CUST-10027', '5G Home', 50.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10027', 'CUST-10027', '5G Home', 50.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10033', 'CUST-10033', 'Business Unlimited', 89.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10033', 'CUST-10033', 'Business Unlimited', 89.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10040', 'CUST-10040', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10040', 'CUST-10040', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10044', 'CUST-10044', 'Unlimited Essential', 45.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10044', 'CUST-10044', 'Unlimited Essential', 45.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10052', 'CUST-10052', 'Unlimited Essential', 45.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10052', 'CUST-10052', 'Unlimited Essential', 45.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10060', 'CUST-10060', 'Enterprise Mobile', 249.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10060', 'CUST-10060', 'Enterprise Mobile', 249.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10071', 'CUST-10071', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10071', 'CUST-10071', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10077', 'CUST-10077', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10077', 'CUST-10077', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10083', 'CUST-10083', 'Business Unlimited', 89.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10083', 'CUST-10083', 'Business Unlimited', 89.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10090', 'CUST-10090', '5G Home', 50.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10090', 'CUST-10090', '5G Home', 50.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10102', 'CUST-10102', 'Unlimited Essential', 45.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10102', 'CUST-10102', 'Unlimited Essential', 45.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10115', 'CUST-10115', 'Business Unlimited', 89.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10115', 'CUST-10115', 'Business Unlimited', 89.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10120', 'CUST-10120', 'Enterprise Mobile', 249.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10120', 'CUST-10120', 'Enterprise Mobile', 249.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10128', 'CUST-10128', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10128', 'CUST-10128', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10136', 'CUST-10136', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10136', 'CUST-10136', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10144', 'CUST-10144', 'Unlimited Essential', 45.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10144', 'CUST-10144', 'Unlimited Essential', 45.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10158', 'CUST-10158', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10158', 'CUST-10158', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10166', 'CUST-10166', 'Business Unlimited', 89.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10166', 'CUST-10166', 'Business Unlimited', 89.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10172', 'CUST-10172', 'Unlimited Plus', 65.99, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10172', 'CUST-10172', 'Unlimited Plus', 65.99, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-H07-10180', 'CUST-10180', 'Enterprise Mobile', 249.0, '2026-07', '2026-07-01', 'PLAN', 0, 'PAID'),
    ('CHG-H08-10180', 'CUST-10180', 'Enterprise Mobile', 249.0, '2026-08', '2026-08-01', 'PLAN', 0, 'PAID'),
    ('CHG-48002', 'CUST-10002', 'Mexico pay-per-use data', 22.0, '2026-08', '2026-08-14', 'ROAMING', 0, 'PAID'),
    ('CHG-48071', 'CUST-10071', 'Premium voicemail', 10.0, '2026-08', '2026-08-01', 'ADDON', 0, 'PAID'),
    ('CHG-48072', 'CUST-10071', 'Premium voicemail', 10.0, '2026-08', '2026-08-01', 'ADDON', 1, 'PAID'),
    ('CHG-48040', 'CUST-10040', 'Spotify premium add-on', 10.0, '2026-08', '2026-08-01', 'ADDON', 0, 'PAID'),
    ('CHG-48041', 'CUST-10040', 'Spotify premium add-on', 10.0, '2026-08', '2026-08-01', 'ADDON', 1, 'PAID'),
    ('CHG-47021', 'CUST-10021', 'Late fee', 15.0, '2026-07', '2026-07-20', 'FEE', 0, 'PAID'),
    ('CHG-48015', 'CUST-10015', 'Travel Pass Zone B', 5.0, '2026-08', '2026-08-20', 'ROAMING', 0, 'PAID'),
    ('CHG-48060', 'CUST-10060', 'Travel Pass Zone C Japan, 3 days', 36.0, '2026-08', '2026-08-11', 'ROAMING', 0, 'PAID'),
    ('CHG-47018', 'CUST-10018', 'Static IP add-on', 15.0, '2026-07', '2026-07-01', 'ADDON', 0, 'PAID'),
    ('CHG-48083', 'CUST-10083', 'Device installment', 40.0, '2026-08', '2026-08-01', 'DEVICE', 0, 'PAID');

-- billing_credits. APPLIED rows point at PAID charges and do not change current_balance.
-- There is no credit yet for CUST-10002, CUST-10027, CUST-10008, CUST-10011, or CUST-10128.
INSERT INTO billing_credits (
    credit_id, customer_id, amount, reason, status, created_at, related_charge_id
) VALUES
    (1, 'CUST-10033', 75.0, 'August 2026 device installment dispute. Amount is above the 50.00 USD auto-approval limit, so the credit is waiting for a billing supervisor. Balance was not reduced.', 'PENDING_APPROVAL', '2026-09-18 15:30:00', NULL),
    (2, 'CUST-10002', 22.0, 'Unlimited Plus includes Zone A Mexico. August pay-per-use data on CHG-48002 was billed in error and was already credited. Do not credit it again.', 'APPLIED', '2026-08-20 11:00:00', 'CHG-48002'),
    (3, 'CUST-10071', 10.0, 'Duplicate Premium voicemail add-on for 2026-08 (CHG-48072). Credit already applied on the paid bill. Do not credit it again.', 'APPLIED', '2026-08-25 09:30:00', 'CHG-48072'),
    (4, 'CUST-10040', 10.0, 'Duplicate Spotify premium add-on for 2026-08 (CHG-48041). Credit already applied on the paid bill.', 'APPLIED', '2026-08-19 14:00:00', 'CHG-48041'),
    (5, 'CUST-10021', 15.0, 'Requested credit for a July late fee. Denied because the payment posted after the due date. Balance was not reduced.', 'REJECTED', '2026-08-20 16:00:00', 'CHG-47021'),
    (6, 'CUST-10018', 15.0, 'July static IP add-on was ordered and then cancelled inside the same cycle. Credit applied on the paid July bill.', 'APPLIED', '2026-07-28 10:15:00', 'CHG-47018');

-- billing_disputes
INSERT INTO billing_disputes (
    dispute_id, customer_id, charge_id, reason, status, opened_at, resolved_at, resolution_notes
) VALUES
    ('DSP-2026-10002', 'CUST-10002', 'CHG-50022', 'Charged twice for Unlimited Plus in billing period 2026-09. The second line is flagged as a duplicate. No credit has been posted.', 'OPEN', '2026-09-21 11:20:00', NULL, NULL),
    ('DSP-2026-10027', 'CUST-10027', 'CHG-50062', 'International Day Pass posted twice on 2026-09-15. Amount 12.00 is within the auto-approval limit. No credit has been posted yet.', 'OPEN', '2026-09-22 09:00:00', NULL, NULL),
    ('DSP-2026-10008', 'CUST-10008', 'CHG-51010', 'Japan pay-per-use data posted twice on 2026-09-18. Amount 36.00 is within the auto-approval limit. No credit has been posted yet.', 'OPEN', '2026-09-22 16:40:00', NULL, NULL),
    ('DSP-2026-10011', 'CUST-10011', 'CHG-51013', 'Device installment posted twice for 2026-09. Amount 80.00 is above the 50.00 auto-approval limit. No credit has been posted yet.', 'ESCALATED', '2026-09-19 13:15:00', NULL, 'Waiting on a billing supervisor because the duplicate amount is over 50.00 USD.'),
    ('DSP-2026-10128', 'CUST-10128', 'CHG-51130', 'Travel Pass Zone B 5-day bundle posted twice on 2026-09-10. Amount is exactly 50.00, which does not exceed the auto-approval limit. No credit has been posted yet.', 'OPEN', '2026-09-20 10:00:00', NULL, NULL),
    ('DSP-2026-10033', 'CUST-10033', NULL, 'Disputes a 75.00 USD device installment from August 2026. Credit 1 is PENDING_APPROVAL. The September balance has not been reduced.', 'ESCALATED', '2026-09-18 15:10:00', NULL, 'Credit row 1 is PENDING_APPROVAL. Balance has not been reduced.'),
    ('DSP-2026-0904', 'CUST-10021', 'CHG-47021', 'Disputed a 15.00 late fee from July 2026.', 'RESOLVED', '2026-08-02 10:00:00', '2026-08-20 16:00:00', 'Denied. Credit 5 is REJECTED. The payment posted after the due date.'),
    ('DSP-2026-0814', 'CUST-10002', 'CHG-48002', 'Mexico pay-per-use data in August. Unlimited Plus includes Zone A.', 'RESOLVED', '2026-08-16 09:00:00', '2026-08-20 11:00:00', 'Credit 2 was APPLIED for 22.00 on the paid August bill. Do not credit CHG-48002 again.'),
    ('DSP-2026-0871', 'CUST-10071', 'CHG-48072', 'Premium voicemail posted twice in August.', 'RESOLVED', '2026-08-22 12:00:00', '2026-08-25 09:30:00', 'Credit 3 was APPLIED for 10.00. The September bill has a single Unlimited Plus charge and no open duplicate.'),
    ('DSP-2026-0840', 'CUST-10040', 'CHG-48041', 'Spotify premium add-on posted twice in August.', 'RESOLVED', '2026-08-18 08:30:00', '2026-08-19 14:00:00', 'Credit 4 was APPLIED for 10.00 on the paid bill.'),
    ('DSP-2026-10136', 'CUST-10136', 'CHG-51137', 'Customer was surprised by a 60.00 Japan Travel Pass. Five Zone C days at 12.00 each. The charge matches the roaming policy and is not a duplicate.', 'RESOLVED', '2026-09-15 11:00:00', '2026-09-16 15:00:00', 'Denied. Published Zone C Travel Pass rate. No credit.'),
    ('DSP-2026-10172', 'CUST-10172', 'CHG-51173', 'Customer disputes 18.40 of Brazil pay-per-use data. One line only, Zone D published rate, inside the 60-day window, not a duplicate.', 'OPEN', '2026-09-22 18:00:00', NULL, 'Not a duplicate. Do not credit a published Zone D rate unless the roaming policy was misapplied.');

COMMIT;
