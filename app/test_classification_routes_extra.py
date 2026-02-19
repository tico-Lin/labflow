"""Extra tests for classification_routes coverage."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import models, security
from app.main import app


def _override_user(payload):
    app.dependency_overrides[security.get_current_user_optional] = lambda: payload


def _clear_override():
    app.dependency_overrides.pop(security.get_current_user_optional, None)


def _mock_result():
    return SimpleNamespace(
        file_type="XRD",
        confidence=0.9,
        suggested_tags=["Tag1"],
        metadata={"key": "value"},
        source="auto",
    )


@pytest.mark.integration
def test_batch_classify_offline_forbidden(test_client: TestClient):
    _override_user({"id": 0, "role": "offline", "is_offline": True})
    try:
        resp = test_client.post("/files/classify", json={"file_ids": [1]})
        assert resp.status_code == 403
    finally:
        _clear_override()


@pytest.mark.integration
def test_batch_classify_role_forbidden(test_client: TestClient):
    _override_user({"id": 1, "role": "viewer", "is_offline": False})
    try:
        resp = test_client.post("/files/classify", json={"file_ids": [1]})
        assert resp.status_code == 403
    finally:
        _clear_override()


@pytest.mark.integration
def test_batch_classify_success_with_tag_create(
    test_client: TestClient, test_db, monkeypatch
):
    _override_user({"id": 1, "role": "admin", "is_offline": False})
    try:
        file_record = models.File(
            filename="sample.xye",
            storage_key="/tmp/sample.xye",
            file_hash="a" * 64,
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)

        monkeypatch.setattr(
            "app.api.classification_routes.classification_service.classify_file",
            lambda filename: _mock_result(),
        )

        resp = test_client.post(
            "/files/classify",
            json={
                "file_ids": [file_record.id],
                "auto_tag": True,
                "auto_create_tags": True,
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["successful"] == 1
        assert payload["failed"] == 0
        assert payload["results"][0]["tags_created"] == ["Tag1"]
        assert payload["results"][0]["tags_added"] == ["Tag1"]
    finally:
        _clear_override()


@pytest.mark.integration
def test_batch_classify_missing_file(test_client: TestClient):
    _override_user({"id": 1, "role": "admin", "is_offline": False})
    try:
        resp = test_client.post(
            "/files/classify", json={"file_ids": [999], "auto_tag": False}
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["successful"] == 0
        assert payload["failed"] == 1
        assert payload["errors"][0]["file_id"] == 999
    finally:
        _clear_override()


@pytest.mark.integration
def test_auto_classify_file_tagging_paths(
    test_client: TestClient, test_db, monkeypatch
):
    _override_user({"id": 1, "role": "admin", "is_offline": False})
    try:
        file_record = models.File(
            filename="sample.xye",
            storage_key="/tmp/sample.xye",
            file_hash="b" * 64,
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)

        monkeypatch.setattr(
            "app.api.classification_routes.classification_service.classify_file",
            lambda filename: _mock_result(),
        )

        resp = test_client.post(
            f"/files/{file_record.id}/auto-classify",
            params={"auto_tag": False},
        )
        assert resp.status_code == 200
        assert resp.json()["tags_created"] == []

        resp = test_client.post(
            f"/files/{file_record.id}/auto-classify",
            params={"auto_tag": True, "auto_create_tags": False},
        )
        assert resp.status_code == 200
        assert resp.json()["tags_created"] == []
        assert resp.json()["tags_added"] == []
    finally:
        _clear_override()


@pytest.mark.integration
def test_auto_classify_file_missing(test_client: TestClient):
    _override_user({"id": 1, "role": "admin", "is_offline": False})
    try:
        resp = test_client.post("/files/999/auto-classify")
        assert resp.status_code == 404
    finally:
        _clear_override()


@pytest.mark.integration
def test_get_file_classification_and_stats(test_client: TestClient, test_db):
    _override_user({"id": 1, "role": "admin", "is_offline": False})
    try:
        file_a = models.File(
            filename="a.txt",
            storage_key="/tmp/a.txt",
            file_hash="c" * 64,
        )
        file_b = models.File(
            filename="b.txt",
            storage_key="/tmp/b.txt",
            file_hash="d" * 64,
        )
        test_db.add_all([file_a, file_b])
        test_db.commit()
        test_db.refresh(file_a)
        test_db.refresh(file_b)

        empty = test_client.get(f"/files/{file_a.id}/classification")
        assert empty.status_code == 200
        assert empty.json() is None

        annotation_a1 = models.Annotation(
            file_id=file_a.id,
            data={"classification": {"file_type": "XRD", "confidence": 0.7}},
            source="auto",
        )
        annotation_a2 = models.Annotation(
            file_id=file_a.id,
            data={"classification": {"file_type": "Unknown", "confidence": 0.2}},
            source="auto",
        )
        annotation_b = models.Annotation(
            file_id=file_b.id,
            data={"classification": {"file_type": "CSV", "confidence": 0.9}},
            source="auto",
        )
        test_db.add_all([annotation_a1, annotation_a2, annotation_b])
        test_db.commit()

        latest = test_client.get(f"/files/{file_a.id}/classification")
        assert latest.status_code == 200
        assert latest.json()["file_type"] == "Unknown"

        stats = test_client.get("/files/classifications/stats")
        assert stats.status_code == 200
        payload = stats.json()
        assert payload["total"] == 2
        assert payload["by_type"]["Unknown"] == 1
        assert payload["by_type"]["CSV"] == 1
    finally:
        _clear_override()


@pytest.mark.integration
def test_supported_file_types(test_client: TestClient):
    resp = test_client.get("/files/supported-types")
    assert resp.status_code == 200
    assert "XRD" in resp.json()
