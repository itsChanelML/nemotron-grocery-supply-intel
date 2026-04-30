from typing import Optional
# backend/api/chat.py
# Main agent chat endpoint
#
# Routing:
#   orchestrator → Gemini 2.5 Pro via Vertex AI
#   forecasting  → Nemotron 70B via NIM  (temp 0.1)
#   equipment    → Nemotron 70B via NIM  (temp 0.1)
#   safety       → Llama 8B via NIM      (temp 0.0)
#   document     → Nemotron 70B via NIM  (temp 0.1)
#
# After agent responds:
#   Scans response for Physical AI trigger keywords
#   Automatically calls /actions to close the IT/OT loop

import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from lib.nim import nim_chat
from lib.gemini import gemini_chat
from agents import (
    AGENT_REGISTRY,
    MARKDOWN_TRIGGERS, DISPATCH_TRIGGERS, QUARANTINE_TRIGGERS,
)
from agents.forecasting import build_system_prompt as forecasting_prompt
from agents.equipment import build_system_prompt as equipment_prompt
from agents.safety import build_system_prompt as safety_prompt
from agents.document import build_system_prompt as document_prompt

router = APIRouter()

ORCHESTRATOR_SYSTEM = """
You are the Orchaid Orchestrator — the master coordination intelligence for the
Stater Bros. Distribution Center multi-agent warehouse system, built on the
NVIDIA MAIW (Multi-Agent Intelligent Warehouse) Blueprint.

You are powered by Gemini 2.5 Pro via Google Cloud Vertex AI. You coordinate
4 specialized NIM-powered agents running on NVIDIA infrastructure:

1. Forecasting Agent (Nemotron 70B via NIM) — demand, spoilage risk, markdowns
2. Equipment Agent (Nemotron 70B via NIM) — cold chain, AMR fleet, conveyors
3. Safety Agent (Llama 8B via NIM) — FDA FSMA, OSHA, live recall cross-reference
4. Document Agent (Nemotron 70B + NV-EmbedQA RAG) — BOLs, invoices, lot matching

Current system status:
- 🔴 CRITICAL: FDA Class II recall — romaine lettuce lot #RLT-2024-0891, 340 units in dock
- 🟠 HIGH: R-12 compressor +17% above baseline — cold chain risk
- 🟠 HIGH: Salmon fillets — 2.1 days to expiry, 340 units, spoilage score 0.87
- 🟡 MEDIUM: BOL #74839 missing cold chain temp log
- 🟡 MEDIUM: AMR-07 odometry drift 3.2x spec
- 🟡 MEDIUM: BOL #74821 quantity delta $340 dispute
- Compliance: 91.4% | Fleet uptime: 94.7% | BOL accuracy: 93.6%

Synthesize across all agents. Cite specific data. Give actionable recommendations.
""".strip()


class ChatRequest(BaseModel):
    agent_id: Optional[str] = None
    messages: list[dict]


class ChatResponse(BaseModel):
    response: str
    physical_action: Optional[dict] = None


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    
    HAS_NIM_KEY = bool(os.getenv("NVIDIA_NIM_API_KEY", "").startswith("nvapi-") and
                       not os.getenv("NVIDIA_NIM_API_KEY", "").startswith("nvapi-xxx"))
    HAS_GCP     = bool(os.getenv("GCP_PROJECT_ID") and
                       os.getenv("GCP_PROJECT_ID") != "your-gcp-project-id")
    
    agent_id = body.agent_id
    messages = body.messages

    if not messages:
        raise HTTPException(status_code=400, detail="messages list is required")

    response_text = ""

    # ── Orchestrator — Gemini 2.5 Pro ────────────────────────────────────
    if not agent_id or agent_id == "orchestrator":
        if HAS_GCP:
            response_text = await gemini_chat(
                system_prompt=ORCHESTRATOR_SYSTEM,
                messages=messages,
            )
        else:
            response_text = (
                "⚙️ Orchestrator offline — add GCP_PROJECT_ID to environment "
                "variables to enable Gemini 2.5 Pro orchestration."
            )

    # ── Specialized agents — NVIDIA NIM ──────────────────────────────────
    else:
        agent = AGENT_REGISTRY.get(agent_id)
        if not agent:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {agent_id}")

        # Build system prompt — in production, pass live BigQuery telemetry
        prompt_builders = {
            "forecasting": forecasting_prompt,
            "equipment":   equipment_prompt,
            "safety":      safety_prompt,
            "document":    document_prompt,
        }
        system_prompt = prompt_builders[agent_id]()

        if HAS_NIM_KEY:
            response_text = await nim_chat(
                model=agent["model"],
                system_prompt=system_prompt,
                messages=messages,
                temperature=agent["temperature"],
            )
        elif HAS_GCP:
            # Fallback: Gemini Flash with same system prompt — stays GCP-native
            response_text = await gemini_chat(
                system_prompt=f"[DEMO — Simulating {agent['name']} ({agent['model']}) via Gemini Flash]\n\n{system_prompt}",
                messages=messages,
                use_fallback=True,
            )
        else:
            response_text = (
                f"⚙️ {agent['name']} offline — add NVIDIA_NIM_API_KEY to enable "
                "NIM inference, or GCP_PROJECT_ID for Gemini Flash fallback."
            )

    # ── Physical AI: detect triggers and fire action loops ────────────────
    physical_action = None
    if agent_id and response_text:
        lower = response_text.lower()
        base_url = str(request.base_url).rstrip("/")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:

                # Loop 1 — Equipment → Google Chat dispatch
                if agent_id == "equipment" and any(t in lower for t in DISPATCH_TRIGGERS):
                    r = await client.post(f"{base_url}/actions", json={
                        "loop": "equipment_dispatch",
                        "trigger": {
                            "agent_id": agent_id,
                            "agent_response": response_text,
                            "data": {
                                "asset": "R-12",
                                "metric": "Compressor cycle time",
                                "value": "340ms",
                                "baseline": "290ms",
                                "zone": "Dairy Zone",
                                "recommendation": "Dispatch maintenance technician immediately. Inspect compressor valve and capacitor.",
                            },
                        },
                    })
                    physical_action = r.json()

                # Loop 2 — Safety → WMS quarantine
                elif agent_id == "safety" and any(t in lower for t in QUARANTINE_TRIGGERS):
                    r = await client.post(f"{base_url}/actions", json={
                        "loop": "wms_quarantine",
                        "trigger": {
                            "agent_id": agent_id,
                            "agent_response": response_text,
                            "data": {
                                "bol_id": "BOL-74808",
                                "lot_number": "RLT-2024-0891",
                                "vendor": "Fresh Express",
                                "product": "Romaine Lettuce (bagged)",
                                "units": 340,
                                "location": "Receiving Dock — Bay 3",
                                "recall_class": "Class II",
                                "recall_number": "F-2024-0033",
                            },
                        },
                    })
                    physical_action = r.json()

                # Loop 3 — Forecasting → POS markdown
                elif agent_id == "forecasting" and any(t in lower for t in MARKDOWN_TRIGGERS):
                    if any(w in lower for w in ["%", "price", "discount", "markdown"]):
                        r = await client.post(f"{base_url}/actions", json={
                            "loop": "pos_markdown",
                            "trigger": {
                                "agent_id": agent_id,
                                "agent_response": response_text,
                                "data": {
                                    "sku_id": "SKU-4821",
                                    "product_name": "Atlantic Salmon Fillets 2lb",
                                    "zone": "Meat & Seafood",
                                    "original_price": 12.99,
                                    "markdown_pct": 30,
                                    "new_price": 9.09,
                                    "units": 340,
                                    "spoilage_score": 0.87,
                                    "days_to_expiry": 2,
                                    "revenue_at_risk": 4416.60,
                                    "revenue_recovered": 3091.60,
                                },
                            },
                        })
                        physical_action = r.json()

        except Exception as e:
            print(f"Physical action trigger failed: {e}")

    return ChatResponse(response=response_text, physical_action=physical_action)
