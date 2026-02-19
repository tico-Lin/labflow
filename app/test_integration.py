"""
集成測試 - API 端點

【覆蓋範圍】
- 檔案上傳和管理
- 批量操作 API
- 標籤系統
- 認證端點
- 查詢優化

【執行】
pytest app/test_integration.py -v
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.models import File, Tag, User

# ============================================================================
# 測試資料庫和客戶端配置
# ============================================================================

# NOTE: The test_db and test_client fixtures are now sourced from conftest.py
# to ensure a consistent, correctly configured testing environment.


@pytest.fixture
def auth_headers(test_client, admin_user):
    """獲得認證 token"""
    response = test_client.post(
        "/auth/login", json={"username": admin_user.username, "password": "admin123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 認證端點測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.auth
class TestAuthEndpoints:
    """認證端點測試"""

    def test_register(self, test_client):
        """測試用戶註冊"""
        response = test_client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@test.local",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["role"] == "viewer"

    def test_register_duplicate_username(self, test_client):
        """測試重複用戶名"""
        # 第一次註冊
        test_client.post(
            "/auth/register",
            json={"username": "testuser", "email": "test@local", "password": "pwd123"},
        )

        # 第二次註冊相同用戶名
        response = test_client.post(
            "/auth/register",
            json={"username": "testuser", "email": "other@local", "password": "pwd456"},
        )
        assert response.status_code == 400

    def test_login(self, test_client, admin_user):
        """測試用戶登錄"""
        response = test_client.post(
            "/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, test_client):
        """測試無效密碼登錄"""
        response = test_client.post(
            "/auth/login", json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_get_current_user(self, test_client: TestClient, admin_user: User):
        """測試取得當前用戶 - 手動建立 token"""
        login = test_client.post(
            "/auth/login",
            json={"username": admin_user.username, "password": "admin123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        # 2. 使用 token 請求 /users/me
        headers = {"Authorization": f"Bearer {token}"}
        response = test_client.get("/users/me", headers=headers)

        # 3. 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == admin_user.username
        assert data["role"] == admin_user.role


# ============================================================================
# 檔案管理測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.file
class TestFileManagement:
    """檔案管理測試"""

    def test_upload_file(self, test_client, auth_headers, test_db):
        """測試檔案上傳"""
        file_content = b"Test file content"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = test_client.post("/files/", files=files, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.txt"
        assert "file_hash" in data

    def test_list_files(self, test_client):
        """測試列出檔案"""
        response = test_client.get("/files/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_file_details(self, test_client, test_db):
        """測試取得檔案詳情"""
        # 建立測試檔案
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        test_db.add(file)
        test_db.commit()

        response = test_client.get(f"/files/{file.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"

    def test_delete_file(self, test_client, auth_headers, test_db):
        """測試刪除檔案"""
        # 建立測試檔案
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        test_db.add(file)
        test_db.commit()
        file_id = file.id

        response = test_client.delete(f"/files/{file_id}", headers=auth_headers)
        assert response.status_code == 204

        # 驗證檔案已刪除
        check = test_client.get(f"/files/{file_id}")
        assert check.status_code == 404


# ============================================================================
# 標籤管理測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.tag
class TestTagManagement:
    """標籤管理測試"""

    def test_create_tag(self, test_client, auth_headers):
        """測試建立標籤"""
        response = test_client.post(
            "/tags/", json={"name": "XRD"}, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "XRD"

    def test_list_tags(self, test_client):
        """測試列出標籤"""
        response = test_client.get("/tags/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_tag_to_file(self, test_client, auth_headers, test_db):
        """測試為檔案添加標籤"""
        # 建立測試檔案和標籤
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        tag = Tag(name="XRD")
        test_db.add(file)
        test_db.add(tag)
        test_db.commit()

        response = test_client.post(
            f"/files/{file.id}/tags", json={"tag_id": tag.id}, headers=auth_headers
        )
        assert response.status_code == 200


# ============================================================================
# 批量操作測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.batch
class TestBatchOperations:
    """批量操作測試"""

    def test_batch_create_tags(self, test_client, auth_headers):
        """測試批量建立標籤"""
        response = test_client.post(
            "/tags/batch-create", json=["XRD", "SEM", "TEM"], headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] == 3
        assert len(data["created_tags"]) == 3

    def test_batch_create_tags_with_duplicates(
        self, test_client, auth_headers, test_db
    ):
        """測試批量建立標籤（包含重複）"""
        # 先建立一個標籤
        tag = Tag(name="XRD")
        test_db.add(tag)
        test_db.commit()

        # 批量建立，其中一個已存在
        response = test_client.post(
            "/tags/batch-create", json=["XRD", "SEM"], headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] == 1
        assert data["existing_count"] == 1

    def test_batch_delete_files(self, test_client, auth_headers, test_db):
        """測試批量刪除檔案"""
        # 建立測試檔案
        file1 = File(
            filename="test1.txt", storage_key="/test/path1", file_hash="a" * 64
        )
        file2 = File(
            filename="test2.txt", storage_key="/test/path2", file_hash="b" * 64
        )
        test_db.add(file1)
        test_db.add(file2)
        test_db.commit()

        response = test_client.post(
            "/files/batch-delete", json=[file1.id, file2.id], headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2


# ============================================================================
# 搜尋和過濾測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.search
class TestSearch:
    """搜尋和過濾測試"""

    def test_search_by_filename(self, test_client, test_db):
        """測試按檔名搜尋"""
        # 建立測試檔案
        file1 = File(
            filename="report_2024.txt", storage_key="/test/path1", file_hash="a" * 64
        )
        file2 = File(
            filename="data_analysis.xlsx", storage_key="/test/path2", file_hash="b" * 64
        )
        test_db.add_all([file1, file2])
        test_db.commit()

        response = test_client.get("/files/search?q=report")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "report_2024.txt"

    def test_search_by_tag(self, test_client, test_db):
        """測試按標籤搜尋"""
        # 建立檔案和標籤
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        tag = Tag(name="XRD")
        file.tags.append(tag)
        test_db.add(file)
        test_db.commit()

        response = test_client.get(f"/files/search?tag_id={tag.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


# ============================================================================
# 結論和標註測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.conclusion
class TestConclusionsAndAnnotations:
    """結論和標註測試"""

    def test_add_conclusion(self, test_client, auth_headers, test_db):
        """測試新增結論"""
        # 建立測試檔案
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        test_db.add(file)
        test_db.commit()

        response = test_client.post(
            f"/files/{file.id}/conclusions/",
            json={"content": "Test conclusion"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["content"] == "Test conclusion"

    def test_get_conclusions(self, test_client, test_db):
        """測試取得結論"""
        # 建立測試檔案和結論
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        test_db.add(file)
        test_db.commit()

        response = test_client.get(f"/files/{file.id}/conclusions/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_annotation(self, test_client, auth_headers, test_db):
        """測試新增標註"""
        # 建立測試檔案
        file = File(filename="test.txt", storage_key="/test/path", file_hash="a" * 64)
        test_db.add(file)
        test_db.commit()

        response = test_client.post(
            f"/files/{file.id}/annotations/",
            json={"data": {"cr_content": 3.5, "structure": "beta"}, "source": "manual"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["data"]["cr_content"] == 3.5


# ============================================================================
# 健康檢查測試
# ============================================================================


@pytest.mark.integration
@pytest.mark.health
class TestHealthCheck:
    """健康檢查測試"""

    def test_root_endpoint(self, test_client):
        """測試根端點"""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_health_endpoint(self, test_client):
        """測試健康檢查端點"""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
