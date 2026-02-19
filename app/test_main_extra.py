"""
Additional endpoint tests to increase main.py coverage.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app import models, security
from app.main import app


def make_auth_header(user_id: int, role: str = "admin", username: str = "user") -> dict:
    token = security.create_access_token(
        {"sub": user_id, "username": username, "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_refresh_token_flow(test_client: TestClient, test_db, monkeypatch):
    user = models.User(
        username="refresh_user",
        email="refresh@example.com",
        hashed_password=security.hash_password("password123"),
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    resp = test_client.post(
        "/auth/login", json={"username": "refresh_user", "password": "password123"}
    )
    assert resp.status_code == 200
    refresh_token = resp.json()["refresh_token"]

    monkeypatch.setattr(security, "verify_token", lambda token: {"sub": user.id})
    refresh = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 200
    payload = refresh.json()
    assert "access_token" in payload
    assert "refresh_token" in payload


@pytest.mark.integration
def test_refresh_token_invalid(test_client: TestClient, monkeypatch):
    monkeypatch.setattr(
        security,
        "verify_token",
        lambda token: (_ for _ in ()).throw(security.JWTError("bad")),
    )
    resp = test_client.post("/auth/refresh", json={"refresh_token": "bad"})
    assert resp.status_code == 401


@pytest.mark.integration
def test_list_users_admin(test_client: TestClient, test_db, monkeypatch):
    admin = models.User(
        username="admin_user",
        email="admin_user@example.com",
        hashed_password=security.hash_password("admin123"),
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)

    monkeypatch.setattr(
        security,
        "get_current_user",
        lambda authorization=None: {"id": admin.id, "role": "admin"},
    )
    headers = make_auth_header(admin.id, role="admin", username=admin.username)
    resp = test_client.get("/users/", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.integration
def test_update_user_self_and_forbidden(test_client: TestClient, test_db, monkeypatch):
    user1 = models.User(
        username="user_one",
        email="user1@example.com",
        hashed_password=security.hash_password("pass1"),
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    user2 = models.User(
        username="user_two",
        email="user2@example.com",
        hashed_password=security.hash_password("pass2"),
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    test_db.add_all([user1, user2])
    test_db.commit()
    test_db.refresh(user1)
    test_db.refresh(user2)

    monkeypatch.setattr(
        security,
        "get_current_user",
        lambda authorization=None: {"id": user1.id, "role": "viewer"},
    )
    headers = make_auth_header(user1.id, role="viewer", username=user1.username)
    resp = test_client.put(
        f"/users/{user1.id}", headers=headers, json={"email": "new@example.com"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@example.com"

    forbidden = test_client.put(
        f"/users/{user2.id}",
        headers=headers,
        json={"email": "other@example.com"},
    )
    assert forbidden.status_code == 403


@pytest.mark.integration
def test_delete_user_admin(test_client: TestClient, test_db, monkeypatch):
    admin = models.User(
        username="delete_admin",
        email="delete_admin@example.com",
        hashed_password=security.hash_password("admin123"),
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    user = models.User(
        username="delete_user",
        email="delete_user@example.com",
        hashed_password=security.hash_password("user123"),
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    test_db.add_all([admin, user])
    test_db.commit()
    test_db.refresh(admin)
    test_db.refresh(user)

    monkeypatch.setattr(
        security,
        "get_current_user",
        lambda authorization=None: {"id": admin.id, "role": "admin"},
    )
    headers = make_auth_header(admin.id, role="admin", username=admin.username)
    resp = test_client.delete(f"/users/{user.id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.integration
def test_update_and_delete_user_not_found(
    test_client: TestClient, test_db, monkeypatch
):
    admin = models.User(
        username="admin_missing",
        email="admin_missing@example.com",
        hashed_password=security.hash_password("admin123"),
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)

    monkeypatch.setattr(
        security,
        "get_current_user",
        lambda authorization=None: {"id": admin.id, "role": "admin"},
    )
    headers = make_auth_header(admin.id, role="admin", username=admin.username)

    update = test_client.put(
        "/users/9999", headers=headers, json={"email": "none@example.com"}
    )
    assert update.status_code == 404

    delete = test_client.delete("/users/9999", headers=headers)
    assert delete.status_code == 404


@pytest.mark.integration
def test_download_and_remove_tag_and_conclusion(
    test_client: TestClient, test_db, monkeypatch
):
    # 創建管理員用戶和認證 headers
    admin = models.User(
        username="test_admin",
        email="admin@test.com",
        hashed_password=security.hash_password("admin123"),
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)

    # Override dependency to bypass auth token validation for this test.
    app.dependency_overrides[security.get_current_user_optional] = (
        lambda authorization=None: {
            "id": admin.id,
            "role": "admin",
            "username": admin.username,
            "is_offline": False,
        }
    )

    auth_headers = make_auth_header(admin.id, role="admin", username=admin.username)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "file.bin")
            with open(file_path, "wb") as handle:
                handle.write(b"data")

            file_record = models.File(
                filename="file.bin",
                storage_key=file_path,
                file_hash="a" * 64,
            )
            tag = models.Tag(name="TagA")
            file_record.tags.append(tag)
            test_db.add(file_record)
            test_db.commit()
            test_db.refresh(file_record)
            test_db.refresh(tag)

            download = test_client.get(
                f"/files/{file_record.id}/download", headers=auth_headers
            )
            assert download.status_code == 200

            remove = test_client.delete(
                f"/files/{file_record.id}/tags/{tag.id}", headers=auth_headers
            )
            assert remove.status_code == 204

            conclusion = models.Conclusion(file_id=file_record.id, content="old")
            test_db.add(conclusion)
            test_db.commit()
            test_db.refresh(conclusion)

            updated = test_client.put(
                f"/conclusions/{conclusion.id}",
                json={"content": "new"},
                headers=auth_headers,
            )
            assert updated.status_code == 200
            assert updated.json()["content"] == "new"

            deleted = test_client.delete(
                f"/conclusions/{conclusion.id}", headers=auth_headers
            )
            assert deleted.status_code == 204
    finally:
        app.dependency_overrides.pop(security.get_current_user_optional, None)


@pytest.mark.integration
def test_download_and_remove_tag_missing(test_client: TestClient, test_db):
    app.dependency_overrides[security.get_current_user_optional] = lambda: {
        "id": 1,
        "role": "admin",
        "username": "admin",
        "is_offline": False,
    }
    missing_file = models.File(
        filename="missing.bin",
        storage_key="missing/path",
        file_hash="b" * 64,
    )
    try:
        test_db.add(missing_file)
        test_db.commit()
        test_db.refresh(missing_file)

        download = test_client.get(f"/files/{missing_file.id}/download")
        assert download.status_code == 404

        remove = test_client.delete(f"/files/{missing_file.id}/tags/999")
        assert remove.status_code == 404
    finally:
        app.dependency_overrides.pop(security.get_current_user_optional, None)


@pytest.mark.integration
def test_update_delete_conclusion_errors(test_client: TestClient, test_db):
    app.dependency_overrides[security.get_current_user_optional] = lambda: {
        "id": 1,
        "role": "admin",
        "username": "admin",
        "is_offline": False,
    }
    try:
        update = test_client.put("/conclusions/9999", json={"content": "x"})
        assert update.status_code == 404

        delete = test_client.delete("/conclusions/9999")
        assert delete.status_code == 404

        file_record = models.File(
            filename="c.bin",
            storage_key="path",
            file_hash="c" * 64,
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)

        conclusion = models.Conclusion(file_id=file_record.id, content="valid")
        test_db.add(conclusion)
        test_db.commit()
        test_db.refresh(conclusion)

        bad = test_client.put(f"/conclusions/{conclusion.id}", json={"content": "   "})
        assert bad.status_code == 400
    finally:
        app.dependency_overrides.pop(security.get_current_user_optional, None)


@pytest.mark.integration
def test_batch_upload_files(test_client: TestClient):
    files = [
        ("files", ("a.txt", b"hello", "text/plain")),
        ("files", ("b.txt", b"hello", "text/plain")),
    ]
    resp = test_client.post("/files/batch-upload", files=files)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["uploaded_count"] == 1
    assert payload["duplicated_count"] == 1


@pytest.mark.integration
def test_reasoning_chain_endpoints(test_client: TestClient, test_db, monkeypatch):
    user = models.User(
        username="reasoning_api_user",
        email="reasoning_api_user@example.com",
        hashed_password=security.hash_password("pass"),
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    app.dependency_overrides[security.get_current_user_optional] = lambda: {
        "id": user.id,
        "role": "admin",
        "username": user.username,
        "is_offline": False,
    }
    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": user.id,
        "role": "admin",
        "username": user.username,
        "is_offline": False,
    }
    headers = make_auth_header(user.id, role="admin", username=user.username)
    nodes = [
        {
            "node_id": "n1",
            "node_type": "data_input",
            "config": {"source": "constant", "value": 1},
        },
        {
            "node_id": "n2",
            "node_type": "output",
            "inputs": ["n1"],
            "config": {"format": "raw"},
        },
    ]
    try:
        created = test_client.post(
            "/reasoning/chains",
            headers=headers,
            json={"name": "Chain1", "description": "d", "nodes": nodes},
        )
        assert created.status_code == 201
        chain_id = created.json()["id"]

        listed = test_client.get("/reasoning/chains", headers=headers)
        assert listed.status_code == 200

        detail = test_client.get(f"/reasoning/chains/{chain_id}", headers=headers)
        assert detail.status_code == 200

        updated = test_client.put(
            f"/reasoning/chains/{chain_id}",
            headers=headers,
            json={"name": "Chain1-updated"},
        )
        assert updated.status_code == 200

        executed = test_client.post(
            f"/reasoning/chains/{chain_id}/execute",
            headers=headers,
            json={"input_data": {}},
        )
        assert executed.status_code == 200
        execution_id = executed.json()["execution_id"]

        execution_detail = test_client.get(
            f"/reasoning/executions/{execution_id}", headers=headers
        )
        assert execution_detail.status_code == 200

        deleted = test_client.delete(f"/reasoning/chains/{chain_id}", headers=headers)
        assert deleted.status_code == 204
    finally:
        app.dependency_overrides.pop(security.get_current_user_optional, None)
        app.dependency_overrides.pop(security.get_current_user, None)


@pytest.mark.integration
def test_script_endpoints(test_client: TestClient, test_db, monkeypatch):
    user = models.User(
        username="script_api_user",
        email="script_api_user@example.com",
        hashed_password=security.hash_password("pass"),
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    app.dependency_overrides[security.get_current_user] = lambda: {
        "id": user.id,
        "role": "admin",
    }
    headers = make_auth_header(user.id, role="admin", username=user.username)
    created = test_client.post(
        "/scripts",
        headers=headers,
        json={"name": "script1", "content": "print('hi')", "parameters": {}},
    )
    assert created.status_code == 201
    script_id = created.json()["id"]

    listed = test_client.get("/scripts", headers=headers)
    assert listed.status_code == 200

    detail = test_client.get(f"/scripts/{script_id}", headers=headers)
    assert detail.status_code == 200

    updated = test_client.put(
        f"/scripts/{script_id}",
        headers=headers,
        json={"name": "script1-updated", "content": "print('updated')"},
    )
    assert updated.status_code == 200

    executed = test_client.post(
        f"/scripts/{script_id}/execute",
        headers=headers,
        json={"input": "value"},
    )
    assert executed.status_code == 200

    deleted = test_client.delete(f"/scripts/{script_id}", headers=headers)
    assert deleted.status_code == 204
    app.dependency_overrides.pop(security.get_current_user, None)
