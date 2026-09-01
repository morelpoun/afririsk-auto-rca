"""Authentification JWT et RBAC minimal (voir docs/auth.md).

Périmètre volontairement limité (v0.6) : trois rôles fixes (admin, agent,
viewer), pas de refresh token, pas de réinitialisation de mot de passe par
email. Suffisant pour distinguer qui peut souscrire une police/déclarer un
sinistre (admin, agent) de la consultation, qui reste publique pour l'instant
(voir avertissement dans docs/auth.md — pas encore de protection des lectures).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import models
from app.database.session import get_db

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-insecure-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

ROLES = ("admin", "agent", "viewer")

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user: models.User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "role": user.role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise (en-tête Authorization: Bearer <token>).",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide ou expiré.") from exc

    user = db.get(models.User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable ou désactivé.")
    return user


def require_roles(*roles: str):
    """Dépendance FastAPI : autorise uniquement les utilisateurs dont le rôle
    est dans `roles`. Usage : `Depends(auth.require_roles("admin", "agent"))`.
    """

    def _check(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle '{user.role}' non autorisé pour cette action (requiert : {', '.join(roles)}).",
            )
        return user

    return _check
