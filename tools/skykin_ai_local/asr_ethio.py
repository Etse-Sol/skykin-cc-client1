"""
Amharic transcription via latest Ethio-ASR.

Uses badrex/Ethio-ASR-amharic — monolingual w2v-bert-2.0 (best published Amharic WER ~22%).
Phone calls (8 kHz) will still have some gaps vs clean studio audio.
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np
import torch
from transformers import Wav2Vec2BertForCTC, Wav2Vec2BertProcessor

from audio_prep import ethiopic_ratio, load_mono_16k

# Latest Amharic specialist (2026 Ethio-ASR monolingual SFT).
ETHIO_MODEL = os.getenv("SKYKIN_ETHIO_ASR_MODEL", "badrex/Ethio-ASR-amharic")
CHUNK_SEC = float(os.getenv("SKYKIN_ASR_CHUNK_SEC", "30"))
OVERLAP_SEC = float(os.getenv("SKYKIN_ASR_OVERLAP_SEC", "4"))

_proc = None
_model = None
_loaded_id = None


def get_ethio():
    global _proc, _model, _loaded_id
    if _model is None or _loaded_id != ETHIO_MODEL:
        print(f"Loading latest Ethio-ASR Amharic model={ETHIO_MODEL} …")
        _proc = Wav2Vec2BertProcessor.from_pretrained(ETHIO_MODEL)
        _model = Wav2Vec2BertForCTC.from_pretrained(ETHIO_MODEL)
        _model.eval()
        _loaded_id = ETHIO_MODEL
        print("Ethio-ASR Amharic ready (w2v-bert-2.0).")
    return _proc, _model


def _silence_mask(audio: np.ndarray, sr: int, frame_ms: int = 30, thr: float = 0.012) -> np.ndarray:
    """True where frame has speech energy."""
    n = max(1, int(sr * frame_ms / 1000))
    if len(audio) < n:
        return np.ones(1, dtype=bool)
    pad = (-len(audio)) % n
    if pad:
        audio = np.pad(audio, (0, pad))
    frames = audio.reshape(-1, n)
    energy = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    return energy > thr


def _decode_chunk(proc, model, audio: np.ndarray, sr: int) -> str:
    inputs = proc(audio, sampling_rate=sr, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)
    return proc.batch_decode(ids)[0].strip()


def _merge_overlap(parts: list[str]) -> str:
    if not parts:
        return ""
    out = parts[0]
    for p in parts[1:]:
        if not p:
            continue
        a = out.split()
        b = p.split()
        best = 0
        for n in range(min(8, len(a), len(b)), 0, -1):
            if a[-n:] == b[:n]:
                best = n
                break
        out = (out + " " + " ".join(b[best:])).strip()
    return out


def transcribe_file(path: str) -> dict[str, Any]:
    audio, sr = load_mono_16k(path)
    proc, model = get_ethio()

    # Do not aggressively gate silence on telephony — it can wipe quiet Amharic speech.
    chunk = int(CHUNK_SEC * sr)
    hop = max(int((CHUNK_SEC - OVERLAP_SEC) * sr), sr)
    parts: list[str] = []
    for i in range(0, len(audio), hop):
        c = audio[i : i + chunk]
        if len(c) < sr // 2:
            break
        if float(np.sqrt(np.mean(c * c) + 1e-12)) < 0.004:
            if i + chunk >= len(audio):
                break
            continue
        text = _decode_chunk(proc, model, c, sr)
        if text:
            parts.append(text)
        if i + chunk >= len(audio):
            break

    full = _merge_overlap(parts).strip()
    ratio = ethiopic_ratio(full)
    print(
        f"Ethio-ASR model={ETHIO_MODEL} chars={len(full)} "
        f"eth_ratio={ratio:.2f} dur={len(audio)/sr:.1f}s chunks={len(parts)}"
    )
    return {
        "text": full,
        "ethiopic_ratio": ratio,
        "provider": f"ethio-asr-latest:{ETHIO_MODEL}",
        "duration_sec": round(len(audio) / sr, 1),
        "model_note": "Latest Amharic Ethio-ASR (w2v-bert-2.0). Phone 8kHz audio may still have gaps.",
    }
