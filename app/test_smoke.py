import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.security import create_access_token

# ==================== 身份驗證 Fixtures ====================


@pytest.fixture
def admin_auth_headers(admin_user):
    """為管理員用戶創建認證標頭"""
    token = create_access_token({"sub": admin_user.username, "role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}


# ==================== 身份驗證測試 ====================


def test_register(test_client: TestClient):
    """測試用戶註冊"""
    resp = test_client.post(
        "/auth/register",
        json={
            "username": "testuser1",
            "password": "password123",
            "email": "test1@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser1"
    assert data["role"] == "viewer"


def test_login(test_client: TestClient, test_db: Session):
    """測試用戶登錄"""
    # 先註冊
    from app.security import hash_password

    user = User(username="testuser3", hashed_password=hash_password("password123"))
    test_db.add(user)
    test_db.commit()

    # 登錄
    resp = test_client.post(
        "/auth/login", json={"username": "testuser3", "password": "password123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(test_client: TestClient, test_db: Session):
    """測試錯誤密碼"""
    from app.security import hash_password

    user = User(username="testuser4", hashed_password=hash_password("password123"))
    test_db.add(user)
    test_db.commit()

    resp = test_client.post(
        "/auth/login", json={"username": "testuser4", "password": "wrongpassword"}
    )
    assert resp.status_code == 401


# ==================== 健康檢查測試 ====================


def test_health(test_client: TestClient):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_file_upload_and_dedup(test_client: TestClient, admin_auth_headers):
    # 測試上傳檔案與去重
    content = b"test1234567890"
    files = {"file": ("test.txt", content, "text/plain")}
    resp1 = test_client.post("/files/", files=files, headers=admin_auth_headers)
    assert resp1.status_code in (200, 201)
    file_id = resp1.json()["id"]
    # 再次上傳同檔案應回傳同一筆
    files = {"file": ("test.txt", content, "text/plain")}  # Re-open file
    resp2 = test_client.post("/files/", files=files, headers=admin_auth_headers)
    assert resp2.status_code in (200, 201)
    assert resp2.json()["id"] == file_id


def test_tag_create_and_link(test_client: TestClient, admin_auth_headers):
    # 建立檔案
    content = b"tagtest"
    files = {"file": ("tag.txt", content, "text/plain")}
    resp = test_client.post("/files/", files=files, headers=admin_auth_headers)
    assert resp.status_code == 201
    file_id = resp.json()["id"]
    # 建立標籤
    tag = {"name": "XRD"}
    tag_resp = test_client.post("/tags/", json=tag, headers=admin_auth_headers)
    assert tag_resp.status_code in (200, 201)
    tag_id = tag_resp.json()["id"]
    # 綁定標籤
    link_resp = test_client.post(
        f"/files/{file_id}/tags/{tag_id}", headers=admin_auth_headers
    )
    assert link_resp.status_code == 200
    assert any(t["id"] == tag_id for t in link_resp.json()["tags"])


def test_conclusion_and_annotation(test_client: TestClient, admin_auth_headers):
    # 建立檔案
    content = b"conclusiontest"
    files = {"file": ("con.txt", content, "text/plain")}
    resp = test_client.post("/files/", files=files, headers=admin_auth_headers)
    assert resp.status_code == 201
    file_id = resp.json()["id"]
    # 新增結論
    conclusion = {"content": "這是測試結論"}
    c_resp = test_client.post(
        f"/files/{file_id}/conclusions/", json=conclusion, headers=admin_auth_headers
    )
    assert c_resp.status_code in (200, 201)
    # 新增標註
    annotation = {"data": {"a": 1}, "source": "manual"}
    a_resp = test_client.post(
        f"/files/{file_id}/annotations/", json=annotation, headers=admin_auth_headers
    )
    assert a_resp.status_code in (200, 201)
    # 查詢標註
    get_a = test_client.get(f"/files/{file_id}/annotations/")
    assert get_a.status_code == 200
    assert isinstance(get_a.json(), list)
