#!/usr/bin/env python3
"""
data/synthetic/generate_telemetry.py
Orchaid — nemotron-grocery-supply-intel

Generates realistic synthetic warehouse telemetry for Stater Bros. DC.
Outputs JSON files for demo mode AND optionally seeds BigQuery directly.

Usage:
  python3 data/synthetic/generate_telemetry.py          # JSON only
  python3 data/synthetic/generate_telemetry.py --bigquery  # JSON + BigQuery
"""

import json
import random
import argparse
from datetime import datetime, timedelta, date
from pathlib import Path

random.seed(42)  # Reproducible synthetic data

OUTPUT_DIR = Path(__file__).parent

# ─── Equipment Readings ───────────────────────────────────────────────────────

REFRIGERATION_UNITS = [
    {"id": f"R-{i:02d}", "zone": z, "baseline_cycle_ms": 290, "threshold_cycle_ms": 320}
    for i, z in enumerate([
        "Dairy", "Dairy", "Produce", "Produce", "Frozen", "Frozen",
        "Meat", "Meat", "Seafood", "Bakery", "Beverage", "Floral",
    ], 1)
]

AMR_FLEET = [
    {"id": f"AMR-{i:02d}", "baseline_drift_cm": 1.0, "threshold_drift_cm": 2.5}
    for i in range(1, 15)
]

def generate_equipment_readings():
    records = []
    now = datetime.utcnow()

    for unit in REFRIGERATION_UNITS:
        # R-12 has a known anomaly
        if unit["id"] == "R-12":
            cycle_ms = round(random.gauss(340, 5), 1)
            status = "WARNING"
            anomaly_score = round(random.uniform(0.65, 0.75), 3)
        elif unit["id"] == "R-03":
            cycle_ms = round(random.gauss(295, 3), 1)
            status = "NOMINAL"
            anomaly_score = round(random.uniform(0.1, 0.2), 3)
        else:
            cycle_ms = round(random.gauss(unit["baseline_cycle_ms"], 4), 1)
            status = "NOMINAL" if cycle_ms < unit["threshold_cycle_ms"] else "WARNING"
            anomaly_score = round(random.uniform(0.05, 0.25), 3)

        records.append({
            "sensor_id": f"SENS-REF-{unit['id']}",
            "asset_type": "refrigeration",
            "asset_name": unit["id"],
            "zone": unit["zone"],
            "metric": "compressor_cycle_ms",
            "value": cycle_ms,
            "baseline": unit["baseline_cycle_ms"],
            "threshold": unit["threshold_cycle_ms"],
            "unit": "ms",
            "status": status,
            "anomaly_score": anomaly_score,
            "timestamp": (now - timedelta(minutes=random.randint(0, 30))).isoformat() + "Z",
        })

        # Door seal reading for R-03 (Produce)
        if unit["id"] == "R-03":
            records.append({
                "sensor_id": f"SENS-SEAL-{unit['id']}",
                "asset_type": "refrigeration",
                "asset_name": unit["id"],
                "zone": unit["zone"],
                "metric": "door_seal_integrity_pct",
                "value": round(random.gauss(91, 0.5), 1),
                "baseline": 100.0,
                "threshold": 95.0,
                "unit": "pct",
                "status": "WARNING",
                "anomaly_score": round(random.uniform(0.4, 0.5), 3),
                "timestamp": (now - timedelta(minutes=random.randint(0, 15))).isoformat() + "Z",
            })

    for amr in AMR_FLEET:
        # AMR-07 has drift anomaly
        if amr["id"] == "AMR-07":
            drift = round(random.gauss(3.2, 0.2), 2)
            status = "WARNING"
            anomaly_score = round(random.uniform(0.7, 0.8), 3)
        elif amr["id"] == "AMR-11":
            drift = round(random.gauss(1.1, 0.1), 2)
            status = "NOMINAL"
            anomaly_score = round(random.uniform(0.05, 0.15), 3)
        else:
            drift = round(random.gauss(amr["baseline_drift_cm"], 0.15), 2)
            status = "NOMINAL" if drift < amr["threshold_drift_cm"] else "WARNING"
            anomaly_score = round(random.uniform(0.05, 0.2), 3)

        records.append({
            "sensor_id": f"SENS-AMR-{amr['id']}",
            "asset_type": "amr",
            "asset_name": amr["id"],
            "zone": "Warehouse Floor",
            "metric": "odometry_drift_cm",
            "value": drift,
            "baseline": amr["baseline_drift_cm"],
            "threshold": amr["threshold_drift_cm"],
            "unit": "cm",
            "status": status,
            "anomaly_score": anomaly_score,
            "timestamp": (now - timedelta(minutes=random.randint(0, 20))).isoformat() + "Z",
        })

        # Battery for AMR-11
        if amr["id"] == "AMR-11":
            records.append({
                "sensor_id": f"SENS-BAT-{amr['id']}",
                "asset_type": "amr",
                "asset_name": amr["id"],
                "zone": "Charging Bay",
                "metric": "battery_capacity_pct",
                "value": round(random.gauss(71, 1.5), 1),
                "baseline": 94.0,
                "threshold": 80.0,
                "unit": "pct",
                "status": "WARNING",
                "anomaly_score": round(random.uniform(0.45, 0.55), 3),
                "timestamp": (now - timedelta(minutes=random.randint(0, 10))).isoformat() + "Z",
            })

    return records


# ─── Inventory Snapshot ───────────────────────────────────────────────────────

PRODUCTS = [
    # (sku_id, name, category, vendor, avg_velocity, spoilage_days)
    ("SKU-4821", "Atlantic Salmon Fillets 2lb", "meat_seafood", "Pacific Seafood", 180, 5),
    ("SKU-1104", "Organic Romaine Hearts 3pk", "produce", "Fresh Express", 420, 7),
    ("SKU-2203", "Bagged Spring Mix 5oz", "produce", "Earthbound Farm", 380, 6),
    ("SKU-3301", "Cut Fruit Medley 32oz", "produce", "Ready Pac Foods", 210, 4),
    ("SKU-0892", "Rotisserie Chicken", "deli", "Stater Bros. Kitchen", 95, 3),
    ("SKU-5512", "Greek Yogurt 32oz (Chobani)", "dairy", "Chobani", 290, 21),
    ("SKU-6601", "Sourdough Bread Loaf", "bakery", "Franz Bakery", 340, 4),
    ("SKU-7703", "Whole Milk Gallon", "dairy", "Clover Sonoma", 510, 14),
    ("SKU-8801", "Strawberries 1lb", "produce", "Driscoll's", 295, 5),
    ("SKU-9901", "Baby Spinach 6oz", "produce", "Taylor Farms", 260, 8),
    ("SKU-1205", "Chicken Breast 3lb", "meat_seafood", "Tyson Foods", 380, 5),
    ("SKU-2308", "Deli Turkey 1lb", "deli", "Boar's Head", 145, 7),
    ("SKU-3412", "Shredded Mozzarella 2lb", "dairy", "Lucerne", 220, 21),
    ("SKU-4516", "Fresh Orange Juice 52oz", "beverage", "Tropicana", 310, 14),
    ("SKU-5620", "Avocados 4pk", "produce", "Del Monte", 480, 6),
]

def compute_spoilage_score(dwell_hours, days_to_expiry, velocity_7d, reorder_pt):
    """Simple spoilage risk model — simulates cuML scoring"""
    dwell_factor = min(dwell_hours / 96, 1.0) * 0.4
    expiry_factor = max(0, (5 - days_to_expiry) / 5) * 0.4
    velocity_factor = max(0, 1 - (velocity_7d / reorder_pt)) * 0.2
    return round(min(dwell_factor + expiry_factor + velocity_factor, 1.0), 3)

def generate_inventory_snapshot():
    records = []
    now = datetime.utcnow()
    today = date.today()

    for sku_id, name, category, vendor, base_velocity, spoilage_days in PRODUCTS:
        # Salmon has a known spoilage issue
        if "Salmon" in name:
            dwell_hours = round(random.uniform(55, 65), 1)
            days_to_expiry = 2
            qty = random.randint(320, 360)
        elif "Romaine" in name:
            dwell_hours = round(random.uniform(30, 40), 1)
            days_to_expiry = random.randint(3, 5)
            qty = random.randint(300, 400)
        elif "Yogurt" in name:
            dwell_hours = round(random.uniform(18, 22), 1)
            days_to_expiry = random.randint(12, 16)
            qty = random.randint(140, 180)
        else:
            dwell_hours = round(random.uniform(4, 72), 1)
            days_to_expiry = random.randint(2, spoilage_days + 5)
            qty = random.randint(50, 600)

        velocity_7d = round(base_velocity * random.uniform(0.8, 1.4), 1)
        reorder_pt = int(base_velocity * 1.5)
        expiry_date = today + timedelta(days=days_to_expiry)
        spoilage_score = compute_spoilage_score(dwell_hours, days_to_expiry, velocity_7d, reorder_pt)

        records.append({
            "sku_id": sku_id,
            "product_name": name,
            "category": category,
            "zone": {"produce": "Produce", "dairy": "Dairy Cold", "meat_seafood": "Meat & Seafood",
                     "bakery": "Bakery", "deli": "Deli", "beverage": "Beverage"}.get(category, "General"),
            "qty_on_hand": qty,
            "unit_of_measure": "units",
            "dwell_hours": dwell_hours,
            "received_date": (today - timedelta(days=int(dwell_hours / 24))).isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "days_to_expiry": days_to_expiry,
            "vendor": vendor,
            "velocity_7d_avg": velocity_7d,
            "reorder_point": reorder_pt,
            "spoilage_risk_score": spoilage_score,
            "markdown_recommended": spoilage_score > 0.6 or days_to_expiry <= 2,
            "snapshot_timestamp": now.isoformat() + "Z",
        })

    return sorted(records, key=lambda r: r["spoilage_risk_score"], reverse=True)


# ─── Compliance Events ────────────────────────────────────────────────────────

def generate_compliance_events():
    now = datetime.utcnow()
    return [
        {
            "event_id": "EVT-2024-0091",
            "event_type": "recall_match",
            "zone": "Receiving Dock",
            "asset_id": "DOCK-RECEIVING",
            "observed_value": 340,
            "threshold_value": 0,
            "unit": "units",
            "severity": "CRITICAL",
            "status": "OPEN",
            "regulation_ref": "21 CFR 7.3(m) — Class II Recall",
            "auto_documented": True,
            "notes": "340 units romaine lettuce lot #RLT-2024-0891 match active FDA Class II recall. Quarantine pending.",
            "timestamp": (now - timedelta(hours=6)).isoformat() + "Z",
        },
        {
            "event_id": "EVT-2024-0089",
            "event_type": "temperature_breach",
            "zone": "Zone D-3",
            "asset_id": "R-08",
            "observed_value": 42.0,
            "threshold_value": 41.0,
            "unit": "degF",
            "severity": "HIGH",
            "status": "DOCUMENTED",
            "regulation_ref": "21 CFR 117.93 — Sanitation controls for human food",
            "auto_documented": True,
            "notes": "Zone D-3 logged 42°F for 11 minutes at 02:14. Auto-documented per FSMA protocol.",
            "timestamp": (now - timedelta(hours=7, minutes=46)).isoformat() + "Z",
        },
        {
            "event_id": "EVT-2024-0090",
            "event_type": "temperature_breach",
            "zone": "Zone F-7",
            "asset_id": "R-22",
            "observed_value": -14.0,
            "threshold_value": -10.0,
            "unit": "degF",
            "severity": "MEDIUM",
            "status": "DOCUMENTED",
            "regulation_ref": "21 CFR 117.93 — Sanitation controls for human food",
            "auto_documented": True,
            "notes": "Zone F-7 logged -14°F for 8 minutes at 04:47. Variance within equipment tolerance; documented.",
            "timestamp": (now - timedelta(hours=5, minutes=13)).isoformat() + "Z",
        },
        {
            "event_id": "EVT-2024-0088",
            "event_type": "proximity_event",
            "zone": "Warehouse Floor — Aisle C",
            "asset_id": "AMR-03",
            "observed_value": 1.2,
            "threshold_value": 1.5,
            "unit": "meters",
            "severity": "MEDIUM",
            "status": "DOCUMENTED",
            "regulation_ref": "OSHA 1910.178(l) — Powered industrial trucks",
            "auto_documented": True,
            "notes": "AMR-03 passed within 1.2m of warehouse associate. No contact. Third proximity event this shift.",
            "timestamp": (now - timedelta(hours=1, minutes=22)).isoformat() + "Z",
        },
        {
            "event_id": "EVT-2024-0085",
            "event_type": "cert_expiry",
            "zone": None,
            "asset_id": "EMP-0441",
            "observed_value": 14,
            "threshold_value": 30,
            "unit": "days_until_expiry",
            "severity": "LOW",
            "status": "OPEN",
            "regulation_ref": "OSHA 1910.178(l)(1) — Operator certification",
            "auto_documented": True,
            "notes": "2 forklift operators (EMP-0441, EMP-0387) have certifications expiring within 14 days. Renewal reminders sent.",
            "timestamp": (now - timedelta(hours=12)).isoformat() + "Z",
        },
    ]


# ─── Document Log (BOLs) ──────────────────────────────────────────────────────

def generate_bol_documents():
    today = date.today()
    return [
        {
            "bol_id": "BOL-74808",
            "doc_type": "BOL",
            "vendor": "Fresh Express",
            "shipment_date": (today - timedelta(days=2)).isoformat(),
            "received_date": (today - timedelta(days=2)).isoformat(),
            "product_category": "produce",
            "product_name": "Romaine Lettuce (bagged, various sizes)",
            "invoiced_qty": 340,
            "received_qty": 340,
            "qty_delta": 0,
            "qty_delta_value": 0.0,
            "lot_number": "RLT-2024-0891",
            "po_lot_number": "RLT-2024-0891",
            "lot_mismatch": False,
            "temp_log_present": True,
            "cold_chain_req": True,
            "status": "QUARANTINED",
            "flags": ["recall_match"],
            "recall_match": True,
            "recall_number": "F-2024-0033",
        },
        {
            "bol_id": "BOL-74821",
            "doc_type": "BOL",
            "vendor": "Del Monte",
            "shipment_date": (today - timedelta(days=2)).isoformat(),
            "received_date": (today - timedelta(days=2)).isoformat(),
            "product_category": "produce",
            "product_name": "Roma Tomatoes (cases)",
            "invoiced_qty": 480,
            "received_qty": 462,
            "qty_delta": -18,
            "qty_delta_value": -340.0,
            "lot_number": "DMT-2024-1102",
            "po_lot_number": "DMT-2024-1102",
            "lot_mismatch": False,
            "temp_log_present": True,
            "cold_chain_req": False,
            "status": "DISPUTED",
            "flags": ["qty_discrepancy"],
            "recall_match": False,
            "recall_number": None,
        },
        {
            "bol_id": "BOL-74839",
            "doc_type": "BOL",
            "vendor": "Tyson Foods",
            "shipment_date": (today - timedelta(days=1)).isoformat(),
            "received_date": (today - timedelta(days=1)).isoformat(),
            "product_category": "meat_seafood",
            "product_name": "Chicken Breast (bulk, 3lb packs)",
            "invoiced_qty": 220,
            "received_qty": 220,
            "qty_delta": 0,
            "qty_delta_value": 0.0,
            "lot_number": "TYS-2024-0891",
            "po_lot_number": "TYS-2024-0891",
            "lot_mismatch": False,
            "temp_log_present": False,
            "cold_chain_req": True,
            "status": "FLAGGED",
            "flags": ["missing_temp_log"],
            "recall_match": False,
            "recall_number": None,
        },
        {
            "bol_id": "BOL-74851",
            "doc_type": "BOL",
            "vendor": "Dole",
            "shipment_date": today.isoformat(),
            "received_date": today.isoformat(),
            "product_category": "produce",
            "product_name": "Bananas (cases)",
            "invoiced_qty": 180,
            "received_qty": 180,
            "qty_delta": 0,
            "qty_delta_value": 0.0,
            "lot_number": "DL-0442",
            "po_lot_number": "DL-0441",
            "lot_mismatch": True,
            "temp_log_present": False,
            "cold_chain_req": False,
            "status": "FLAGGED",
            "flags": ["lot_mismatch"],
            "recall_match": False,
            "recall_number": None,
        },
    ]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate Orchaid synthetic telemetry")
    parser.add_argument("--bigquery", action="store_true", help="Also seed BigQuery tables")
    args = parser.parse_args()

    print("🌿 Orchaid — Generating synthetic telemetry for Stater Bros. DC...")

    datasets = {
        "equipment_readings": generate_equipment_readings(),
        "inventory_snapshot": generate_inventory_snapshot(),
        "compliance_events": generate_compliance_events(),
        "bol_documents": generate_bol_documents(),
    }

    for name, data in datasets.items():
        path = OUTPUT_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  ✓ {name}.json — {len(data)} records")

    if args.bigquery:
        print("\n📊 Seeding BigQuery...")
        try:
            from google.cloud import bigquery as bq
            import os
            client = bq.Client(project=os.environ["GCP_PROJECT_ID"])
            dataset = os.environ.get("GCP_BIGQUERY_DATASET", "orchaid_warehouse")

            table_map = {
                "equipment_readings": datasets["equipment_readings"],
                "inventory_snapshot": datasets["inventory_snapshot"],
                "compliance_events": datasets["compliance_events"],
                "document_log": datasets["bol_documents"],
            }

            for table_name, rows in table_map.items():
                table_ref = f"{os.environ['GCP_PROJECT_ID']}.{dataset}.{table_name}"
                errors = client.insert_rows_json(table_ref, rows)
                if errors:
                    print(f"  ✗ {table_name}: {errors}")
                else:
                    print(f"  ✓ {table_name}: {len(rows)} rows inserted")
        except Exception as e:
            print(f"  ✗ BigQuery seed failed: {e}")
            print("    Make sure GCP_PROJECT_ID is set and GOOGLE_APPLICATION_CREDENTIALS is valid")

    print("\n✅ Done. JSON files ready in data/synthetic/")
    print("   Run 'npm run dev' to start Orchaid in demo mode.")

if __name__ == "__main__":
    main()
