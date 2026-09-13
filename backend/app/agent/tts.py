"""TTS de l'assistant.

Moteur par défaut : **Edge TTS** (voix neuronales françaises, gratuites, en ligne),
avec une prosodie adaptée au ton du message (débit/hauteur variables).

Repli : **Piper** local (hors ligne, CPU) si Edge échoue ou si `TTS_ENGINE=piper`.
Dernier recours : le front bascule sur la voix du navigateur (503).
"""

from __future__ import annotations

import io
import threading
import wave

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel

from app.agent.voice import TONES, enhance_for_speech, prosody_for
from app.config import BACKEND, settings

router = APIRouter(prefix="/agent", tags=["agent"])

TTS_DIR = BACKEND / "data" / "tts"

_piper_lock = threading.Lock()
_piper_voice = None


class TTSBody(BaseModel):
    text: str
    tone: str = "neutral"
    lang: str = "fr"


# —— moteur Edge (neural, en ligne) ——
async def _synth_edge(text: str, tone: str, voice: str) -> tuple[bytes, str]:
    try:
        import edge_tts  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("edge-tts n'est pas installé") from exc

    prosody = prosody_for(tone)
    communicate = edge_tts.Communicate(
        enhance_for_speech(text),
        voice,
        rate=prosody["rate"],
        pitch=prosody["pitch"],
        volume=prosody["volume"],
    )
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio" and chunk.get("data"):
            chunks.append(chunk["data"])
    if not chunks:
        raise RuntimeError("edge-tts: aucun audio reçu")
    return b"".join(chunks), "audio/mpeg"


# —— moteur Piper (local, hors ligne) ——
def _get_piper():
    global _piper_voice
    if _piper_voice is not None:
        return _piper_voice
    try:
        from piper.voice import PiperVoice  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("piper-tts n'est pas installé") from exc
    model = TTS_DIR / f"{settings.tts_piper_voice}.onnx"
    if not model.exists():
        raise RuntimeError(f"voix Piper absente: {model.name}")
    _piper_voice = PiperVoice.load(str(model))
    return _piper_voice


def _synth_piper(text: str) -> tuple[bytes, str]:
    with _piper_lock:
        voice = _get_piper()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            voice.synthesize_wav(text, wav)
    return buf.getvalue(), "audio/wav"


@router.get("/tts/status")
def tts_status() -> dict:
    return {
        "engine": settings.tts_engine,
        "voice": settings.tts_voice,
        "voice_ar": settings.tts_voice_ar,
        "piper_voice": settings.tts_piper_voice,
        "piper_available": (TTS_DIR / f"{settings.tts_piper_voice}.onnx").exists(),
    }


@router.post("/tts")
async def tts(body: TTSBody) -> Response:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "Texte vide")
    text = text[:600]
    tone = body.tone if body.tone in TONES else "neutral"

    data: bytes | None = None
    mime = "audio/mpeg"
    voice = settings.tts_voice_ar if body.lang == "ar" else settings.tts_voice

    # 1) Edge (neural) si demandé
    if settings.tts_engine != "piper":
        try:
            data, mime = await _synth_edge(text, tone, voice)
        except Exception:
            data = None

    # 2) repli Piper (local)
    if data is None:
        try:
            data, mime = await run_in_threadpool(_synth_piper, text)
        except Exception as exc:
            raise HTTPException(503, f"TTS indisponible: {exc}") from exc

    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Length": str(len(data)), "Cache-Control": "no-store"},
    )
