# Audio transcription pipeline

Command-line tool: pass a WAV or MP3 file, get JSON with full text, detected language, and per-segment start/end times in seconds.

## Setup and run

Python 3.10+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python transcribe.py path/to/recording.wav > transcript.json
```

MP3 is supported. Options: `--model base` (default `small`), `--max-mb 100` (default 50). The first run downloads model weights (network required); later runs use the cache. Transcription uses CPU with int8; larger models or long files take longer.

Example output:

```json
{
  "status": "completed",
  "language": "en",
  "text": "Hello, thanks for joining. Let us get started.",
  "segments": [
    {"start": 0.4, "end": 2.1, "text": "Hello, thanks for joining."},
    {"start": 2.5, "end": 3.8, "text": "Let us get started."}
  ]
}
```

If no speech is detected: `status` is `no_speech_detected`, empty `text`, empty `segments`. Missing, empty, unsupported, or oversized inputs produce error JSON on stderr and exit code 1. Extension and size checks are convenience guards; invalid audio is caught when decoding.

## Design choices and limits

- **Engine:** `faster-whisper` runs locally, supports multiple languages and segment timestamps, and avoids sending audio to a hosted API. Weights download on first use.
- **Output:** Text follows the model; only surrounding whitespace is stripped on segments. Timestamps are segment-level estimates, not word alignment. No summarization or rewriting.
- **Scope:** One file per invocation. The size cap limits accidental huge uploads on this single-process CLI. Long-form production use would need measured limits, background jobs, and careful chunking if audio is split.
- **VAD:** `vad_filter=True` skips likely silence (faster, less wasted work) but can drop quiet speech—worth checking on your recordings.

## Production design (not implemented)

Upload via authenticated API → private object storage → job record → queue. Workers transcribe outside the request path; clients poll by job id. Retention, encryption, and access control depend on the product.

Job states: `queued`, `processing`, `completed`, `failed`. Retry transient errors with backoff; fail fast on bad audio. Idempotent transcript writes avoid duplicates on retry. Monitor queue lag, latency, errors, and worker capacity.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use a fake model for JSON shape, no-speech handling, and file validation—no download, no accuracy measurement. For recognition quality, run the CLI on audio you know and compare text and timestamps.

## Verification (local)

After `pip install -r requirements.txt` in a venv:

- Four unit tests passed (`python -m unittest discover -s tests -v`).
- CLI smoke test on locally generated English speech (macOS `say`): valid JSON, `status: completed`, `language: en`, segments with `end >= start`. Synthetic speech only—not an accuracy study across speakers, noise, or languages.
- Nonexistent path: exit code 1, error JSON on stderr, empty stdout.
- `faster-whisper` 1.x passes `metadata_errors` to PyAV; PyAV 19 removed it. Pin `av>=18,<19` with `faster-whisper>=1.1,<2` in `requirements.txt`.

Repository: [audio-transcription-pipeline](https://github.com/ajaybenii/audio-transcription-pipeline).
