"""
tools/video_analysis.py

Video intelligence extraction for missing persons investigation.

Flow for each TikTok post:
    1. download_video()       → temp .mp4 file
    2. upload_to_gemini()     → Gemini Files API (required for video)
    3. analyze_with_gemini()  → single prompt → structured VideoSignals JSON
    4. cleanup                → delete temp file + Gemini file

Why Gemini 1.5 Flash and not Gemma via Kaggle:
    Kaggle hosts Gemma for fine-tuning and batch notebook runs.
    Its API is notebook-execution-based — not suitable for real-time calls.
    Gemini 1.5 Flash via Google AI Studio accepts raw video natively
    (audio + frames + OCR in one call), has a free tier of 1,500 req/day,
    and is purpose-built for exactly this use case.

    Free tier: 1,500 req/day · 1M tokens/min · video up to 1 hour
    Get key: https://aistudio.google.com/app/apikey
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from core.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com"


# ── Output schema ─────────────────────────────────────────────────────────────

class PersonSignal(BaseModel):
    description: str
    clothing: list[str] = []
    approximate_age: str | None = None
    gender: str | None = None
    confidence: float = 0.0

class LocationSignal(BaseModel):
    raw_text: str
    location_type: str      # street_sign | landmark | spoken | map_overlay | background
    specificity: str        # exact | neighborhood | city | vague
    value: str
    confidence: float = 0.0

class SpokenClaim(BaseModel):
    quote: str
    language: str           # ar | fr | en | darija | mixed
    claim_type: str         # sighting | rumour | denial | direction | other
    confidence: float = 0.0

class SuspiciousElement(BaseModel):
    element: str
    reason: str
    severity: str           # low | medium | high

class VideoSignals(BaseModel):
    """All signals extracted from one video. Stored in CaseState + DB."""
    post_id: str
    video_url: str
    analysis_timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    persons_detected: list[PersonSignal] = []
    location_signals: list[LocationSignal] = []
    spoken_claims: list[SpokenClaim] = []
    suspicious_elements: list[SuspiciousElement] = []
    overall_relevance: float = 0.0
    case_relevant: bool = False
    summary: str = ""
    recommended_action: str = ""
    model_used: str = ""
    gemini_file_uri: str | None = None
    processing_error: str | None = None

class VideoAnalysisInput(BaseModel):
    post_id: str = Field(description="TikTok post ID")
    video_url: str = Field(description="Direct video URL from Apify TikTok response")
    case_id: str = Field(description="Investigation case ID")
    subject_description: str = Field(
        description=(
            "Full description of the missing person: name, age, build, "
            "hair, last known clothing, last known location + date. "
            "E.g. 'Amira Benali, 14yo female, dark hair, blue jacket and jeans, "
            "last seen Morocco Mall Casablanca Jan 15 2024'"
        )
    )


# ── Investigation prompt ──────────────────────────────────────────────────────

INVESTIGATION_PROMPT = """\
You are an AI assistant supporting a missing persons investigation.
Analyze this video carefully and extract every signal that could help locate or identify the subject.

Missing person details:
{subject_description}

Extract ALL of the following:

1. PERSONS — any person visible or described (appearance, clothing, age, gender)
2. LOCATIONS — street signs, landmarks, spoken place names, map overlays,
   recognizable buildings, neighborhood sounds or characteristics
3. SPOKEN WORDS — every relevant spoken statement in any language
   (Arabic MSA, Darija, French, or mixed). Transcribe sighting claims,
   directions, identifications, denials.
4. SUSPICIOUS ELEMENTS — recycled footage, staged content, contradictions,
   inconsistent backgrounds, signs of coordinated inauthentic behavior
5. OVERALL ASSESSMENT — relevance score and recommended investigator action

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON:

{{
  "persons_detected": [
    {{
      "description": "physical description",
      "clothing": ["item1", "item2"],
      "approximate_age": "string or null",
      "gender": "string or null",
      "confidence": 0.0
    }}
  ],
  "location_signals": [
    {{
      "raw_text": "exactly what was said or shown",
      "location_type": "street_sign|landmark|spoken|map_overlay|background",
      "specificity": "exact|neighborhood|city|vague",
      "value": "location name or description",
      "confidence": 0.0
    }}
  ],
  "spoken_claims": [
    {{
      "quote": "verbatim or close transcription",
      "language": "ar|fr|en|darija|mixed",
      "claim_type": "sighting|rumour|denial|direction|other",
      "confidence": 0.0
    }}
  ],
  "suspicious_elements": [
    {{
      "element": "what was found",
      "reason": "why suspicious",
      "severity": "low|medium|high"
    }}
  ],
  "overall_relevance": 0.0,
  "case_relevant": false,
  "summary": "one sentence",
  "recommended_action": "what the investigator should do next"
}}

Empty array [] if a section has no findings.
Confidence: 0.0 uncertain · 0.5 possible · 0.8 likely · 1.0 certain
"""


# ── Gemini Files API client ───────────────────────────────────────────────────

class GeminiVideoClient:
    """
    Handles video upload + analysis via Gemini API.

    Video requires two steps:
      1. Upload via Files API  → get file URI (5–30s)
      2. Send generation call  → model reads audio + frames + text

    Files auto-expire after 48h on Google's side.
    We delete immediately after analysis to stay clean.
    """

    def __init__(self):
        self._api_key = get_settings().GEMINI_API_KEY

    async def upload_video(self, file_path: Path) -> tuple[str, str]:
        """
        Upload mp4 to Gemini Files API via resumable upload.
        Returns (file_uri, file_name).
        file_uri  → used in the generation request
        file_name → used to poll state and delete
        """
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not set — get one free at aistudio.google.com")

        file_bytes = file_path.read_bytes()
        file_size = len(file_bytes)

        async with httpx.AsyncClient(timeout=120) as client:
            # Initiate resumable upload
            init = await client.post(
                f"{GEMINI_BASE}/upload/v1beta/files",
                params={"key": self._api_key},
                headers={
                    "X-Goog-Upload-Protocol": "resumable",
                    "X-Goog-Upload-Command": "start",
                    "X-Goog-Upload-Header-Content-Length": str(file_size),
                    "X-Goog-Upload-Header-Content-Type": "video/mp4",
                    "Content-Type": "application/json",
                },
                json={"file": {"display_name": file_path.name}},
            )
            init.raise_for_status()

            upload_url = init.headers.get("x-goog-upload-url")
            if not upload_url:
                raise ValueError("No upload URL returned by Gemini Files API")

            # Upload binary content
            upload = await client.put(
                upload_url,
                headers={
                    "Content-Length": str(file_size),
                    "X-Goog-Upload-Offset": "0",
                    "X-Goog-Upload-Command": "upload, finalize",
                },
                content=file_bytes,
            )
            upload.raise_for_status()
            data = upload.json()

        file_uri  = data.get("file", {}).get("uri", "")
        file_name = data.get("file", {}).get("name", "")
        if not file_uri:
            raise ValueError(f"No URI in upload response: {data}")

        logger.info(f"Uploaded to Gemini: {file_name} ({file_size/1024:.0f} KB)")

        # Wait until ACTIVE before sending inference request
        await self._wait_active(file_name)
        return file_uri, file_name

    async def _wait_active(self, file_name: str, max_wait_s: int = 90):
        async with httpx.AsyncClient(timeout=10) as client:
            for _ in range(max_wait_s // 3):
                r = await client.get(
                    f"{GEMINI_BASE}/v1beta/{file_name}",
                    params={"key": self._api_key},
                )
                r.raise_for_status()
                state = r.json().get("state", "")
                if state == "ACTIVE":
                    return
                if state == "FAILED":
                    raise RuntimeError("Gemini file processing failed")
                await asyncio.sleep(3)
        raise TimeoutError("Gemini file did not become ACTIVE within timeout")

    async def analyze(self, file_uri: str, subject_description: str) -> dict[str, Any]:
        """Send the video + prompt to Gemini and return parsed JSON."""
        payload = {
            "contents": [{
                "parts": [
                    {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}},
                    {"text": INVESTIGATION_PROMPT.format(subject_description=subject_description)},
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,       # low = deterministic structured output
                "topP": 0.8,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",  # Gemini returns JSON string
            },
        }

        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"{GEMINI_BASE}/v1beta/models/gemini-1.5-flash:generateContent",
                params={"key": self._api_key},
                json=payload,
            )

        if r.status_code == 429:
            raise RuntimeError("Gemini rate limit — free tier is 1,500 req/day. Try again tomorrow.")
        r.raise_for_status()

        raw = (
            r.json()
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Model ignored responseMimeType — strip fences and retry
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned)

    async def delete_file(self, file_name: str):
        """Delete from Gemini storage. Non-critical — files auto-expire in 48h."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.delete(
                    f"{GEMINI_BASE}/v1beta/{file_name}",
                    params={"key": self._api_key},
                )
        except Exception as e:
            logger.warning(f"Could not delete Gemini file {file_name}: {e}")


# ── Video downloader ──────────────────────────────────────────────────────────

async def download_video(url: str, max_mb: int = 100) -> Path:
    """
    Stream-download a video URL to a named temp file.
    Returns the Path. Caller must delete after use.
    """
    max_bytes = max_mb * 1024 * 1024
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                cl = r.headers.get("content-length")
                if cl and int(cl) > max_bytes:
                    raise ValueError(f"Video too large: {int(cl)/1024/1024:.0f}MB")

                received = 0
                async for chunk in r.aiter_bytes(65536):
                    received += len(chunk)
                    if received > max_bytes:
                        raise ValueError(f"Video exceeded {max_mb}MB limit during download")
                    tmp.write(chunk)
        tmp.flush()
        logger.info(f"Downloaded {received/1024:.0f}KB → {tmp.name}")
        return Path(tmp.name)

    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise
    finally:
        tmp.close()


# ── Orchestrator ──────────────────────────────────────────────────────────────

async def run_video_analysis(
    post_id: str,
    video_url: str,
    subject_description: str,
) -> VideoSignals:
    """
    Full pipeline: download → upload → analyze → cleanup.
    Never raises — errors go into VideoSignals.processing_error
    so the agent can decide what to do.
    """
    gemini = GeminiVideoClient()
    tmp_path: Path | None = None
    gemini_file_name: str | None = None

    try:
        tmp_path = await download_video(video_url)
        file_uri, gemini_file_name = await gemini.upload_video(tmp_path)
        raw = await gemini.analyze(file_uri, subject_description)

        signals = VideoSignals(
            post_id=post_id,
            video_url=video_url,
            persons_detected=[PersonSignal(**p) for p in raw.get("persons_detected", [])],
            location_signals=[LocationSignal(**l) for l in raw.get("location_signals", [])],
            spoken_claims=[SpokenClaim(**c) for c in raw.get("spoken_claims", [])],
            suspicious_elements=[SuspiciousElement(**s) for s in raw.get("suspicious_elements", [])],
            overall_relevance=float(raw.get("overall_relevance", 0.0)),
            case_relevant=bool(raw.get("case_relevant", False)),
            summary=raw.get("summary", ""),
            recommended_action=raw.get("recommended_action", ""),
            model_used="gemini-1.5-flash",
            gemini_file_uri=file_uri,
        )

        logger.info(
            f"[video_analysis] post={post_id} relevant={signals.case_relevant} "
            f"score={signals.overall_relevance:.2f} persons={len(signals.persons_detected)} "
            f"locations={len(signals.location_signals)} claims={len(signals.spoken_claims)}"
        )
        return signals

    except Exception as e:
        logger.error(f"[video_analysis] failed post={post_id}: {e}", exc_info=True)
        return VideoSignals(
            post_id=post_id,
            video_url=video_url,
            processing_error=str(e),
            model_used="gemini-1.5-flash",
        )
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        if gemini_file_name:
            await gemini.delete_file(gemini_file_name)


# ── LangGraph @tool ───────────────────────────────────────────────────────────

@tool(args_schema=VideoAnalysisInput)
async def analyze_video(
    post_id: str,
    video_url: str,
    case_id: str,
    subject_description: str,
) -> VideoSignals:
    """
    Analyze a TikTok video for missing persons investigation signals.

    Call this ONLY when:
    - The post has engagement above threshold (plays > 5000 OR shares > 50)
    - bot_score < 0.4 (credible account)
    - post_id has NOT been analyzed this session (check video_analyses in state)

    Costs ~1 Gemini API request per call. Free tier: 1,500/day.
    Do not call for every video — use for high-signal posts only.

    Returns: persons, locations, spoken claims, suspicious elements,
    relevance score, and recommended investigator action.
    """
    return await run_video_analysis(
        post_id=post_id,
        video_url=video_url,
        subject_description=subject_description,
    )