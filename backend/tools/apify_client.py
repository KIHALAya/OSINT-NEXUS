"""
tools/apify_client.py
Shared Apify platform client.
"""

import logging
from typing import Any
import httpx
from core.config import get_settings

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"

class ApifyError(Exception):
    def __init__(self, message:str, status_code:int |None = None, run_id:str |None = None):
        super().__init__(message)
        self.status_code = status_code
        self.run_id = run_id

class ApifyClient:
    def __init__(self):
        self._settings = get_settings()

    async def run_actor(
            self, 
            actor_id: str,
            run_input: dict[str, Any],
            timeout_seconds: int | None = None,
    ) -> list[dict[str, Any]]:
        
        token = self._settings.APIFY_TOKEN
        if not token:
            raise ApifyError("APIFY_API_TOKEN not configured")
        timeout = timeout_seconds or self._settings.APIFY_TIMEOUT_SECONDS
        actor_id_url = actor_id.replace("/", "~")
        url = f"{APIFY_BASE}/acts/{actor_id_url}/run-sync-get-dataset-items"
        params = {
            "token": token,
            "timeout": timeout,
            "format": "json",
        }
        logger.info(f"Apify run starting actor={actor_id} input_keys={list(run_input.keys())}")

        async with httpx.AsyncClient(timeout = timeout + 10) as client:
            try:
                response = await client.post(url, params=params, json=run_input)
            except httpx.TimeoutException:
                raise ApifyError(
                    f"Apify actor {actor_id} timed out after {timeout}s"
                )
            except httpx.RequestError as e:
                raise ApifyError(f"Apify request failed : {e}")
            
        if response.status_code == 200:
            items = response.json()
            logger.info(f"Apify run complete actor={actor_id} items={len(items)}")
            return items if isinstance(items, list) else []
        
        if response.status_code == 400:
            raise ApifyError(
                f"Invalid input for actor {actor_id}: {response.text}",
                status_code=400
            )
        if response.status_code == 401:
            raise ApifyError("Apify token invalid or expired", status_code=401)
        if response.status_code == 404:
            raise ApifyError(
                f"Actor not found: {actor_id}. Check the actor ID.",
                status_code=404,
            )
        if response.status_code == 402:
            raise ApifyError(
                "Apify account usage limit reached. Upgrade plan or wait.",
                status_code=402,
            )
    
        raise ApifyError(
            f"Apify returned {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
        )
    async def get_run_status(self, run_id:str) -> dict[str, Any]:
        token = self._settings.APIFY_TOKEN
        url = f"{APIFY_BASE}/actor-runs/{run_id}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"token":token})
            resp.raise_for_status()
            return resp.json().get("data", {})