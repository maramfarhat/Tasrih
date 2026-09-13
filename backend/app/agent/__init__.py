"""Agent Tasrih — assistant conversationnel (guide) pour la déclaration mensuelle."""

from fastapi import APIRouter

from app.agent.chat import router as chat_router
from app.agent.tts import router as tts_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(tts_router)

__all__ = ["router"]
