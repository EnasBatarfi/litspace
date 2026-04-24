# This module implements the logic for interacting with different LLM providers based on the configuration.

from __future__ import annotations

from collections.abc import Callable

import httpx
from google import genai

from app.core.config import settings


def _provider_chain() -> list[str]:
    if settings.llm_provider_chain:
        providers = [part.strip().lower() for part in settings.llm_provider_chain.split(",") if part.strip()]
    else:
        providers = [settings.llm_provider.lower().strip()]

    if not providers:
        raise ValueError("No LLM provider configured")

    if not settings.llm_fallback_enabled:
        return providers[:1]

    deduped: list[str] = []
    for provider in providers:
        if provider not in deduped:
            deduped.append(provider)
    return deduped


def _provider_model_name(provider: str) -> str:
    if provider == "gemini":
        return settings.gemini_model
    if provider == "openai":
        return settings.openai_model
    if provider == "anthropic":
        return settings.anthropic_model
    if provider == "ollama":
        return settings.ollama_model
    raise ValueError(f"Unsupported llm_provider: {provider}")


def _print_provider_status(provider: str, message: str) -> None:
    model = _provider_model_name(provider)
    print(f"[llm] provider={provider} model={model} {message}")


def _format_http_error(provider: str, exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    body = response.text.strip()
    if body:
        return f"{provider} HTTP {response.status_code}: {body}"
    return f"{provider} HTTP {response.status_code}"


def _is_openai_reasoning_model(model: str) -> bool:
    normalized = model.lower()
    return normalized.startswith("gpt-5") or normalized.startswith("o1") or normalized.startswith("o3") or normalized.startswith("o4")


def _build_openai_payload(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> dict:
    payload = {
        "model": settings.openai_model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
        "max_output_tokens": max_output_tokens,
    }

    if _is_openai_reasoning_model(settings.openai_model):
        payload["reasoning"] = {"effort": "low"}
        payload["text"] = {"verbosity": "low"}
    else:
        payload["temperature"] = temperature

    return payload


def _generate_with_gemini(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"{system_prompt}\n\n{user_prompt}"

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config={
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        },
    )

    content = (response.text or "").strip()
    if not content:
        raise ValueError("Gemini returned an empty response")

    return content


def _generate_with_openai(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    def send_request(output_budget: int) -> dict:
        payload = _build_openai_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=output_budget,
        )

        with httpx.Client(timeout=120.0) as client:
            try:
                response = client.post(
                    f"{settings.openai_base_url.rstrip('/')}/responses",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(_format_http_error("openai", exc)) from exc

            return response.json()

    def extract_text(data: dict) -> str:
        content = ""
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for block in item.get("content", []):
                if block.get("type") in {"output_text", "text"}:
                    content += block.get("text", "")
        return content.strip()

    data = send_request(max_output_tokens)
    content = extract_text(data)
    if content:
        return content

    incomplete_reason = (data.get("incomplete_details") or {}).get("reason")
    if incomplete_reason == "max_output_tokens":
        retry_budget = max(1200, max_output_tokens * 2)
        data = send_request(retry_budget)
        content = extract_text(data)
        if content:
            return content

    raise ValueError(f"OpenAI returned an empty response: {data}")


def _generate_with_anthropic(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    payload = {
        "model": settings.anthropic_model,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }

    with httpx.Client(timeout=120.0) as client:
        try:
            response = client.post(
                f"{settings.anthropic_base_url.rstrip('/')}/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(_format_http_error("anthropic", exc)) from exc

        data = response.json()

    content_blocks = data.get("content") or []
    text_parts = [
        block.get("text", "")
        for block in content_blocks
        if block.get("type") == "text"
    ]
    content = "".join(text_parts).strip()
    if not content:
        raise ValueError("Anthropic returned an empty response")

    return content


def _generate_with_ollama(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
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
        try:
            response = client.post(f"{settings.ollama_base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(_format_http_error("ollama", exc)) from exc

        data = response.json()

    content = data.get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("Ollama returned an empty response")

    return content


def generate_answer_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_output_tokens: int,
) -> str:
    generators: dict[str, Callable[[str, str, float, int], str]] = {
        "gemini": _generate_with_gemini,
        "openai": _generate_with_openai,
        "anthropic": _generate_with_anthropic,
        "ollama": _generate_with_ollama,
    }

    failures: list[str] = []

    for provider in _provider_chain():
        generator = generators.get(provider)
        if generator is None:
            failures.append(f"{provider}: unsupported provider")
            continue

        try:
            content = generator(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            _print_provider_status(provider, "selected")
            return content
        except Exception as exc:
            _print_provider_status(provider, f"failed: {exc}")
            failures.append(f"{provider}: {exc}")

    raise RuntimeError("All configured LLM providers failed: " + " | ".join(failures))
