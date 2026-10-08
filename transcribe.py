"""Transcribe one WAV or MP3 recording to JSON using faster-whisper."""

import argparse
import json
import sys
from pathlib import Path


SUPPORTED_EXTENSIONS = {".wav", ".mp3"}


def validate_audio(path_arg: str, max_mb: int) -> Path:
    path = Path(path_arg)
    if not path.is_file():
        raise ValueError(f"Audio file does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Supported audio formats are WAV and MP3.")
    size = path.stat().st_size
    if size == 0:
        raise ValueError("Audio file is empty.")
    if size > max_mb * 1024 * 1024:
        raise ValueError(f"Audio file exceeds the {max_mb} MB limit.")
    return path


def transcribe_audio(path: Path, model) -> dict:
    # faster-whisper returns a generator: inference finishes as it is consumed.
    segments, info = model.transcribe(str(path), task="transcribe", vad_filter=True)
    rows = []
    for segment in segments:
        content = segment.text.strip()
        if content:
            rows.append(
                {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": content,
                }
            )

    return {
        "status": "completed" if rows else "no_speech_detected",
        "language": info.language if rows else None,
        "text": " ".join(row["text"] for row in rows),
        "segments": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio_path", help="Path to a WAV or MP3 recording")
    parser.add_argument("--model", default="small", help="Whisper model size (default: small)")
    parser.add_argument("--max-mb", type=int, default=50, help="Upload size limit in MB (default: 50)")
    args = parser.parse_args(argv)
    if args.max_mb <= 0:
        parser.error("--max-mb must be positive")

    try:
        path = validate_audio(args.audio_path, args.max_mb)
        # Lazy import: validation and unit tests do not need the heavy model package.
        from faster_whisper import WhisperModel

        model = WhisperModel(args.model, device="cpu", compute_type="int8")
        result = transcribe_audio(path, model)
    except Exception as exc:
        # Errors go to stderr; stdout is reserved for successful JSON output.
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
