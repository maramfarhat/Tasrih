"""Routes agent : /agent/guidance (proactif) et /agent/chat (conversation)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.guidance import guidance_for, suggestions_for
from app.agent.prompts import build_messages
from app.agent.voice import classify_tone
from app.config import settings
from app.knowledge import search as kb_search

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentContext(BaseModel):
    step: int | None = None
    step_label: str | None = None
    q_index: int | None = None
    profile: dict[str, Any] | None = None
    cif: dict[str, Any] | None = None
    rne: dict[str, Any] | None = None
    onboarding: dict[str, Any] | None = None
    employees: list[dict[str, Any]] | None = None
    invoices: list[dict[str, Any]] | None = None
    amounts: dict[str, Any] | None = None
    needs_user_review: list[str] | None = None
    confidence: float | None = None
    logged_in: bool | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    context: AgentContext = Field(default_factory=AgentContext)
    lang: str = "fr"


class GuidanceRequest(BaseModel):
    step: int | None = None
    context: AgentContext = Field(default_factory=AgentContext)
    lang: str = "fr"


class AgentReply(BaseModel):
    reply: str
    suggestions: list[str] = Field(default_factory=list)
    highlight: str | None = None
    step: int | None = None
    tone: str = "neutral"
    source: str = "guidance"  # guidance | llm


def _context_dict(ctx: AgentContext, step: int | None) -> dict[str, Any]:
    data = ctx.model_dump()
    if step is not None:
        data["step"] = step
    data["step_label"] = data.get("step_label") or ""
    return data


@router.post("/guidance", response_model=AgentReply)
def agent_guidance(body: GuidanceRequest) -> AgentReply:
    """Message proactif pour l'écran courant (pas d'appel IA : réponse instantanée)."""
    context = _context_dict(body.context, body.step)
    guide = guidance_for(body.step, context, body.lang)
    return AgentReply(
        reply=guide["message"],
        suggestions=guide["suggestions"],
        highlight=guide["highlight"],
        step=body.step,
        tone=classify_tone(guide["message"], body.step),
        source="guidance",
    )


@router.post("/chat", response_model=AgentReply)
def agent_chat(body: ChatRequest) -> AgentReply:
    """Réponse conversationnelle basée sur le contexte de l'étape."""
    context = _context_dict(body.context, body.context.step)
    guide = guidance_for(body.context.step, context, body.lang)

    history = [m.model_dump() for m in body.messages]
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")

    if not settings.groq_api_key:
        return AgentReply(
            reply=guide["message"],
            suggestions=guide["suggestions"],
            highlight=guide["highlight"],
            step=body.context.step,
            tone=classify_tone(guide["message"], body.context.step),
            source="guidance",
        )

    try:
        from groq import Groq

        # RAG : passages du guide officiel pertinents pour la question posée.
        sources = kb_search.search_chunks(last_user, 4) if last_user else []
        client = Groq(api_key=settings.groq_api_key)
        messages = build_messages(history, context, guide["message"], sources, lang=body.lang)
        completion = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.4,
            max_tokens=220,
            messages=messages,  # type: ignore[arg-type]
        )
        reply = (completion.choices[0].message.content or "").strip()
    except Exception:
        reply = ""

    if not reply:
        reply = guide["message"]
        source = "guidance"
    else:
        source = "llm"

    return AgentReply(
        reply=reply,
        suggestions=[] if source == "llm" else guide["suggestions"],
        highlight=guide["highlight"] if not last_user else None,
        step=body.context.step,
        tone=classify_tone(reply, body.context.step),
        source=source,
    )


@router.get("/suggestions")
def agent_suggestions(step: int | None = None, lang: str = "fr") -> dict[str, list[str]]:
    return {"suggestions": suggestions_for(step, {}, lang)}
