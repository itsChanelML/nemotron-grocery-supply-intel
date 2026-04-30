# backend/agents/__init__.py
from agents.forecasting import FORECASTING_AGENT, build_system_prompt as forecasting_prompt, MARKDOWN_TRIGGERS
from agents.equipment import EQUIPMENT_AGENT, build_system_prompt as equipment_prompt, DISPATCH_TRIGGERS
from agents.safety import SAFETY_AGENT, build_system_prompt as safety_prompt, QUARANTINE_TRIGGERS
from agents.document import DOCUMENT_AGENT, build_system_prompt as document_prompt

AGENT_REGISTRY = {
    "forecasting": FORECASTING_AGENT,
    "equipment":   EQUIPMENT_AGENT,
    "safety":      SAFETY_AGENT,
    "document":    DOCUMENT_AGENT,
}
