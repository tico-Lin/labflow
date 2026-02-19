"""
Extra tests for security helpers.
"""

import pytest
from fastapi import HTTPException

from app import security


def test_get_bearer_token_missing():
    with pytest.raises(HTTPException) as exc:
        security.get_bearer_token(None)
    assert exc.value.status_code == 401


def test_get_bearer_token_invalid_scheme():
    with pytest.raises(HTTPException) as exc:
        security.get_bearer_token("Basic abc")
    assert exc.value.status_code == 401


def test_verify_token_invalid():
    with pytest.raises(security.JWTError):
        security.verify_token("invalid.token.value")


def test_create_and_verify_tokens():
    access = security.create_access_token({"sub": "1", "username": "u", "role": "admin"})
    refresh = security.create_refresh_token({"sub": "1", "username": "u"})
    assert access
    assert refresh
    payload = security.verify_token(access)
    assert payload["sub"] == "1"
    assert payload["role"] == "admin"


def test_create_access_token_error(monkeypatch):
    monkeypatch.setattr(security.jwt_module, "encode", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(security.JWTError):
        security.create_access_token({"sub": "1", "username": "u", "role": "admin"})


def test_create_refresh_token_error(monkeypatch):
    monkeypatch.setattr(security.jwt_module, "encode", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(security.JWTError):
        security.create_refresh_token({"sub": "1", "username": "u"})


def test_verify_token_expired(monkeypatch):
    monkeypatch.setattr(security.jwt_module, "decode", lambda *args, **kwargs: (_ for _ in ()).throw(security.jwt_module.ExpiredSignatureError("exp")))
    with pytest.raises(security.JWTError):
        security.verify_token("expired")


def test_verify_token_generic_error(monkeypatch):
    monkeypatch.setattr(security.jwt_module, "decode", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(security.JWTError):
        security.verify_token("bad")


def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc:
        security.get_current_user("Bearer invalid.token")
    assert exc.value.status_code == 401


def test_get_current_admin_forbidden():
    with pytest.raises(HTTPException) as exc:
        security.get_current_admin({"id": 1, "role": "viewer"})
    assert exc.value.status_code == 403


def test_get_current_admin_allows():
    user = {"id": 1, "role": "admin"}
    assert security.get_current_admin(user) == user
