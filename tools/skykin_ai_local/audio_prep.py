"""Load call WAV → mono float32 @ 16 kHz (telephony often 8 kHz stereo)."""
from __future__ import annotations

import numpy as np


def _peak_norm(audio: np.ndarray) -> np.ndarray:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-4:
        audio = audio / peak * 0.95
    return audio.astype(np.float32)


def _resample_soxr(audio: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    if orig_sr == target_sr:
        return audio.astype(np.float32)
    try:
        import soxr

        return soxr.resample(audio.astype(np.float32), orig_sr, target_sr).astype(np.float32)
    except Exception:
        duration = len(audio) / float(orig_sr)
        n_out = max(1, int(duration * target_sr))
        x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
        return np.interp(x_new, x_old, audio).astype(np.float32)


def load_mono_16k(path: str) -> tuple[np.ndarray, int]:
    """Return (audio_float32_mono, 16000) with high-quality resample."""
    path = str(path)
    try:
        import soundfile as sf

        data, rate = sf.read(path, always_2d=True, dtype="float32")
        # Mix L+R (call recordings usually have both sides)
        mono = data.mean(axis=1)
        mono = _resample_soxr(mono, int(rate), 16000)
        return _peak_norm(mono), 16000
    except Exception:
        pass

    try:
        import av

        container = av.open(path)
        stream = container.streams.audio[0]
        resampler = av.audio.resampler.AudioResampler(format="flt", layout="mono", rate=16000)
        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                arr = out.to_ndarray()
                if arr.ndim > 1:
                    arr = arr.mean(axis=0)
                chunks.append(np.asarray(arr, dtype=np.float32).reshape(-1))
        for out in resampler.resample(None):
            arr = out.to_ndarray()
            if arr.ndim > 1:
                arr = arr.mean(axis=0)
            chunks.append(np.asarray(arr, dtype=np.float32).reshape(-1))
        container.close()
        if not chunks:
            raise RuntimeError("no audio decoded")
        return _peak_norm(np.concatenate(chunks)), 16000
    except Exception:
        pass

    import wave

    with wave.open(path, "rb") as w:
        nch = w.getnchannels()
        rate = w.getframerate()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise RuntimeError(f"unsupported sample width {width}")
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1)
    data = _resample_soxr(data, int(rate), 16000)
    return _peak_norm(data), 16000


def write_wav_16k(path: str, audio: np.ndarray) -> None:
    import wave

    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())


def ethiopic_ratio(text: str) -> float:
    if not text:
        return 0.0
    eth = sum(1 for ch in text if "\u1200" <= ch <= "\u137F")
    letters = sum(1 for ch in text if ch.isalpha() or ("\u1200" <= ch <= "\u137F"))
    if letters == 0:
        return 0.0
    return eth / float(letters)
