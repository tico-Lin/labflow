"""Extra tests for reasoning_routes coverage."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import security
from app.main import app


def _override_optional(payload):
    app.dependency_overrides[security.get_current_user_optional] = lambda: payload


def _override_required(payload):
    app.dependency_overrides[security.get_current_user] = lambda: payload


def _clear_overrides():
    app.dependency_overrides.pop(security.get_current_user_optional, None)
    app.dependency_overrides.pop(security.get_current_user, None)


@pytest.mark.integration
def test_reasoning_offline_forbidden(test_client: TestClient):
    offline = {"id": 0, "role": "offline", "is_offline": True}
    _override_optional(offline)
    try:
        chain_id = str(uuid4())
        resp = test_client.post(
            "/reasoning/chains",
            json={"name": "c", "description": "d", "nodes": []},
        )
        assert resp.status_code == 403

        resp = test_client.put(
            f"/reasoning/chains/{chain_id}",
            json={"name": "x"},
        )
        assert resp.status_code == 403

        resp = test_client.delete(f"/reasoning/chains/{chain_id}")
        assert resp.status_code == 403

        resp = test_client.post(
            f"/reasoning/chains/{chain_id}/execute",
            json={"input_data": {}},
        )
        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.integration
def test_reasoning_execution_not_found(test_client: TestClient, monkeypatch):
    _override_required({"id": 1, "role": "admin"})
    try:
        monkeypatch.setattr(
            "app.api.reasoning_routes.ReasoningService.get_execution",
            lambda self, execution_id: None,
        )
        resp = test_client.get(f"/reasoning/executions/{uuid4()}")
        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.integration
def test_reasoning_history_not_found(test_client: TestClient, monkeypatch):
    _override_required({"id": 1, "role": "admin"})
    try:
        monkeypatch.setattr(
            "app.api.reasoning_routes.ReasoningService.get_execution_history",
            lambda self, chain_id, days=30: None,
        )
        resp = test_client.get(f"/reasoning/chains/{uuid4()}/history")
        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.integration
def test_reasoning_list_chain_executions_error(test_client: TestClient, monkeypatch):
    _override_required({"id": 1, "role": "admin"})
    try:
        monkeypatch.setattr(
            "app.api.reasoning_routes.ReasoningService.list_executions",
            lambda self, chain_id, skip=0, limit=20: (_ for _ in ()).throw(
                Exception("boom")
            ),
        )
        resp = test_client.get(f"/reasoning/chains/{uuid4()}/executions")
        assert resp.status_code == 400
    finally:
        _clear_overrides()


@pytest.mark.integration
def test_reasoning_list_chains_error(test_client: TestClient, monkeypatch):
    _override_optional({"id": 1, "role": "admin", "is_offline": False})
    try:
        monkeypatch.setattr(
            "app.api.reasoning_routes.ReasoningService.list_chains",
            lambda self, skip=0, limit=10: (_ for _ in ()).throw(Exception("boom")),
        )
        resp = test_client.get("/reasoning/chains")
        assert resp.status_code == 400
    finally:
        _clear_overrides()
