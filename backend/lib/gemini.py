# backend/lib/gemini.py
# Gemini 2.5 Pro orchestrator client via Google Cloud Vertex AI
#
# Why Gemini for the Orchestrator:
#   The Orchestrator synthesizes signals across all 4 NIM agents —
#   sensor telemetry, spoilage scores, compliance flags, document
#   discrepancies — into a unified operational picture. Gemini 2.5 Pro's
#   2M token context window makes it ideal for this role.
#   Keeps the stack 100% NVIDIA (agent inference) + Google (orchestration
#   + data) with zero third-party dependencies.
#
# Credential strategy:
#   Local:  GOOGLE_APPLICATION_CREDENTIALS file path (auto-detected)
#   Cloud Run / Vercel: GOOGLE_APPLICATION_CREDENTIALS_JSON (full JSON string)

import os
import json
from typing import Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
LOCATION   = os.getenv("GCP_LOCATION", "us-central1")

ORCHESTRATOR_MODEL = "gemini-2.5-pro"
FALLBACK_MODEL     = "gemini-2.5-flash"

_initialized = False


def _init_vertex():
    """Initialize Vertex AI — handles both local and Cloud Run credentials."""
    global _initialized
    if _initialized:
        return

    # Cloud Run / Vercel: credentials passed as JSON string env var
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        from google.oauth2 import service_account
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
    else:
        # Local: GOOGLE_APPLICATION_CREDENTIALS file path (auto-detected by SDK)
        vertexai.init(project=PROJECT_ID, location=LOCATION)

    _initialized = True


async def gemini_chat(
    system_prompt: str,
    messages: list[dict],
    use_fallback: bool = False,
) -> str:
    """
    Send a message to Gemini via Vertex AI.
    Used only by the Orchestrator in api/chat.py.

    Args:
        system_prompt: Orchestrator system instructions
        messages:      Conversation history [{role, content}]
        use_fallback:  Use Flash instead of Pro (faster, cheaper)

    Returns:
        Generated text response
    """
    if not PROJECT_ID or PROJECT_ID == "your-gcp-project-id":
        raise ValueError(
            "GCP_PROJECT_ID is not configured. "
            "Add it to your .env file or Cloud Run environment variables."
        )

    _init_vertex()

    model_name = FALLBACK_MODEL if use_fallback else ORCHESTRATOR_MODEL
    model = GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
        generation_config={
            "max_output_tokens": 1024,
            "temperature": 0.2,
            "top_p": 0.8,
        },
    )

    # Convert {role, content} → Vertex AI Content objects
    # Gemini uses "model" instead of "assistant"
    history = []
    for msg in messages[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

    chat = model.start_chat(history=history, response_validation=False)
    latest = messages[-1]["content"]
    response = await chat.send_message_async(latest)

    return response.text or ""
