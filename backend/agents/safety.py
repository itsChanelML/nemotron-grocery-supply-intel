from typing import Optional
# backend/agents/safety.py
# Safety Agent — FDA & OSHA Compliance
#
# Model: meta/llama-3.1-8b-instruct via NIM
# Temperature: 0.0 (zero — compliance answers must be deterministic)
# Physical AI Loop: Loop 2 → WMS Quarantine trigger
#
# Why Llama 8B (not Nemotron 70B):
#   FDA/OSHA compliance is primarily rule lookup + threshold comparison
#   against known regulations. "Did zone D-3 exceed 41°F?" and "Does this
#   match 21 CFR 117.93?" are pattern matching tasks, not complex causal
#   reasoning. The 8B model handles this reliably at 4x lower latency and
#   cost. We reserve Nemotron 70B for agents requiring deep multi-variable
#   reasoning. Zero temp = zero ambiguity on safety decisions.
#   Note: escalates to Nemotron 70B for novel cross-regulation scenarios.

from lib.nim import LLAMA_8B


SAFETY_AGENT = {
    "id": "safety",
    "name": "Safety Agent",
    "role": "FDA & OSHA Compliance",
    "model": LLAMA_8B,
    "temperature": 0.0,
}

# Keywords that trigger Loop 2 (WMS quarantine) in api/chat.py
QUARANTINE_TRIGGERS = ["quarantine", "recall", "rlt-2024-0891", "class ii", "isolate"]


def build_system_prompt(telemetry: Optional[dict] = None, fda_recalls: Optional[list] = None) -> str:
    """
    Build the Safety Agent system prompt.
    Injects live compliance events and FDA recall data when available.
    """
    compliance_section = ""
    if telemetry and telemetry.get("compliance"):
        import json
        compliance_section = f"""
## Live Compliance Events (from BigQuery — last 24 hours)
{json.dumps(telemetry["compliance"], indent=2, default=str)}
"""
    else:
        compliance_section = """
## Live Compliance Events (Synthetic — Demo Mode)

Temperature Log Violations (last 24 hours):
- Zone D-3: logged 42°F for 11 min at 02:14 (threshold: 41°F) — auto-documented
  · Regulation: 21 CFR 117.93 · Status: DOCUMENTED
- Zone F-7: logged -14°F for 8 min at 04:47 (threshold: -10°F) — auto-documented
  · Regulation: 21 CFR 117.93 · Status: DOCUMENTED

OSHA Proximity Events (current shift):
- 3 AMR-human proximity events below 1.5m threshold — no contact, all logged
  · Regulation: OSHA 1910.178(l)
- 2 forklift operator certifications expire within 14 days
  · Regulation: OSHA 1910.178(l)(1)

HACCP Plan:
- Last audit: 47 days ago · Next required: 60-day cycle · 13 days remaining
"""

    recalls_section = ""
    if fda_recalls:
        import json
        recalls_section = f"""
## Live FDA Recall Alerts (from OpenFDA API — real time)
{json.dumps(fda_recalls, indent=2, default=str)}
"""
    else:
        recalls_section = """
## Live FDA Recall Alerts (Synthetic — Demo Mode)

ACTIVE — Class II Recall
Product: Romaine Lettuce (bagged, various sizes)
Lot: #RLT-2024-0891
Supplier: Fresh Express
Reason: Potential Listeria monocytogenes contamination
Regulation: 21 CFR 7.3(m) — Class II (may cause temporary adverse health consequences)
Our inventory match: 340 units confirmed in Receiving Dock Bay 3 — QUARANTINE PENDING
Cross-reference: BOL #74808 (shipment date: 2 days ago)
"""

    return f"""You are the Safety Agent for Orchaid — an NVIDIA NIM-powered compliance
and hazard detection agent for the Stater Bros. Distribution Center,
San Bernardino, CA.

You run on meta/llama-3.1-8b-instruct via NVIDIA NIM microservices.

You enforce:
- FDA FSMA (Food Safety Modernization Act) — 21 CFR Part 117
- OSHA 1910 General Industry Standards
- California Department of Public Health food safety regulations
- HACCP (Hazard Analysis Critical Control Points) requirements

You have access to LIVE FDA recall data from the OpenFDA API,
cross-referenced in real time against incoming shipment records in BigQuery.

{compliance_section}
{recalls_section}

## Response Guidelines
- Always cite the regulation number (e.g., 21 CFR 117.93, OSHA 1910.178)
- Distinguish "document and monitor" vs "immediate action required"
- For recall matches: always recommend quarantine first, investigation second
- Be direct — compliance is not a place for hedging
- When recommending quarantine: use the word "quarantine" explicitly
""".strip()
