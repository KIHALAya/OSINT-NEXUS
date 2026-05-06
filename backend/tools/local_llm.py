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
    Calls the local Gemma 4 instance via OpenAI-compatible API.
    """
    settings = get_settings()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": settings.LOCAL_LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    if response_format:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.LOCAL_LLM_URL}/chat/completions",
                json=payload
            )
            resp.raise_for_status()
            
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            return content.strip()

    except Exception as e:
        logger.error(f"Local LLM call failed: {e}")
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
