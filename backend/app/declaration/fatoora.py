"""Fatoora — connecteur (démo OAuth + import factures).

L'API officielle Fatoora/TTN nécessite un partenariat / credentials entreprise.
En mode démo: l'utilisateur 'autorise' puis upload / sync des factures PDF-images.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

# sessions démo en mémoire
_SESSIONS: dict[str, dict[str, Any]] = {}


def create_auth_session() -> dict[str, Any]:
    token = secrets.token_urlsafe(16)
    _SESSIONS[token] = {
        "authorized": False,
        "created_at": time.time(),
        "provider": "fatoora-demo",
    }
    return {
        "auth_url": f"/fatoora/callback?token={token}",
        "token": token,
        "mode": "demo",
        "message": (
            "Mode démo: cliquez Autoriser pour simuler l'accès Fatoora. "
            "En production: OAuth TTN / Fatoora avec credentials entreprise."
        ),
    }


def authorize(token: str) -> dict[str, Any]:
    sess = _SESSIONS.get(token)
    if not sess:
        # create if missing (UI may call authorize with new token)
        _SESSIONS[token] = {"authorized": True, "created_at": time.time(), "provider": "fatoora-demo"}
        return {"ok": True, "token": token, "authorized": True}
    sess["authorized"] = True
    return {"ok": True, "token": token, "authorized": True}


def is_authorized(token: str | None) -> bool:
    if not token:
        return False
    sess = _SESSIONS.get(token)
    return bool(sess and sess.get("authorized"))
