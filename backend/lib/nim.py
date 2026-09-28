# backend/lib/nim.py
# NVIDIA NIM inference client for Orchaid
#
# NIM uses the OpenAI-compatible API format, so we use the openai SDK
# pointed at NVIDIA's inference endpoint.
#
# Model routing rationale:
#   Nemotron 3 Super 120B — Forecasting, Equipment, Document agents
#     NVIDIA Nemotron 3 Super (120B MoE) — strong instruction
#     following, multi-step numerical reasoning and
#     root cause analysis.
#
#   Nemotron 3.5 Lightning 30B — Safety agent
#     Rule lookup + threshold comparison against known regulations.
#     Reliable at 4x lower latency and cost. Zero temp for determinism.
#
#   NV-EmbedQA — Document agent vector embeddings
#     NeMo Retriever pattern: embed → BigQuery vector search → Nemotron gen

import os
from openai import AsyncOpenAI, OpenAI
from typing import Optional

NIM_BASE_URL = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY  = os.getenv("NVIDIA_NIM_API_KEY", "")

# Model constants
NEMOTRON_LARGE = "nvidia/nemotron-3-super-120b-a12b"
NEMOTRON_FAST  = "nvidia/nemotron-3.5-lightning-30b-a3b"
NV_EMBED       = "nvidia/nemotron-3-embed-1b"


def _require_key() -> str:
    if not NIM_API_KEY:
        raise ValueError(
            "NVIDIA_NIM_API_KEY is not set. "
            "Get your key at https://build.nvidia.com"
        )
    return NIM_API_KEY


def get_nim_client() -> OpenAI:
    """Return a sync OpenAI client pointed at the NVIDIA NIM endpoint."""
    return OpenAI(base_url=NIM_BASE_URL, api_key=_require_key())


async def nim_chat(
    model: str,
    system_prompt: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """
    Send a chat completion request to NVIDIA NIM.

    Args:
        model:         NIM model string (use constants above)
        system_prompt: Agent system instructions
        messages:      Conversation history [{role, content}]
        temperature:   Sampling temperature (0.0 for safety, 0.1 for ops agents)
        max_tokens:    Max tokens to generate

    Returns:
        Generated text response
    """
    client = AsyncOpenAI(base_url=NIM_BASE_URL, api_key=_require_key())

    formatted = [{"role": "system", "content": system_prompt}] + messages

    # Try the requested model, then fall back to the fast model if it is
    # overloaded or unavailable (NIM catalog models are retired periodically).
    candidates = [model] if model == NEMOTRON_FAST else [model, NEMOTRON_FAST]
    last_err: Exception | None = None
    for m in candidates:
        try:
            response = await client.chat.completions.create(
                model=m,
                messages=formatted,
                temperature=temperature,
                max_tokens=max_tokens,
                # Reasoning models: skip the chain-of-thought, return only the answer
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            return response.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"NIM call failed for {m}: {e}")
    raise last_err


async def nim_embed(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings via NIM for Document Agent RAG.
    Uses NeMo Retriever pattern: embed → vector search → grounded generation.

    Args:
        texts: List of text chunks to embed

    Returns:
        List of embedding vectors
    """
    client = get_nim_client()

    response = client.embeddings.create(
        model=NV_EMBED,
        input=texts,
        extra_body={"input_type": "passage", "truncate": "END"},
    )

    return [item.embedding for item in response.data]
