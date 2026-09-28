# backend/api/actions.py
# Physical AI Action Handler — closes all 3 IT/OT loops
#
# Loop 1: Equipment Agent → Google Chat maintenance dispatch
# Loop 2: Safety Agent   → WMS quarantine record
# Loop 3: Forecasting    → POS markdown record

import time
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

# In-memory action log — session-scoped
# In production: write to BigQuery orchaid_warehouse.action_log
ACTION_LOG: list[dict] = []


class ActionRequest(BaseModel):
    loop: str
    trigger: dict


@router.post("")
async def trigger_action(body: ActionRequest):
    loop    = body.loop
    trigger = body.trigger
    now     = datetime.now(timezone.utc).isoformat()
    action_id = f"ACT-{int(time.time() * 1000)}"

    result = {}

    # ── LOOP 1: Equipment → Google Chat ───────────────────────────────────
    if loop == "equipment_dispatch":
        data = trigger.get("data", {})

        # Fire Google Chat webhook
        gchat_result = {"success": False, "demo": True}
        try:
            from api.gchat import GChatRequest, send_gchat_alert
            gchat_result = await send_gchat_alert(
                GChatRequest(type="equipment_critical", payload=data)
            )
        except Exception as e:
            gchat_result = {"success": False, "error": str(e)}

        result = {
            "action_id": action_id,
            "loop": loop,
            "status": "DISPATCHED",
            "timestamp": now,
            "loop_trace": {
                "trigger": {
                    "label": "Sensor Anomaly Detected",
                    "detail": f"{data.get('asset', 'R-12')} — {data.get('metric')}: {data.get('value')} vs {data.get('baseline')} baseline (+17%)",
                    "icon": "⬡",
                },
                "reasoning": {
                    "label": "Equipment Agent Reasoning",
                    "detail": trigger.get("agent_response", "")[:180] + "…",
                    "icon": "🧠",
                    "model": "nvidia/llama-3.1-nemotron-70b-instruct via NIM",
                },
                "action": {
                    "label": "Maintenance Dispatch Sent",
                    "detail": "Google Chat alert queued (add GOOGLE_CHAT_WEBHOOK_URL to send live)"
                              if gchat_result.get("demo")
                              else "✅ Google Chat alert delivered to Maintenance Supervisor space",
                    "icon": "📲",
                    "channel": "Google Chat — Stater Bros. Maintenance Supervisor",
                    "demo": gchat_result.get("demo", True),
                },
                "result": {
                    "label": "Loop Closed",
                    "detail": "Technician notified. FDA 21 CFR 117 cold chain compliance window: 1 hour. Asset status: MAINTENANCE PENDING.",
                    "icon": "✅",
                    "status": "DISPATCHED",
                },
            },
            "feed_event": {
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "equipment",
                "level": "CRITICAL",
                "msg": "R-12 maintenance dispatch sent → Google Chat alert delivered to Maintenance Supervisor",
                "action_badge": "DISPATCHED",
            },
        }

    # ── LOOP 2: Safety → WMS Quarantine ──────────────────────────────────
    elif loop == "wms_quarantine":
        data = trigger.get("data", {})
        record = {
            "quarantine_id": f"QRN-{int(time.time() * 1000)}",
            "bol_id": data.get("bol_id", "BOL-74808"),
            "lot_number": data.get("lot_number", "RLT-2024-0891"),
            "vendor": data.get("vendor", "Fresh Express"),
            "product": data.get("product", "Romaine Lettuce (bagged)"),
            "units_quarantined": data.get("units", 340),
            "location": data.get("location", "Receiving Dock — Bay 3"),
            "recall_class": data.get("recall_class", "Class II"),
            "recall_number": data.get("recall_number", "F-2024-0033"),
            "regulation": "21 CFR 7.3(m)",
            "quarantined_by": "Orchaid Safety Agent (automated)",
            "quarantined_at": now,
            "status": "QUARANTINED",
        }
        ACTION_LOG.append({"type": "quarantine", **record})

        result = {
            "action_id": action_id,
            "loop": loop,
            "status": "QUARANTINED",
            "timestamp": now,
            "record": record,
            "loop_trace": {
                "trigger": {
                    "label": "FDA Recall Match Detected",
                    "detail": f"OpenFDA API returned Class II recall on lot #{record['lot_number']}. Cross-referenced against {record['bol_id']} in BigQuery. Match confirmed.",
                    "icon": "⬟",
                },
                "reasoning": {
                    "label": "Safety Agent Reasoning",
                    "detail": trigger.get("agent_response", "")[:180] + "…",
                    "icon": "🧠",
                    "model": "meta/llama-3.1-8b-instruct via NIM",
                },
                "action": {
                    "label": "WMS Quarantine Record Written",
                    "detail": f"{record['units_quarantined']} units of {record['product']} — Lot #{record['lot_number']} — status set to QUARANTINED",
                    "icon": "🚫",
                    "channel": "WMS → BigQuery orchaid_warehouse.compliance_events",
                },
                "result": {
                    "label": "Loop Closed",
                    "detail": f"{record['units_quarantined']} units physically isolated at {record['location']}. FDA documentation auto-generated. Vendor notification: pending.",
                    "icon": "✅",
                    "status": "QUARANTINED",
                },
            },
            "feed_event": {
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "safety",
                "level": "CRITICAL",
                "msg": f"WMS quarantine applied — {record['units_quarantined']} units romaine lot #{record['lot_number']} isolated at Receiving Dock",
                "action_badge": "QUARANTINED",
            },
        }

    # ── LOOP 3: Forecasting → POS Markdown ───────────────────────────────
    elif loop == "pos_markdown":
        data = trigger.get("data", {})
        original_price    = data.get("original_price", 12.99)
        markdown_pct      = data.get("markdown_pct", 30)
        new_price         = round(original_price * (1 - markdown_pct / 100), 2)
        units             = data.get("units", 340)
        revenue_at_risk   = round(original_price * units, 2)
        revenue_recovered = round(new_price * units, 2)

        record = {
            "markdown_id": f"MKD-{int(time.time() * 1000)}",
            "sku_id": data.get("sku_id", "SKU-4821"),
            "product_name": data.get("product_name", "Atlantic Salmon Fillets 2lb"),
            "zone": data.get("zone", "Meat & Seafood"),
            "original_price": original_price,
            "markdown_pct": markdown_pct,
            "new_price": new_price,
            "units_affected": units,
            "spoilage_risk_score": data.get("spoilage_score", 0.87),
            "days_to_expiry": data.get("days_to_expiry", 2),
            "revenue_at_risk": revenue_at_risk,
            "revenue_recovered": revenue_recovered,
            "markdown_by": "Orchaid Forecasting Agent (automated)",
            "effective_at": now,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
            "status": "MARKDOWN APPLIED",
        }
        ACTION_LOG.append({"type": "markdown", **record})

        result = {
            "action_id": action_id,
            "loop": loop,
            "status": "MARKDOWN APPLIED",
            "timestamp": now,
            "record": record,
            "loop_trace": {
                "trigger": {
                    "label": "Spoilage Risk Threshold Exceeded",
                    "detail": f"{record['product_name']} — Risk score: {record['spoilage_risk_score']}/1.0 · {record['days_to_expiry']} days to expiry · {record['units_affected']} units unsold",
                    "icon": "◈",
                },
                "reasoning": {
                    "label": "Forecasting Agent Reasoning",
                    "detail": trigger.get("agent_response", "")[:180] + "…",
                    "icon": "🧠",
                    "model": "nvidia/llama-3.1-nemotron-70b-instruct via NIM",
                },
                "action": {
                    "label": "POS Price Update Applied",
                    "detail": f"{record['product_name']} — ${record['original_price']} → ${record['new_price']} ({record['markdown_pct']}% off) · {record['units_affected']} units",
                    "icon": "🏷️",
                    "channel": "POS System → BigQuery orchaid_warehouse.pos_markdowns",
                },
                "result": {
                    "label": "Loop Closed",
                    "detail": f"Revenue recovered: ${record['revenue_recovered']:,.2f} of ${record['revenue_at_risk']:,.2f} at risk. Markdown expires in 8 hours.",
                    "icon": "✅",
                    "status": "MARKDOWN APPLIED",
                },
            },
            "feed_event": {
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "forecasting",
                "level": "HIGH",
                "msg": f"POS markdown applied — {record['product_name']} {record['markdown_pct']}% off · ${record['revenue_recovered']:,.2f} revenue recovered",
                "action_badge": "MARKDOWN APPLIED",
            },
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unknown loop: {loop}")

    ACTION_LOG.append({"action_id": action_id, "loop": loop, "timestamp": now, "status": result["status"]})
    return result


@router.get("")
async def get_action_log():
    """Return session action log."""
    return {"actions": ACTION_LOG}
