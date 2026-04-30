# backend/api/telemetry.py
# Warehouse telemetry endpoint
# Demo mode: reads from data/synthetic/*.json
# Production: queries BigQuery via lib/bigquery.py

import os
import json
from pathlib import Path
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter()

IS_DEMO = (
    not os.getenv("GCP_PROJECT_ID") or
    os.getenv("GCP_PROJECT_ID") == "your-gcp-project-id"
)

SYNTHETIC_DIR = Path(__file__).parent.parent / "data" / "synthetic"


def load_synthetic(filename: str) -> list:
    try:
        return json.loads((SYNTHETIC_DIR / filename).read_text())
    except Exception:
        return []


@router.get("")
async def get_telemetry(
    type: str = Query(default="all", description="equipment|inventory|compliance|documents|all")
):
    """
    Serve warehouse telemetry to the frontend.
    Demo mode reads from synthetic JSON files.
    Production queries BigQuery directly.
    """
    payload = {
        "source":     "synthetic" if IS_DEMO else "bigquery",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }

    if IS_DEMO:
        if type in ("equipment", "all"):
            payload["equipment"]  = load_synthetic("equipment_readings.json")
        if type in ("inventory", "all"):
            payload["inventory"]  = load_synthetic("inventory_snapshot.json")
        if type in ("compliance", "all"):
            payload["compliance"] = load_synthetic("compliance_events.json")
        if type in ("documents", "all"):
            payload["documents"]  = load_synthetic("bol_documents.json")
        return payload

    # Production — BigQuery
    from lib.bigquery import (
        get_equipment_telemetry,
        get_inventory_snapshot,
        get_compliance_events,
        get_document_log,
    )

    if type in ("equipment", "all"):
        payload["equipment"]  = get_equipment_telemetry()
    if type in ("inventory", "all"):
        payload["inventory"]  = get_inventory_snapshot()
    if type in ("compliance", "all"):
        payload["compliance"] = get_compliance_events()
    if type in ("documents", "all"):
        payload["documents"]  = get_document_log()

    return payload


@router.get("")
async def get_telemetry_cached(type: str = "all"):
    return await get_telemetry(type=type)
