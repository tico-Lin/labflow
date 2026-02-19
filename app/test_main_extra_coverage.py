"""Extra tests for main.py coverage."""

import pytest
from fastapi.testclient import TestClient

from app import models


@pytest.mark.integration
def test_root_and_health(test_client: TestClient):
    resp = test_client.get("/")
    assert resp.status_code == 200
    assert "LabFlow API is running" in resp.json()["message"]

    resp = test_client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert "offline_mode" in payload


@pytest.mark.integration
def test_i18n_locales(test_client: TestClient):
    resp = test_client.get("/i18n/locales")
    assert resp.status_code == 200
    locales = resp.json()["locales"]
    assert isinstance(locales, list)


@pytest.mark.integration
def test_i18n_translations_success(test_client: TestClient):
    resp = test_client.get("/i18n/translations/zh")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["locale"] == "zh"
    assert "translations" in payload
    assert isinstance(payload["translations"], dict)


@pytest.mark.integration
def test_i18n_translations_missing_locale(test_client: TestClient):
    resp = test_client.get("/i18n/translations/xx")
    assert resp.status_code == 404


@pytest.mark.integration
def test_i18n_translate_key(test_client: TestClient):
    resp = test_client.get("/i18n/translate/zh/common.name")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["locale"] == "zh"
    assert payload["key"] == "common.name"
    assert "translation" in payload


@pytest.mark.integration
def test_analysis_tools_list(test_client: TestClient):
    resp = test_client.get("/analysis/tools")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.integration
def test_analysis_run_error(test_client: TestClient, monkeypatch):
    from app.services.analysis_service import AnalysisService, AnalysisServiceError

    def mock_run_tool(*args, **kwargs):
        raise AnalysisServiceError("boom")

    monkeypatch.setattr(AnalysisService, "run_tool", mock_run_tool)

    resp = test_client.post(
        "/analysis/run",
        json={"tool_id": "x", "file_id": 1, "parameters": {}, "store_output": False},
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_auth_register_duplicate_username(test_client: TestClient):
    resp = test_client.post(
        "/auth/register",
        json={"username": "user1", "password": "password123"},
    )
    assert resp.status_code == 201

    resp = test_client.post(
        "/auth/register",
        json={"username": "user1", "password": "password123"},
    )
    assert resp.status_code == 400
    assert "已存在" in resp.json()["detail"]


@pytest.mark.integration
def test_auth_register_duplicate_email(test_client: TestClient):
    resp = test_client.post(
        "/auth/register",
        json={"username": "user1", "email": "same@test.com", "password": "password123"},
    )
    assert resp.status_code == 201

    resp = test_client.post(
        "/auth/register",
        json={"username": "user2", "email": "same@test.com", "password": "password123"},
    )
    assert resp.status_code == 400
    assert "已被使用" in resp.json()["detail"]


@pytest.mark.integration
def test_files_search_endpoint(test_client: TestClient, test_db):
    file_a = models.File(
        filename="a.txt",
        storage_key="/tmp/a.txt",
        file_hash="a" * 64,
    )
    file_b = models.File(
        filename="b.txt",
        storage_key="/tmp/b.txt",
        file_hash="b" * 64,
    )
    test_db.add_all([file_a, file_b])
    test_db.commit()

    resp = test_client.get("/files/search?q=a")
    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert "total" in payload
    assert len(payload["items"]) >= 1
