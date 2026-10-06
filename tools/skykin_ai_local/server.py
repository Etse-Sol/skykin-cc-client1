"""
SkyKin local AI — Amharic call evaluation (PC demo UI + API).

Open http://127.0.0.1:8100 after: python server.py
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

WHISPER_MODEL = os.getenv("SKYKIN_WHISPER_MODEL", "medium")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
# Prefer 7b if installed; 3b is faster to download and fine for QA JSON scoring.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_MODELS = [
    m.strip()
    for m in os.getenv("OLLAMA_MODELS", "qwen2.5:7b,qwen2.5:3b").split(",")
    if m.strip()
]
DEVICE = os.getenv("SKYKIN_WHISPER_DEVICE", "cpu")
COMPUTE = os.getenv("SKYKIN_WHISPER_COMPUTE", "int8")
ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
SCORE_KEYS = ("greeting", "knowledge", "resolution", "tone", "procedure", "closing")


def _load_dotenv() -> None:
    """Load tools/skykin_ai_local/.env into os.environ (no python-dotenv dependency)."""
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


_load_dotenv()
# Prefer Gemini for Amharic when a key is present; Ethio remains the fallback.
ASR_ENGINE = os.getenv("SKYKIN_ASR_ENGINE", "auto").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

app = FastAPI(title="SkyKin AI Local", version="0.2.0")
_whisper = None
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def get_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel

        print(f"Loading Whisper model={WHISPER_MODEL} device={DEVICE} compute={COMPUTE} …")
        _whisper = WhisperModel(WHISPER_MODEL, device=DEVICE, compute_type=COMPUTE)
        print("Whisper ready.")
    return _whisper


def _finalize_transcript(r: dict[str, Any], provider_fallback: str) -> tuple[str, str]:
    text = (r.get("text") or "").strip()
    ratio = float(r.get("ethiopic_ratio") or 0)
    provider = str(r.get("provider") or provider_fallback)
    if not text:
        raise RuntimeError("Empty transcript from ASR")
    if ratio < 0.15:
        provider = provider + "+low-ethiopic"
    return text, provider


def _transcribe_ethio(path: str) -> tuple[str, str]:
    from asr_ethio import transcribe_file

    try:
        r = transcribe_file(path)
    except Exception as e:
        raise RuntimeError(f"Ethio-ASR failed: {e}") from e
    return _finalize_transcript(r, "ethio-asr")


def _transcribe_gemini(path: str) -> tuple[str, str]:
    from asr_gemini import transcribe_file

    try:
        r = transcribe_file(path)
    except Exception as e:
        raise RuntimeError(f"Gemini ASR failed: {e}") from e
    return _finalize_transcript(r, "gemini-asr")


def transcribe_amharic(path: str) -> tuple[str, str]:
    """Return (transcript, asr_provider). Prefer Gemini audio STT; fall back to Ethio-ASR."""
    engine = ASR_ENGINE
    if engine == "auto":
        engine = "gemini" if GEMINI_API_KEY else "ethio"

    errors: list[str] = []
    if engine == "gemini":
        try:
            return _transcribe_gemini(path)
        except Exception as e:
            print("Gemini ASR primary failed, falling back to Ethio:", e)
            errors.append(str(e))
            try:
                text, provider = _transcribe_ethio(path)
                return text, provider + "+gemini-fallback"
            except Exception as e2:
                errors.append(str(e2))
                raise RuntimeError("ASR failed: " + " | ".join(errors)) from e2

    if engine == "ethio":
        return _transcribe_ethio(path)

    raise RuntimeError(f"Unknown SKYKIN_ASR_ENGINE={ASR_ENGINE!r} (use auto|gemini|ethio)")

def clamp_scores(d: dict[str, Any]) -> dict[str, int]:
    out = {}
    for k in SCORE_KEYS:
        v = int(d.get(k, d.get(f"score_{k}", 3)))
        out[k] = max(1, min(5, v))
    return out


def _ollama_installed_models() -> list[str]:
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        if r.status_code != 200:
            return []
        names = []
        for m in (r.json().get("models") or []):
            n = str(m.get("name") or "").strip()
            if n:
                names.append(n)
        return names
    except Exception:
        return []


def _qa_system_prompt() -> str:
    return (
        "You are a professional call-center QA coach for Ahununu / SkyKin (Ethiopia). "
        "The transcript is usually Amharic (Ge'ez script), sometimes mixed with English. "
        "Score the AGENT performance only. Return JSON only with integer scores 1-5 for: "
        "greeting, knowledge, resolution, tone, procedure, closing, "
        "and notes (2-4 short sentences in English or Amharic). "
        "Rubric: 1=poor, 3=acceptable, 5=excellent. "
        "If transcript is empty, garbled, or too short to judge, use mid scores (2-3) "
        "and say so clearly in notes. Do not invent facts that are not in the transcript."
    )


def _extract_json_obj(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


def score_with_gemini(transcript: str, meta: dict) -> dict[str, Any] | None:
    key = GEMINI_API_KEY
    if not key:
        return None
    models = [GEMINI_MODEL]
    for m in ("gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"):
        if m not in models:
            models.append(m)
    prompt = (
        f"{_qa_system_prompt()}\n\n"
        f"Meta: {json.dumps(meta, ensure_ascii=False)}\n\n"
        f"Transcript:\n{transcript or '(empty)'}"
    )
    last_err = None
    for model in models:
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
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=120.0,
            )
            if r.status_code != 200:
                print("Gemini HTTP", model, r.status_code, r.text[:300])
                last_err = f"HTTP {r.status_code}"
                continue
            body = r.json()
            parts = (
                ((body.get("candidates") or [{}])[0].get("content") or {}).get("parts")
                or []
            )
            content = "".join(str(p.get("text") or "") for p in parts)
            data = _extract_json_obj(content)
            if not data:
                last_err = "empty/invalid JSON"
                continue
            return {
                "scores": clamp_scores(data),
                "notes": str(data.get("notes", "")).strip() or "Scored via Gemini",
                "provider": f"gemini:{model}",
            }
        except Exception as e:
            print("Gemini try failed", model, e)
            last_err = e
            continue
    print("Gemini unavailable:", last_err)
    return None


def score_call(transcript: str, meta: dict) -> dict[str, Any]:
    """Prefer Gemini (if key set), then Ollama, then heuristic."""
    return (
        score_with_gemini(transcript, meta)
        or score_with_ollama(transcript, meta)
        or score_heuristic(transcript)
    )


def score_with_ollama(transcript: str, meta: dict) -> dict[str, Any] | None:
    system = _qa_system_prompt()
    user = (
        f"Meta: {json.dumps(meta, ensure_ascii=False)}\n\n"
        f"Transcript:\n{transcript or '(empty)'}"
    )
    installed = _ollama_installed_models()
    # Prefer whatever is actually installed (3b on this PC).
    candidates: list[str] = []
    for m in [OLLAMA_MODEL, *OLLAMA_MODELS, "qwen2.5:3b", "qwen2.5:7b"]:
        if m and m not in candidates:
            candidates.append(m)
    if installed:
        candidates = [m for m in candidates if m in installed or any(m == i or i.startswith(m + ":") for i in installed)]
        # also allow exact installed names
        for i in installed:
            if i not in candidates:
                candidates.append(i)
    if not candidates:
        print("Ollama has no models installed")
        return None

    last_err = None
    for model in candidates:
        try:
            r = httpx.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=300.0,
            )
            if r.status_code != 200:
                print("Ollama HTTP", model, r.status_code, r.text[:200])
                last_err = f"HTTP {r.status_code}"
                continue
            content = (r.json().get("message") or {}).get("content") or ""
            data = json.loads(content)
            return {
                "scores": clamp_scores(data if isinstance(data, dict) else {}),
                "notes": str(data.get("notes", "")).strip() or "Scored via Ollama",
                "provider": f"ollama:{model}",
            }
        except Exception as e:
            print("Ollama try failed", model, e)
            last_err = e
            continue
    print("Ollama unavailable:", last_err)
    return None


def score_heuristic(transcript: str) -> dict[str, Any]:
    t = (transcript or "").strip()
    n = len(t)
    if n < 20:
        base = 2
        notes = "Transcript very short/empty — heuristic draft only. Install Ollama for real scoring."
    elif n < 120:
        base = 3
        notes = "Short Amharic transcript — heuristic draft. Install Ollama (qwen2.5) for real scoring."
    else:
        base = 4
        notes = "Heuristic draft from transcript length only. Install Ollama (qwen2.5) for real scoring."
    bump = 0
    if re.search(r"(ሰላም|እንደምን|hello|hi\b|good\s*(morning|afternoon))", t, re.I):
        bump = 1
    scores = {k: max(1, min(5, base + (bump if k in ("greeting", "tone") else 0))) for k in SCORE_KEYS}
    return {"scores": scores, "notes": notes, "provider": "heuristic"}


def set_job(job_id: str, **fields: Any) -> None:
    with _jobs_lock:
        job = _jobs.setdefault(job_id, {})
        job.update(fields)
        job["updated_at"] = time.time()


def run_job(job_id: str, path: str, meta: dict, filename: str) -> None:
    try:
        set_job(
            job_id,
            status="running",
            step="load",
            step_label=(
                "Loading Gemini audio STT…"
                if (ASR_ENGINE in ("gemini", "auto") and GEMINI_API_KEY)
                else "Loading Ethio-ASR Amharic (w2v-bert)…"
            ),
            progress=8,
            filename=filename,
        )
        set_job(
            job_id,
            step="transcribe",
            step_label="Transcribing Amharic with Gemini…",
            progress=35,
        )
        transcript, asr_provider = transcribe_amharic(path)
        set_job(
            job_id,
            step="evaluate",
            step_label="Evaluating call quality…",
            progress=70,
            transcript=transcript,
            asr_provider=asr_provider,
        )
        scored = score_call(transcript, meta)
        set_job(
            job_id,
            status="done",
            step="done",
            step_label="Done",
            progress=100,
            transcript=transcript,
            scores=scored["scores"],
            notes=scored["notes"],
            provider=scored.get("provider"),
            asr_provider=asr_provider,
            ok=True,
        )
    except Exception as e:
        set_job(
            job_id,
            status="error",
            step="error",
            step_label="Failed",
            progress=100,
            ok=False,
            error=str(e),
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.on_event("startup")
def _warm_ethio():
    """Load Ethio-ASR once so the first UI job does not fail / fall through."""
    try:
        from asr_ethio import get_ethio

        get_ethio()
        print("Startup: Ethio-ASR warmed")
    except Exception as e:
        print("Startup: Ethio-ASR warm failed:", e)


@app.get("/health")
def health():
    installed = _ollama_installed_models()
    return {
        "ok": True,
        "asr_engine": ASR_ENGINE,
        "asr_primary": (
            "gemini"
            if (ASR_ENGINE == "gemini" or (ASR_ENGINE == "auto" and GEMINI_API_KEY))
            else "ethio"
        ),
        "ethio_model": os.getenv("SKYKIN_ETHIO_ASR_MODEL", "badrex/Ethio-ASR-amharic"),
        "device": DEVICE,
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "ollama_installed": installed,
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL,
    }


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    meta: str = Form(""),
    caller: str = Form(""),
    agent_ext: str = Form(""),
):
    meta_obj: dict[str, Any] = {}
    if meta:
        try:
            meta_obj = json.loads(meta)
        except json.JSONDecodeError:
            meta_obj = {"raw_meta": meta}
    if caller:
        meta_obj["caller"] = caller
    if agent_ext:
        meta_obj["agent_ext"] = agent_ext

    raw = await file.read()
    if len(raw) < 500:
        return JSONResponse({"ok": False, "error": "Recording too short or empty"}, status_code=400)

    suffix = Path(file.filename or "call.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    job_id = uuid.uuid4().hex[:12]
    set_job(
        job_id,
        status="queued",
        step="upload",
        step_label="Recording received",
        progress=2,
        filename=file.filename or "recording.wav",
        ok=None,
    )
    threading.Thread(
        target=run_job,
        args=(job_id, tmp_path, meta_obj, file.filename or "recording.wav"),
        daemon=True,
    ).start()
    return {"ok": True, "job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return JSONResponse({"ok": False, "error": "Unknown job"}, status_code=404)
    return {"ok": True, **job}


@app.post("/v1/evaluate")
async def evaluate(
    file: UploadFile = File(...),
    meta: str = Form(""),
    task: str = Form("evaluation"),
    domain: str = Form(""),
    caller: str = Form(""),
    agent_ext: str = Form(""),
    direction: str = Form(""),
    duration: str = Form("0"),
):
    """Same contract as ecs-cc skykin_ai.php (blocking)."""
    meta_obj: dict[str, Any] = {}
    if meta:
        try:
            meta_obj = json.loads(meta)
        except json.JSONDecodeError:
            meta_obj = {"raw_meta": meta}
    meta_obj.setdefault("domain", domain)
    meta_obj.setdefault("caller", caller)
    meta_obj.setdefault("agent_ext", agent_ext)
    meta_obj.setdefault("direction", direction)
    meta_obj.setdefault("duration", int(duration or 0))
    meta_obj["task"] = task

    suffix = Path(file.filename or "call.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        raw = await file.read()
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        if len(raw) < 500:
            return JSONResponse({"ok": False, "error": "Recording too short or empty"}, status_code=400)
        transcript, asr_provider = transcribe_amharic(tmp_path)
        scored = score_call(transcript, meta_obj)
        return {
            "ok": True,
            "transcript": transcript,
            "scores": scored["scores"],
            "notes": scored["notes"],
            "provider": scored.get("provider"),
            "asr_provider": asr_provider,
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8100, reload=False)
