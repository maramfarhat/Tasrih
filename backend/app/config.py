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

    # voix de l'assistant : "edge" (neural, en ligne) ou "piper" (hors ligne)
    tts_engine: str = "edge"
    tts_voice: str = "fr-FR-RemyMultilingualNeural"
    tts_piper_voice: str = "fr_FR-tom-medium"


settings = Settings()
DATA.mkdir(parents=True, exist_ok=True)
