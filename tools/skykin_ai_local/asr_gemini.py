"""Amharic call transcription via Gemini multimodal audio."""
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx

from audio_prep import ethiopic_ratio

ROOT = Path(__file__).resolve().parent


def _ensure_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_ensure_env()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

_PROMPT = (
    "Transcribe this call-center phone recording.\n"
    "The language is Amharic (and maybe a little English).\n"
    "Rules:\n"
    "- Output ONLY the spoken transcript in Amharic Ge'ez (Ethiopic) script.\n"
    "- Keep English words/numbers as spoken.\n"
    "- Do NOT translate into English.\n"
    "- Do NOT add titles, timestamps, speaker labels, or commentary.\n"
    "- If audio is silent or unintelligible, return an empty string."
)


def _mime_for(path: str) -> str:
    mt, _ = mimetypes.guess_type(path)
    if mt and mt.startswith("audio/"):
        return mt
    suf = Path(path).suffix.lower()
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
    }.get(suf, "audio/wav")


def _candidate_models() -> list[str]:
    model = os.getenv("GEMINI_MODEL", GEMINI_MODEL).strip() or "gemini-3.5-flash"
    models = [model]
    for m in ("gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"):
        if m and m not in models:
            models.append(m)
    return models


def transcribe_file(path: str) -> dict[str, Any]:
    _ensure_env()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")

    raw = Path(path).read_bytes()
    if len(raw) < 200:
        raise RuntimeError("Audio file too small")

    b64 = base64.standard_b64encode(raw).decode("ascii")
    mime = _mime_for(path)
    last_err: Any = None

    for model in _candidate_models():
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        try:
            r = httpx.post(
                url,
                params={"key": key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": _PROMPT},
                                {"inline_data": {"mime_type": mime, "data": b64}},
                            ],
                        }
                    ],
                    "generationConfig": {"temperature": 0.1},
                },
                timeout=600.0,
            )
            if r.status_code != 200:
                print("Gemini ASR HTTP", model, r.status_code, r.text[:300])
                last_err = f"HTTP {r.status_code}"
                continue
            body = r.json()
            parts = (
                ((body.get("candidates") or [{}])[0].get("content") or {}).get("parts")
                or []
            )
            text = "".join(str(p.get("text") or "") for p in parts).strip()
            # Strip accidental markdown fences
            if text.startswith("```"):
                text = text.strip("`").split("\n", 1)[-1].strip()
            ratio = ethiopic_ratio(text)
            print(
                f"Gemini ASR model={model} chars={len(text)} "
                f"eth_ratio={ratio:.2f} bytes={len(raw)}"
            )
            return {
                "text": text,
                "ethiopic_ratio": ratio,
                "provider": f"gemini-asr:{model}",
                "model_note": "Gemini multimodal audio transcription (Amharic).",
            }
        except Exception as e:
            print("Gemini ASR failed", model, e)
            last_err = e
            continue

    raise RuntimeError(f"Gemini ASR unavailable: {last_err}")
