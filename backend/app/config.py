from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_vision_model: str = "openai/gpt-oss-120b"

    # Accès à la vue administration DGI (/admin) — séparé du contribuable.
    admin_password: str = "dgi-admin"

    # voix de l'assistant : "edge" (neural, en ligne) ou "piper" (hors ligne)
    tts_engine: str = "edge"
    # Voix française native (éviter les voix "Multilingual" qui déforment la prononciation).
    tts_voice: str = "fr-FR-HenriNeural"
    # Voix arabe (arabe standard clair / فصحى) utilisée quand l'interface est en arabe.
    tts_voice_ar: str = "ar-SA-HamedNeural"
    tts_piper_voice: str = "fr_FR-tom-medium"


settings = Settings()
DATA.mkdir(parents=True, exist_ok=True)
