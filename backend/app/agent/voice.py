"""Voix de l'assistant : classement du ton et prosodie associée.

Chaque message est classé selon son contenu (salutation, consigne, succès,
avertissement, erreur) puis converti en réglages de débit/hauteur pour donner
une voix « vivante » qui colle au propos, au lieu d'un débit constant.
"""

from __future__ import annotations

import random

Tone = str  # "warm" | "neutral" | "success" | "warning" | "error"
TONES = ("warm", "neutral", "success", "warning", "error")

_ERROR_MARKERS = (
    "erreur",
    "impossible",
    "échec",
    "echec",
    "problème",
    "probleme",
    "désolé",
    "desole",
    "indisponible",
)

_WARNING_MARKERS = (
    "attention",
    "vérifiez",
    "verifiez",
    "à vérifier",
    "a verifier",
    "manquant",
    "peu confiante",
    "risque",
    "n'est pas lu",
    "n’est pas lu",
    "pas lu",
    "corrigez",
    "incomplet",
)

_SUCCESS_MARKERS = (
    "parfait",
    "très bien",
    "tres bien",
    "bravo",
    "c'est prêt",
    "est prête",
    "bien reçu",
    "j'ai bien",
    "j’ai bien",
    "prête",
    "réussi",
)

_WARM_MARKERS = (
    "bonjour",
    "bienvenue",
    "je suis karim",
    "avec plaisir",
    "aidé",
)


def classify_tone(text: str, step: int | None = None) -> Tone:
    t = (text or "").lower()

    if any(m in t for m in _ERROR_MARKERS):
        return "error"
    if any(m in t for m in _WARNING_MARKERS):
        return "warning"
    if any(m in t for m in _SUCCESS_MARKERS):
        return "success"
    if step is not None and step <= 0:
        return "warm"
    if any(m in t for m in _WARM_MARKERS):
        return "warm"
    return "neutral"


_BASE: dict[str, dict[str, int]] = {
    "warm": {"rate": -4, "pitch": -2},
    "neutral": {"rate": 0, "pitch": 0},
    "success": {"rate": 5, "pitch": 2},
    "warning": {"rate": -11, "pitch": -4},
    "error": {"rate": -8, "pitch": -2},
}


def prosody_for(tone: Tone) -> dict[str, str]:
    """Réglages edge-tts (rate/pitch/volume) avec une petite variation naturelle."""
    base = _BASE.get(tone, _BASE["neutral"])
    rate = base["rate"] + random.randint(-2, 2)
    pitch = base["pitch"] + random.randint(-1, 1)
    return {"rate": f"{rate:+d}%", "pitch": f"{pitch:+d}Hz", "volume": "+0%"}


def enhance_for_speech(text: str) -> str:
    """Améliore le phrasé : pauses après ponctuation, souffle après les deux-points."""
    import re

    out = re.sub(r"\s+", " ", (text or "").strip())
    # petite respiration après deux-points et point-virgule
    out = out.replace(" :", ", ").replace(":", ", ").replace(" ; ", ", ")
    # marquer les montants/nombres pour un débit posé
    out = re.sub(r"(\d)\s*TND\b", r"\1 dinars", out)
    return out


def tone_for_reply(text: str, declared: str | None = None, step: int | None = None) -> Tone:
    """Ton déclaré par l'agent s'il est valide, sinon déduit du texte."""
    if declared in TONES:
        return declared
    return classify_tone(text, step)
