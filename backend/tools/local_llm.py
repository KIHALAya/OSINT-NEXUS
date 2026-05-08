"""
tools/local_llm.py

Interface for local LLM calls (Gemma 4).
Assumes an OpenAI-compatible API running locally (Ollama, vLLM, etc.).

Used for:
  - Keyword generation (Bootstrap)
  - Raw post triage (Video Selector)
  - PII-sensitive claim extraction (Claim Extractor)
"""

import json
import logging
import asyncio
import httpx
from typing import Any, Optional
from core.config import get_settings

logger = logging.getLogger(__name__)

async def call_local_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.1,
    response_format: Optional[dict] = None
) -> str:
    """
    Calls Gemma 4 via the selected provider (Ollama, Groq, or Google).
    This allows development on resource-constrained machines by switching to a hosted API.
    """
    settings = get_settings()
    
    # ── Option 1: Google AI Studio (Hosted Gemma) ────────────────────────────
    if settings.LLM_PROVIDER == "google":
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GOOGLE_GEMMA_MODEL,
            system_instruction=system_prompt
        )
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
        return response.text.strip()

    # ── Option 2: Groq, OpenRouter, or Ollama (OpenAI Compatible) ─────────────
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    if settings.LLM_PROVIDER == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        model = settings.GROQ_MODEL
        headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    elif settings.LLM_PROVIDER == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        model = settings.OPENROUTER_MODEL
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "X-Title": "OSINT-SENTINEL (Hackathon)",
        }
    else:  # Default to Ollama
        url = f"{settings.LOCAL_LLM_URL}/chat/completions"
        model = settings.LOCAL_LLM_MODEL
        headers = {}

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM call failed (provider={settings.LLM_PROVIDER}): {e}")
        raise RuntimeError(f"Gemma 4 integration error: {e}")

async def call_local_llm_json(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> dict:
    """
    Helper to call Gemma and parse JSON response.
    """
    # Force JSON format if supported, or just prompt for it
    content = await call_local_llm(
        prompt, 
        system_prompt, 
        response_format={"type": "json_object"}
    )
    
    try:
        # Strip markdown fences if the model added them anyway
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to parse JSON from local LLM: {e} | Content: {content[:100]}...")
        return {}
