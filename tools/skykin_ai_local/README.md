# SkyKin AI — local PC test (Amharic)

Test on your PC with sample recordings first. Connect to ecs-cc later.

## Your PC notes

- ~16 GB RAM, no NVIDIA GPU detected → use Whisper **`small`** on CPU (slower but OK for tests).
- Python 3.14 may break `torch`. Prefer a **Python 3.11 or 3.12** venv if install fails.

## Setup (once)

```powershell
cd C:\Users\hp\skykin-fusionpbx\tools\skykin_ai_local
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional (better scores): install [Ollama](https://ollama.com), then:

```powershell
ollama pull qwen2.5:7b
```

## Test with a recording

```powershell
.\.venv\Scripts\Activate.ps1
python test_recording.py C:\path\to\amharic_call.wav
```

## Local website (recommended)

Same flow as call-center Evaluation, on your PC:

```powershell
.\.venv\Scripts\Activate.ps1
python server.py
```

Open in Chrome: **http://127.0.0.1:8100**

1. Choose / drop a recording  
2. Click **Start evaluation**  
3. Watch progress: load → transcribe (Amharic) → evaluate  
4. See scores + transcript  

Health API: http://127.0.0.1:8100/health

```powershell
python test_recording.py C:\path\to\amharic_call.wav --url http://127.0.0.1:8100
```

## Amharic ASR

Default: **`badrex/Ethio-ASR-amharic`** (Amharic specialist, already cached).  
Higher (when download finishes): `multilingual-300M` → `600M` → `1B`.

```powershell
$env:SKYKIN_ETHIO_ASR_MODEL='badrex/Ethio-ASR-multilingual-600M'
```

Overlapping chunks improve transcript flow. Audio is mono 16 kHz. Whisper is not used.

Point ecs-cc `/etc/skykin/ai.env`:

```
SKYKIN_AI=on
SKYKIN_AI_MODE=skykin
SKYKIN_AI_BASE_URL=http://YOUR-PC-IP:8100
```
