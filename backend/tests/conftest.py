"""Fixtures partagées : jetons d'authentification prêts à l'emploi pour les
tests qui touchent des endpoints protégés (POST /policies, /claims, ...).
Chaque fixture crée un compte dédié avec un email unique (uuid) pour rester
indépendante de l'état accumulé dans la base SQLite locale entre les
exécutions de la suite.
"""
from __future__ import annotations

import uuid

import pytest

from app import auth
from app.database import crud
from app.database.session import SessionLocal, init_db


def _make_user_headers(role: str) -> dict[str, str]:
    init_db()
    db = SessionLocal()
    try:
        email = f"{role}-{uuid.uuid4().hex[:12]}@test.afririsk"
        user = crud.create_user(db, email, auth.hash_password("test-password-123"), role)
        db.commit()
        db.refresh(user)
        token = auth.create_access_token(user)
    finally:
        db.close()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_headers() -> dict[str, str]:
    return _make_user_headers("agent")


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return _make_user_headers("admin")


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    return _make_user_headers("viewer")
