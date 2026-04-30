-- data/schema/bigquery_schema.sql
-- Orchaid — nemotron-grocery-supply-intel
-- BigQuery dataset: orchaid_warehouse
-- Run this to create the schema before seeding with synthetic data

-- ─────────────────────────────────────────────────────────────
-- 1. EQUIPMENT READINGS
-- Sensor telemetry from refrigeration units, AMRs, conveyors
-- Partitioned by day for cost-efficient querying
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `orchaid_warehouse.equipment_readings` (
  sensor_id       STRING NOT NULL,
  asset_type      STRING NOT NULL,  -- 'refrigeration' | 'amr' | 'conveyor' | 'dock_door'
  asset_name      STRING NOT NULL,  -- e.g. 'R-12', 'AMR-07', 'Line C-3'
  zone            STRING,           -- e.g. 'Dairy', 'Produce', 'Frozen'
  metric          STRING NOT NULL,  -- e.g. 'compressor_cycle_ms', 'odometry_drift_cm'
  value           FLOAT64 NOT NULL,
  baseline        FLOAT64,          -- Expected/spec value for anomaly scoring
  threshold       FLOAT64,          -- Alert threshold
  unit            STRING,           -- 'ms', 'cm', 'pct', 'degF', 'sec'
  status          STRING NOT NULL,  -- 'NOMINAL' | 'WARNING' | 'CRITICAL'
  anomaly_score   FLOAT64,          -- 0.0 to 1.0 — from cuML anomaly detection
  timestamp       TIMESTAMP NOT NULL
)
PARTITION BY DATE(timestamp)
OPTIONS (
  description = "Equipment sensor readings — partitioned daily, queried per 2-hour window"
);

-- ─────────────────────────────────────────────────────────────
-- 2. INVENTORY SNAPSHOT
-- Current SKU-level inventory state with spoilage scoring
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `orchaid_warehouse.inventory_snapshot` (
  sku_id              STRING NOT NULL,
  product_name        STRING NOT NULL,
  category            STRING,         -- 'produce' | 'dairy' | 'meat' | 'frozen' | 'bakery'
  subcategory         STRING,
  zone                STRING,
  qty_on_hand         INT64 NOT NULL,
  unit_of_measure     STRING,         -- 'units' | 'cases' | 'pallets'
  dwell_hours         FLOAT64,        -- Time in DC since receipt
  received_date       DATE,
  expiry_date         DATE,
  days_to_expiry      INT64,
  vendor              STRING,
  velocity_7d_avg     FLOAT64,        -- Average daily units sold over last 7 days
  velocity_30d_avg    FLOAT64,
  reorder_point       INT64,
  spoilage_risk_score FLOAT64,        -- 0.0 to 1.0 — model-scored
  markdown_recommended BOOL,
  snapshot_timestamp  TIMESTAMP NOT NULL
)
PARTITION BY DATE(snapshot_timestamp)
OPTIONS (
  description = "SKU-level inventory with spoilage risk scores — refreshed every 5 minutes"
);

-- ─────────────────────────────────────────────────────────────
-- 3. COMPLIANCE EVENTS
-- FDA and OSHA compliance log — all violations, breaches, audits
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `orchaid_warehouse.compliance_events` (
  event_id          STRING NOT NULL,
  event_type        STRING NOT NULL,  -- 'temperature_breach' | 'proximity_event' | 'recall_match' | 'cert_expiry' | 'haccp_audit'
  zone              STRING,
  asset_id          STRING,           -- e.g. 'R-12', 'AMR-07', 'Door-7'
  observed_value    FLOAT64,
  threshold_value   FLOAT64,
  unit              STRING,
  severity          STRING NOT NULL,  -- 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  status            STRING NOT NULL,  -- 'OPEN' | 'DOCUMENTED' | 'RESOLVED' | 'ESCALATED'
  regulation_ref    STRING,           -- e.g. '21 CFR 117.93', 'OSHA 1910.178'
  auto_documented   BOOL DEFAULT TRUE,
  notes             STRING,
  resolved_at       TIMESTAMP,
  timestamp         TIMESTAMP NOT NULL
)
PARTITION BY DATE(timestamp)
OPTIONS (
  description = "FDA/OSHA compliance events — all violations and audits, append-only"
);

-- ─────────────────────────────────────────────────────────────
-- 4. DOCUMENT LOG
-- BOL, invoice, and purchase order tracking
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `orchaid_warehouse.document_log` (
  bol_id            STRING NOT NULL,
  doc_type          STRING NOT NULL,  -- 'BOL' | 'INVOICE' | 'PO' | 'RECALL_NOTICE'
  vendor            STRING NOT NULL,
  shipment_date     DATE,
  received_date     DATE,
  product_category  STRING,
  product_name      STRING,
  invoiced_qty      INT64,
  received_qty      INT64,
  qty_delta         INT64,            -- received - invoiced (negative = shortage)
  qty_delta_value   FLOAT64,          -- estimated dollar value of delta
  lot_number        STRING,           -- Lot number on the BOL
  po_lot_number     STRING,           -- Lot number specified in the PO
  lot_mismatch      BOOL,
  temp_log_present  BOOL,
  cold_chain_req    BOOL,             -- Does this shipment require cold chain docs?
  status            STRING NOT NULL,  -- 'APPROVED' | 'PENDING' | 'FLAGGED' | 'DISPUTED' | 'QUARANTINED'
  flags             ARRAY<STRING>,    -- e.g. ['qty_discrepancy', 'missing_temp_log', 'lot_mismatch']
  recall_match      BOOL DEFAULT FALSE,
  recall_number     STRING,           -- FDA recall number if matched
  gcs_uri           STRING,           -- gs:// path to original PDF in Cloud Storage
  document_ai_job   STRING,           -- Document AI batch job ID
  created_at        TIMESTAMP NOT NULL,
  updated_at        TIMESTAMP
)
PARTITION BY DATE(shipment_date)
OPTIONS (
  description = "BOL and invoice document log — all shipment records with Document AI extraction results"
);

-- ─────────────────────────────────────────────────────────────
-- USEFUL VIEWS
-- ─────────────────────────────────────────────────────────────

-- High-risk inventory (for Forecasting Agent)
CREATE OR REPLACE VIEW `orchaid_warehouse.v_high_risk_inventory` AS
SELECT *
FROM `orchaid_warehouse.inventory_snapshot`
WHERE spoilage_risk_score > 0.5
   OR days_to_expiry <= 3
   OR dwell_hours > 72
ORDER BY spoilage_risk_score DESC;

-- Open compliance events (for Safety Agent)
CREATE OR REPLACE VIEW `orchaid_warehouse.v_open_compliance` AS
SELECT *
FROM `orchaid_warehouse.compliance_events`
WHERE status IN ('OPEN', 'ESCALATED')
ORDER BY
  CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
  timestamp DESC;

-- Flagged documents (for Document Agent)
CREATE OR REPLACE VIEW `orchaid_warehouse.v_flagged_documents` AS
SELECT *
FROM `orchaid_warehouse.document_log`
WHERE status IN ('FLAGGED', 'DISPUTED', 'QUARANTINED')
ORDER BY updated_at DESC;
