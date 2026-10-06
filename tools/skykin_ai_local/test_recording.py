"""
Test local AI with a recording file (no server needed for one-shot).

  python test_recording.py path/to/call.wav

Or against a running server:

  python test_recording.py path/to/call.wav --url http://127.0.0.1:8100
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows consoles are often cp1252 — Amharic needs UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("recording", type=Path, help="WAV/MP3/etc.")
    p.add_argument("--url", default="", help="If set, POST to /v1/evaluate on this base URL")
    args = p.parse_args()
    path: Path = args.recording
    if not path.is_file():
        print("File not found:", path)
        return 1

    if args.url:
        import httpx

        base = args.url.rstrip("/")
        with path.open("rb") as f:
            r = httpx.post(
                f"{base}/v1/evaluate",
                files={"file": (path.name, f, "audio/wav")},
                data={"task": "evaluation", "meta": json.dumps({"source": "local_test"})},
                timeout=300.0,
            )
        print("HTTP", r.status_code)
        try:
            print(json.dumps(r.json(), ensure_ascii=False, indent=2))
        except Exception:
            print(r.text[:2000])
        return 0 if r.status_code == 200 else 2

    # In-process (loads Whisper once)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from server import score_heuristic, score_with_ollama, transcribe_amharic

    print("Transcribing (Amharic)…", path)
    text = transcribe_amharic(str(path))
    print("--- transcript ---")
    print(text or "(empty)")
    scored = score_with_ollama(text, {"source": "local_test"}) or score_heuristic(text)
    print("--- scores ---")
    print(json.dumps(scored, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
