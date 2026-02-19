"""
Error-path tests for main.py endpoints.
"""

import os
import tempfile
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.main as main
from app import models, security
from app.main import app


def make_auth_header(
    user_id: int, role: str = "viewer", username: str = "user"
) -> dict:
    token = security.create_access_token(
        {"sub": str(user_id), "username": username, "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user):
    """為管理員用戶創建認證標頭"""
    return make_auth_header(admin_user.id, role="admin", username=admin_user.username)


@pytest.mark.integration
def test_register_duplicate_email(test_client: TestClient, test_db):
    user = models.User(
        username="dup_email",
        email="dup@example.com",
        hashed_password=security.hash_password("password123"),
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()

    resp = test_client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "password": "password123",
            "email": "dup@example.com",
        },
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_custom_openapi_cached():
    schema_first = app.openapi()
    schema_second = app.openapi()
    assert schema_first is schema_second


@pytest.mark.integration
def test_login_inactive_user(test_client: TestClient, test_db):
    user = models.User(
        username="inactive",
        email="inactive@example.com",
        hashed_password=security.hash_password("password123"),
        role=models.RoleEnum.VIEWER,
        is_active=0,
    )
    test_db.add(user)
    test_db.commit()

    resp = test_client.post(
        "/auth/login", json={"username": "inactive", "password": "password123"}
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_refresh_token_inactive_user(test_client: TestClient, test_db):
    user = models.User(
        username="inactive_refresh",
        email="inactive_refresh@example.com",
        hashed_password=security.hash_password("password123"),
        role=models.RoleEnum.VIEWER,
        is_active=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    refresh_token = security.create_refresh_token(
        {"sub": str(user.id), "username": user.username}
    )
    resp = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


@pytest.mark.integration
def test_analysis_run_error_paths(test_client: TestClient, monkeypatch):
    def raise_known(*args, **kwargs):
        raise main.AnalysisServiceError("bad tool")

    monkeypatch.setattr(main.AnalysisService, "run_tool", raise_known)
    resp = test_client.post("/analysis/run", json={"tool_id": "x", "file_id": 1})
    assert resp.status_code == 400

    def raise_unknown(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main.AnalysisService, "run_tool", raise_unknown)
    resp = test_client.post("/analysis/run", json={"tool_id": "x", "file_id": 1})
    assert resp.status_code == 500


@pytest.mark.integration
def test_users_me_not_found(test_client: TestClient):
    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": 999,
        "role": "viewer",
    }
    resp = test_client.get("/users/me")
    assert resp.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_search_files_with_tag_filter(test_client: TestClient, test_db):
    file_record = models.File(
        filename="search.bin", storage_key="/tmp/s", file_hash="1" * 64
    )
    tag = models.Tag(name="search_tag")
    file_record.tags.append(tag)
    test_db.add(file_record)
    test_db.commit()

    resp = test_client.get(f"/files/search?tag_id={tag.id}")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.integration
def test_get_file_not_found(test_client: TestClient):
    resp = test_client.get("/files/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_file_empty_filename(test_db):
    class DummyFile:
        filename = ""

        async def seek(self, *args, **kwargs):
            return 0

        async def tell(self):
            return 0

    with pytest.raises(HTTPException) as exc:
        await main.upload_file(
            file=DummyFile(),
            db=test_db,
            current_user={"id": 1, "username": "test", "role": "viewer"},
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_too_large(test_db, monkeypatch):
    class DummyFile:
        filename = "big.bin"

        async def seek(self, *args, **kwargs):
            return 0

        async def tell(self):
            return 2

        async def read(self, size=-1):
            return b""

    async def fake_hash(file):
        return "f" * 64

    monkeypatch.setattr(main, "MAX_UPLOAD_SIZE", 1)
    monkeypatch.setattr(main, "calculate_file_hash", fake_hash)

    with pytest.raises(HTTPException) as exc:
        await main.upload_file(
            file=DummyFile(),
            db=test_db,
            current_user={"id": 1, "username": "test", "role": "viewer"},
        )
    assert exc.value.status_code == 413


@pytest.mark.integration
def test_delete_file_storage_delete_error(
    test_client: TestClient, test_db, monkeypatch, admin_auth_headers
):
    file_record = models.File(
        filename="delete.bin", storage_key="/tmp/missing", file_hash="d" * 64
    )
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    monkeypatch.setattr(
        main.storage, "delete", lambda key: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    resp = test_client.delete(f"/files/{file_record.id}", headers=admin_auth_headers)
    assert resp.status_code == 204


@pytest.mark.integration
def test_create_tag_existing(test_client: TestClient, test_db, admin_auth_headers):
    tag = models.Tag(name="existing_tag")
    test_db.add(tag)
    test_db.commit()

    resp = test_client.post(
        "/tags/", json={"name": "existing_tag"}, headers=admin_auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == tag.id


@pytest.mark.integration
def test_add_tag_body_missing_tag_id(
    test_client: TestClient, test_db, admin_auth_headers
):
    file_record = models.File(
        filename="tag.bin", storage_key="/tmp/t", file_hash="e" * 64
    )
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    resp = test_client.post(
        f"/files/{file_record.id}/tags", json={}, headers=admin_auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_add_tag_duplicate_and_remove_missing(
    test_client: TestClient, test_db, admin_auth_headers
):
    file_record = models.File(
        filename="tag2.bin", storage_key="/tmp/t2", file_hash="f" * 64
    )
    tag = models.Tag(name="t1")
    test_db.add_all([file_record, tag])
    test_db.commit()
    test_db.refresh(file_record)
    test_db.refresh(tag)

    first = test_client.post(
        f"/files/{file_record.id}/tags/{tag.id}", headers=admin_auth_headers
    )
    assert first.status_code == 200

    second = test_client.post(
        f"/files/{file_record.id}/tags/{tag.id}", headers=admin_auth_headers
    )
    assert second.status_code == 200

    other_tag = models.Tag(name="t2")
    test_db.add(other_tag)
    test_db.commit()
    test_db.refresh(other_tag)

    remove = test_client.delete(
        f"/files/{file_record.id}/tags/{other_tag.id}", headers=admin_auth_headers
    )
    assert remove.status_code == 204


@pytest.mark.integration
def test_add_tag_file_or_tag_missing(
    test_client: TestClient, test_db, admin_auth_headers
):
    file_record = models.File(
        filename="tag3.bin", storage_key="/tmp/t3", file_hash="2" * 64
    )
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    missing_file = test_client.post("/files/9999/tags/1", headers=admin_auth_headers)
    assert missing_file.status_code == 404

    missing_tag = test_client.post(
        f"/files/{file_record.id}/tags/9999", headers=admin_auth_headers
    )
    assert missing_tag.status_code == 404


@pytest.mark.integration
def test_create_conclusion_errors(test_client: TestClient, test_db):
    file_record = models.File(
        filename="c1.bin", storage_key="/tmp/c1", file_hash="a" * 64
    )
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    empty = test_client.post(
        f"/files/{file_record.id}/conclusions/", json={"content": " "}
    )
    assert empty.status_code == 400

    missing = test_client.post("/files/9999/conclusions/", json={"content": "ok"})
    assert missing.status_code == 404


@pytest.mark.integration
def test_conclusions_list_and_update(
    test_client: TestClient, test_db, admin_auth_headers
):
    file_record = models.File(
        filename="c2.bin", storage_key="/tmp/c2", file_hash="e" * 64
    )
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    resp = test_client.get(f"/files/{file_record.id}/conclusions/")
    assert resp.status_code == 200
    assert resp.json() == []

    conclusion = models.Conclusion(file_id=file_record.id, content="initial")
    test_db.add(conclusion)
    test_db.commit()
    test_db.refresh(conclusion)

    update = test_client.put(
        f"/conclusions/{conclusion.id}",
        json={"content": "updated"},
        headers=admin_auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["content"] == "updated"


@pytest.mark.integration
def test_annotation_errors(test_client: TestClient, test_db, monkeypatch):
    file_record = models.File(
        filename="a1.bin", storage_key="/tmp/a1", file_hash="b" * 64
    )
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    missing = test_client.post(
        "/files/9999/annotations/", json={"data": {"x": 1}, "source": "manual"}
    )
    assert missing.status_code == 404

    empty = test_client.post(
        f"/files/{file_record.id}/annotations/", json={"data": {}, "source": "manual"}
    )
    assert empty.status_code == 400

    monkeypatch.setattr(
        main.annotation_provider,
        "add_annotation",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    error = test_client.post(
        f"/files/{file_record.id}/annotations/",
        json={"data": {"x": 1}, "source": "manual"},
    )
    assert error.status_code == 500


@pytest.mark.integration
def test_get_annotations_missing_file(test_client: TestClient):
    resp = test_client.get("/files/9999/annotations/")
    assert resp.status_code == 404


@pytest.mark.integration
def test_request_observability_exception_path(test_client: TestClient):
    from fastapi import APIRouter
    from fastapi.testclient import TestClient as LocalClient

    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("boom")

    app.include_router(router)
    client = LocalClient(app, raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500


@pytest.mark.integration
def test_sync_files_error_path(test_client: TestClient, test_db, monkeypatch):
    file_record = models.File(
        filename="orphan.bin", storage_key="/tmp/orphan", file_hash="c" * 64
    )
    test_db.add(file_record)
    test_db.commit()

    monkeypatch.setattr(
        main.os.path, "exists", lambda path: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    resp = test_client.post("/admin/sync-files/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


@pytest.mark.integration
def test_file_status_error_path(test_client: TestClient, test_db, monkeypatch):
    file_record = models.File(
        filename="status.bin", storage_key="/tmp/status", file_hash="c" * 64
    )
    test_db.add(file_record)
    test_db.commit()

    monkeypatch.setattr(
        main.os.path, "exists", lambda path: (_ for _ in ()).throw(RuntimeError("fail"))
    )
    resp = test_client.get("/admin/file-status/")
    assert resp.status_code == 200
    assert "error" in resp.json()


@pytest.mark.integration
def test_batch_delete_partial(test_client: TestClient, test_db):
    fd, path = tempfile.mkstemp()
    os.close(fd)

    file_record = models.File(filename="del.bin", storage_key=path, file_hash="d" * 64)
    test_db.add(file_record)
    test_db.commit()
    test_db.refresh(file_record)

    resp = test_client.post("/files/batch-delete", json=[file_record.id, 9999])
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "partial"
    assert 9999 in payload["failed_ids"]


@pytest.mark.integration
def test_batch_delete_error(test_client: TestClient, test_db, monkeypatch):
    def fail_commit():
        raise RuntimeError("fail")

    monkeypatch.setattr(test_db, "commit", fail_commit)
    resp = test_client.post("/files/batch-delete", json=[9999])
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


@pytest.mark.integration
def test_batch_create_tags_error(test_client: TestClient, test_db, monkeypatch):
    def fail_commit():
        raise RuntimeError("db down")

    monkeypatch.setattr(test_db, "commit", fail_commit)
    resp = test_client.post("/tags/batch-create", json=["dup", "dup2"])
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["status"] == "error"


@pytest.mark.integration
def test_batch_upload_storage_error(test_client: TestClient, monkeypatch):
    async def fail_save(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(main.storage, "save", fail_save)
    resp = test_client.post(
        "/files/batch-upload",
        files=[("files", ("a.bin", b"data", "application/octet-stream"))],
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["uploaded_count"] == 0


@pytest.mark.integration
def test_batch_upload_outer_error(test_client: TestClient, test_db, monkeypatch):
    def fail_commit():
        raise RuntimeError("fail")

    monkeypatch.setattr(test_db, "commit", fail_commit)
    resp = test_client.post(
        "/files/batch-upload",
        files=[("files", ("a.bin", b"data", "application/octet-stream"))],
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "error"


@pytest.mark.integration
def test_reasoning_chain_invalid_uuid(test_client: TestClient):
    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": 1,
        "role": "viewer",
    }
    resp = test_client.get("/reasoning/chains/not-a-uuid")
    assert resp.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_execution_result_normalization(test_client: TestClient, test_db):
    user = models.User(
        username="exec_user",
        email="exec_user@example.com",
        hashed_password=security.hash_password("password123"),
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    chain = models.ReasoningChain(
        id=uuid4(),
        name="chain",
        description="",
        nodes=[
            {
                "node_id": "n1",
                "node_type": "data_input",
                "config": {"source": "constant", "value": 1},
            }
        ],
        is_template=False,
        created_by_id=user.id,
    )
    test_db.add(chain)
    test_db.commit()
    test_db.refresh(chain)

    execution = models.ReasoningExecution(
        id=uuid4(),
        chain_id=chain.id,
        status="completed",
        user_id=user.id,
        input_data="not json",
        results='{"x": 1}',
        error_log='{"err": "x"}',
    )
    test_db.add(execution)
    test_db.commit()
    test_db.refresh(execution)

    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": user.id,
        "role": "viewer",
    }
    resp = test_client.get(f"/reasoning/executions/{execution.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["results"] == {"x": 1}
    assert payload["input_data"] == {}
    assert payload["error"] == {"err": "x"}
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_execution_result_not_found(test_client: TestClient):
    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": 1,
        "role": "viewer",
    }
    resp = test_client.get("/reasoning/executions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_script_endpoints_not_found(test_client: TestClient):
    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": 1,
        "role": "viewer",
    }
    missing = test_client.get("/scripts/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404

    bad = test_client.post("/scripts/not-a-uuid/execute", json={"x": 1})
    assert bad.status_code == 400
    app.dependency_overrides.clear()
