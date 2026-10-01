from __future__ import annotations

import subprocess
from pathlib import Path

_model = None
_model_name: str | None = None


def _get_model(name: str):
    global _model, _model_name
    if _model is None or _model_name != name:
        from faster_whisper import WhisperModel

        # CPU برای سازگاری؛ اگر CUDA داری device="cuda" بگذار
        _model = WhisperModel(name, device="cpu", compute_type="int8")
        _model_name = name
    return _model


def ogg_to_wav(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-400:]}")
    return dst


def transcribe(audio_path: Path, model_name: str = "base", language: str = "fa") -> str:
    model = _get_model(model_name)
    segments, _info = model.transcribe(
        str(audio_path),
        language=language or None,
        vad_filter=True,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text
