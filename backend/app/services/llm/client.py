# This module provides a client for interacting with a language model (LLM) provider, specifically Ollama.

from __future__ import annotations

import httpx

from app.core.config import settings


def generate_answer_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    if settings.llm_provider.lower() != "ollama":
        raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")

    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": temperature,
            "num_predict": max_output_tokens,
        },
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("LLM returned an empty response")

    return content