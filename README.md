# Audio transcription pipeline

This is a small Python command-line application that accepts a WAV or MP3 recording and returns a JSON transcript. It uses `faster-whisper` for speech recognition. Each segment includes its start and end time in seconds, measured from the beginning of the recording. It also reports the detected language.

## Run it

Python 3.10 or newer is recommended. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python transcribe.py path/to/recording.wav > transcript.json
```

On Windows, activate the environment with `.venv\Scripts\activate` instead. MP3 works the same way. You can choose a different model with `--model base` or raise the default 50 MB file limit with `--max-mb 100`. The first run may download model weights, so it needs an internet connection. Subsequent runs can reuse the cached model. This example runs on CPU with int8 computation; a larger model or CPU-only inference may take time.

Example successful output (illustrative):

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

If no speech is found, the status is `no_speech_detected`, the transcript is empty, and the segment list is empty. A missing, empty, unsupported, or oversized file returns an error JSON on stderr and a nonzero exit code. File extension and size checks are convenience checks, not proof that a file contains valid audio; the decoder handles malformed audio as an error.

## Decisions and limits

- I used `faster-whisper` because it runs locally, supports multilingual transcription and gives segment timestamps without requiring me to train a model. This also avoids sending the recording to a hosted speech API. The model still needs downloading on the first run.
- I kept the transcript close to the model output and only stripped whitespace around segments. The timestamps are model estimates, not word-level alignment. I did not add automatic rewriting or summarization because those steps could change what was said.
- The CLI processes one file at a time. Its file size limit prevents accidentally feeding a very large file to this simple local process. For longer recordings, I would increase the limit only after measuring memory and processing time, and I would use a background job in a service. I would not split the audio casually without handling offsets and speech that crosses chunk boundaries.
- `vad_filter=True` skips likely silent parts, which can reduce wasted processing. It can also miss quiet speech, so I would evaluate it on the expected recordings before using the system in a sensitive workflow.

## Production design (not implemented here)

For concurrent uploads, I would accept an authenticated upload through an API, store the audio in private object storage, create a job record, then enqueue its identifier. Workers would load the audio and run transcription separately from the request handler. The API would return a job identifier immediately and expose a status endpoint to retrieve the transcript when ready. Audio and transcript records would use retention rules, access control, encryption, and audit logs suited to the application.

For recovery, the job would move through `queued`, `processing`, `completed`, and `failed` states. A worker would retry transient failures with backoff and a retry limit; permanent decoding errors would fail immediately. The transcript write would be idempotent so a repeated job does not create duplicate results. I would monitor queue delay, processing time, error rate, and worker capacity. This architecture is a proposal for the assessment, not functionality in this repository.

## Tests

```bash
python -m unittest discover -s tests -v
```

The unit tests use a fake speech model to check JSON formatting, no-speech behavior, and input validation without a model download. They do not measure recognition accuracy. To check actual transcription, install the requirements and run the CLI on a short recording whose words you know, then compare the transcript and timestamps to the audio.

## Verification (local)

These checks were run in this project directory after `pip install -r requirements.txt` in a virtual environment:

- **Unit tests:** four tests passed (`python -m unittest discover -s tests -v`).
- **Real transcription:** the CLI completed successfully on locally generated English synthetic speech (macOS `say`), producing valid JSON with `status: "completed"`, `language: "en"`, and segment timestamps with `end >= start`. This was a **synthetic speech smoke test only**, not a broad accuracy evaluation across speakers, accents, noise, or languages.
- **Missing file:** `transcribe.py` with a nonexistent path exited with code **1** and printed an error JSON object on **stderr** (stdout stayed empty).
- **Dependencies:** `faster-whisper` 1.x requires PyAV’s `metadata_errors` argument on `av.open()`. PyAV **19.x** removed that parameter and caused runtime failures until `requirements.txt` pinned **`av>=18,<19`** alongside `faster-whisper>=1.1,<2`.

## Submit

Repository: [audio-transcription-pipeline](https://github.com/ajaybenii/audio-transcription-pipeline). Record a short English video explaining the pipeline, its output, trade-offs, and the production design above.
