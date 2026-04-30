from typing import Optional
# backend/agents/forecasting.py
# Forecasting Agent — Demand & Spoilage Intelligence
#
# Model: nvidia/llama-3.1-nemotron-70b-instruct via NIM
# Temperature: 0.1 (low — deterministic forecasts)
# Physical AI Loop: Loop 3 → POS Markdown trigger
#
# Why Nemotron 70B:
#   Demand forecasting requires multi-step numerical reasoning across
#   velocity trends, dwell times, and external demand signals simultaneously.
#   Nemotron's RLHF post-training on Llama 70B significantly outperforms
#   the base model on structured reasoning tasks. Low temp = reproducible
#   markdown recommendations across runs.

from lib.nim import NEMOTRON_70B


FORECASTING_AGENT = {
    "id": "forecasting",
    "name": "Forecasting Agent",
    "role": "Demand & Spoilage Intelligence",
    "model": NEMOTRON_70B,
    "temperature": 0.1,
}

# Keywords that trigger Loop 3 (POS Markdown) in api/chat.py
MARKDOWN_TRIGGERS = ["markdown", "salmon", "spoilage", "expiry", "discount", "price"]


def build_system_prompt(telemetry: Optional[dict] = None) -> str:
    """
    Build the Forecasting Agent system prompt.
    Injects live BigQuery telemetry when available.
    Falls back to synthetic data snapshot for demo mode.
    """
    telemetry_section = ""
    if telemetry and telemetry.get("inventory"):
        import json
        telemetry_section = f"""
## Live Inventory Telemetry (from BigQuery — refreshed every 5 minutes)
{json.dumps(telemetry["inventory"], indent=2, default=str)}
"""
    else:
        telemetry_section = """
## Live Inventory Telemetry (Synthetic — Demo Mode)
- Fresh Produce Zone: 847 SKUs active, 23 flagged at >72hr dwell time
- Dairy/Cold: 94.2% capacity, 3 pallets Greek yogurt (Chobani) 18hr delayed
- Bakery: Bread velocity +34% above 7-day avg (local event demand signal)
- Meat/Seafood: Atlantic Salmon Fillets — 2.1 days to expiry, 340 units unsold
  · Spoilage risk score: 0.87/1.0 · Velocity: below reorder threshold
  · Revenue at risk: $4,416.60 · Markdown recommended: 30% by 6PM
- Frozen Zone: -3°F variance in Zone F-7, demand normal
- Top spoilage risk: bagged salad (0.87), cut fruit (0.79), rotisserie chicken (0.71)
"""

    return f"""You are the Forecasting Agent for Orchaid — an NVIDIA NIM-powered demand
and spoilage intelligence agent for the Stater Bros. Distribution Center,
San Bernardino, CA. You are part of the NVIDIA MAIW (Multi-Agent Intelligent
Warehouse) Blueprint implementation.

You run on nvidia/llama-3.1-nemotron-70b-instruct via NVIDIA NIM microservices.
Your reasoning is grounded in real-time BigQuery telemetry and cuML-style
spoilage risk scoring.

{telemetry_section}

## Your Responsibilities
- Forecast demand spikes by category using velocity + external signals
- Flag SKUs at spoilage risk with dwell time, expiry proximity, and score
- Recommend markdown timing, percentage, and affected units
- Surface throughput bottlenecks before they cause stockouts or waste

## Response Guidelines
- Be specific — cite SKU names, quantities, scores, and timeframes
- Lead with the highest-risk items
- Give concrete actions: "Mark down 30% by 6PM today — recovers $3,091"
- Flag urgency: 🔴 CRITICAL | 🟠 HIGH | 🟡 MEDIUM | 🟢 LOW
- Keep responses to 4-6 sentences unless asked for full analysis
""".strip()
