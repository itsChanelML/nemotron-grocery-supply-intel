# backend/lib/bigquery.py
# Google Cloud BigQuery client for Orchaid
# Reads live warehouse telemetry to ground agent system prompts
#
# Tables (in dataset orchaid_warehouse):
#   equipment_readings   — sensor telemetry, anomaly scores
#   inventory_snapshot   — SKU-level spoilage risk scoring
#   compliance_events    — FDA/OSHA violations and recall matches
#   document_log         — BOL discrepancies, lot mismatches, missing docs

import os
import json
from typing import Optional
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
DATASET    = os.getenv("GCP_BIGQUERY_DATASET", "orchaid_warehouse")


def get_bq_client() -> bigquery.Client:
    """
    Return a BigQuery client with correct credentials.
    Handles both local (file path) and Cloud Run (JSON string) auth.
    """
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(project=PROJECT_ID, credentials=credentials)
    # Local: GOOGLE_APPLICATION_CREDENTIALS file path auto-detected
    return bigquery.Client(project=PROJECT_ID)


def get_equipment_telemetry() -> list[dict]:
    """
    Fetch latest equipment sensor readings.
    Grounds the Equipment Agent system prompt with live data.
    """
    client = get_bq_client()
    query = f"""
        SELECT sensor_id, asset_name, zone, metric, value,
               baseline, threshold, unit, status, anomaly_score, timestamp
        FROM `{PROJECT_ID}.{DATASET}.equipment_readings`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
        ORDER BY anomaly_score DESC, timestamp DESC
        LIMIT 50
    """
    rows = client.query(query).result()
    return [dict(row) for row in rows]


def get_inventory_snapshot() -> list[dict]:
    """
    Fetch current inventory with spoilage scores.
    Grounds the Forecasting Agent system prompt with live data.
    """
    client = get_bq_client()
    query = f"""
        SELECT sku_id, product_name, category, zone, qty_on_hand,
               dwell_hours, expiry_date, vendor, velocity_7d_avg,
               reorder_point, spoilage_risk_score, markdown_recommended
        FROM `{PROJECT_ID}.{DATASET}.inventory_snapshot`
        WHERE spoilage_risk_score > 0.3 OR dwell_hours > 48
        ORDER BY spoilage_risk_score DESC
        LIMIT 30
    """
    rows = client.query(query).result()
    return [dict(row) for row in rows]


def get_compliance_events() -> list[dict]:
    """
    Fetch recent compliance events.
    Grounds the Safety Agent system prompt with live data.
    """
    client = get_bq_client()
    query = f"""
        SELECT event_id, event_type, zone, observed_value,
               threshold_value, unit, severity, status,
               regulation_ref, timestamp
        FROM `{PROJECT_ID}.{DATASET}.compliance_events`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ORDER BY
            CASE severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                ELSE 4
            END,
            timestamp DESC
        LIMIT 20
    """
    rows = client.query(query).result()
    return [dict(row) for row in rows]


def get_document_log() -> list[dict]:
    """
    Fetch recent BOL and document records.
    Grounds the Document Agent system prompt with live data.
    """
    client = get_bq_client()
    query = f"""
        SELECT bol_id, vendor, shipment_date, invoiced_qty,
               received_qty, qty_delta, lot_number, po_lot_number,
               temp_log_present, status, flags
        FROM `{PROJECT_ID}.{DATASET}.document_log`
        WHERE shipment_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        ORDER BY
            CASE status
                WHEN 'FLAGGED' THEN 1
                WHEN 'DISPUTED' THEN 2
                WHEN 'QUARANTINED' THEN 3
                WHEN 'PENDING' THEN 4
                ELSE 5
            END,
            shipment_date DESC
        LIMIT 25
    """
    rows = client.query(query).result()
    return [dict(row) for row in rows]
