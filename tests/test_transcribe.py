import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from transcribe import transcribe_audio, validate_audio


class FakeModel:
    def __init__(self, segments):
        self.segments = segments

    def transcribe(self, path, *, task, vad_filter):
        assert path.endswith(".wav")
        assert task == "transcribe"
        assert vad_filter is True
        return iter(self.segments), SimpleNamespace(language="en")


class TranscriptionTests(unittest.TestCase):
    def test_transcript_and_timestamps(self):
        model = FakeModel(
            [
                SimpleNamespace(start=0.4123, end=2.1234, text=" Hello. "),
                SimpleNamespace(start=2.5, end=3.75, text=" Welcome! "),
            ]
        )
        result = transcribe_audio(Path("sample.wav"), model)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["text"], "Hello. Welcome!")
        self.assertEqual(result["segments"][0], {"start": 0.412, "end": 2.123, "text": "Hello."})

    def test_no_speech(self):
        result = transcribe_audio(Path("sample.wav"), FakeModel([]))
        self.assertEqual(
            result,
            {"status": "no_speech_detected", "language": None, "text": "", "segments": []},
        )

    def test_invalid_or_oversized_input(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            empty = folder / "empty.wav"
            empty.touch()
            with self.assertRaisesRegex(ValueError, "empty"):
                validate_audio(str(empty), 1)

            wrong_format = folder / "audio.txt"
            wrong_format.write_bytes(b"audio")
            with self.assertRaisesRegex(ValueError, "formats"):
                validate_audio(str(wrong_format), 1)

            too_big = folder / "large.MP3"
            too_big.write_bytes(b"x" * (1024 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "exceeds"):
                validate_audio(str(too_big), 1)

    def test_missing_file(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            validate_audio("missing.wav", 1)


if __name__ == "__main__":
    unittest.main()
