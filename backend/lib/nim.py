# backend/lib/nim.py
# NVIDIA NIM inference client for Orchaid
#
# NIM uses the OpenAI-compatible API format, so we use the openai SDK
# pointed at NVIDIA's inference endpoint.
#
# Model routing rationale:
#   Nemotron 70B — Forecasting, Equipment, Document agents
#     Meta Llama 3.1 70B base + NVIDIA RLHF post-training for instruction
#     following. Significantly outperforms base Llama on multi-step
#     numerical reasoning and root cause analysis tasks.
#
#   Llama 8B — Safety agent
#     Rule lookup + threshold comparison against known regulations.
#     Reliable at 4x lower latency and cost. Zero temp for determinism.
#
#   NV-EmbedQA — Document agent vector embeddings
#     NeMo Retriever pattern: embed → BigQuery vector search → Nemotron gen

import os
from openai import OpenAI
from typing import Optional

NIM_BASE_URL = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY  = os.getenv("NVIDIA_NIM_API_KEY", "")

# Model constants
NEMOTRON_70B = "nvidia/llama-3.1-nemotron-70b-instruct"
LLAMA_8B     = "meta/llama-3.1-8b-instruct"
NV_EMBED     = "nvidia/nv-embedqa-e5-v5"


def get_nim_client() -> OpenAI:
    """Return an OpenAI client pointed at the NVIDIA NIM endpoint."""
    if not NIM_API_KEY:
        raise ValueError(
            "NVIDIA_NIM_API_KEY is not set. "
            "Get your key at https://build.nvidia.com"
        )
    return OpenAI(base_url=NIM_BASE_URL, api_key=NIM_API_KEY)


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
    client = get_nim_client()

    formatted = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model=model,
        messages=formatted,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content or ""


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
