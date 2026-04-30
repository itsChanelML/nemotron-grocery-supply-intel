# backend/api/gchat.py
# Google Chat webhook proxy — Physical AI Loop 1
#
# Sends real-time maintenance dispatch alerts to a Google Chat space
# when the Equipment Agent detects a CRITICAL cold chain anomaly.
#
# Why Google Chat (not Slack or SMS):
#   Stater Bros. runs Google Workspace. Floor supervisors and maintenance
#   coordinators use Google Chat for operational communication. This is
#   the actual notification channel a regional grocer would use.
#
# Setup:
#   1. Create a Google Chat space
#   2. Space name → Apps & Integrations → Webhooks → Add Webhook
#   3. Copy webhook URL → GOOGLE_CHAT_WEBHOOK_URL env var

import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

GCHAT_WEBHOOK = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "")


def build_equipment_card(payload: dict) -> dict:
    """Build a rich Google Chat card for a maintenance dispatch alert."""
    return {
        "cards": [
            {
                "header": {
                    "title": "🔴 CRITICAL — Maintenance Dispatch Required",
                    "subtitle": f"Orchaid Equipment Agent · Stater Bros. DC",
                },
                "sections": [
                    {
                        "widgets": [
                            {
                                "keyValue": {
                                    "topLabel": "Asset",
                                    "content": f"{payload.get('asset', 'R-12')} — {payload.get('zone', 'Dairy Zone')}",
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "Anomaly Detected",
                                    "content": f"{payload.get('metric')}: {payload.get('value')} vs {payload.get('baseline')} baseline",
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "Recommended Action",
                                    "content": payload.get("recommendation", "Dispatch maintenance technician immediately."),
                                    "contentMultiline": True,
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "Compliance Risk",
                                    "content": "FDA 21 CFR 117 cold chain violation if unaddressed within 1 hour",
                                }
                            },
                        ]
                    },
                    {
                        "widgets": [
                            {
                                "buttons": [
                                    {
                                        "textButton": {
                                            "text": "✅ ACKNOWLEDGE",
                                            "onClick": {"openLink": {"url": "https://orchaid.vercel.app"}},
                                        }
                                    },
                                    {
                                        "textButton": {
                                            "text": "📋 VIEW COMMAND CENTER",
                                            "onClick": {"openLink": {"url": "https://orchaid.vercel.app"}},
                                        }
                                    },
                                ]
                            }
                        ]
                    },
                ],
            }
        ]
    }


class GChatRequest(BaseModel):
    type: str
    payload: dict


@router.post("")
async def send_gchat_alert(body: GChatRequest):
    # Demo mode — no webhook configured
    if not GCHAT_WEBHOOK or "YOUR_SPACE" in GCHAT_WEBHOOK:
        return {
            "success": True,
            "demo": True,
            "message": "Demo mode — add GOOGLE_CHAT_WEBHOOK_URL to send live Google Chat alerts",
        }

    message_body = {}
    if body.type == "equipment_critical":
        message_body = build_equipment_card(body.payload)
    else:
        message_body = {"text": f"Orchaid Alert: {body.type} — {body.payload}"}

    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.post(
            GCHAT_WEBHOOK,
            json=message_body,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()

    return {
        "success": True,
        "demo": False,
        "message": "Alert dispatched to Google Chat",
    }
