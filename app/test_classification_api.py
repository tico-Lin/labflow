"""
檔案分類 API 測試

測試檔案分類服務 API 端點:
- POST /files/classify - 分類檔案
- POST /files/{file_id}/auto-classify - 自動分類檔案
- GET /files/{file_id}/classification - 查詢分類結果
- GET /files/classifications/stats - 查詢統計
- GET /files/supported-types - 查詢支持的類型

作者: GitHub Copilot
建檔時間: 2025-02-17
"""

import hashlib
import pytest
from app.models import File, User, Tag, Annotation
from app.security import create_access_token


def simple_hash_password(password: str) -> str:
    """簡單的密碼雜湊函數（測試用）"""
    return hashlib.sha256(password.encode()).hexdigest()


class TestClassificationAPI:
    """檔案分類 API 的集成測試"""

    @pytest.fixture(scope="function", autouse=True)
    def setup_users(self, test_db, mock_password_hashing):
        """為每個測試設置使用者"""
        # 創建測試使用者
        admin = User(
            username="admin",
            email="admin@test.com",
            hashed_password=simple_hash_password("admin123"),
            role="admin",
        )
        editor = User(
            username="editor",
            email="editor@test.com",
            hashed_password=simple_hash_password("editor123"),
            role="editor",
        )
        viewer = User(
            username="viewer",
            email="viewer@test.com",
            hashed_password=simple_hash_password("viewer123"),
            role="viewer",
        )

        test_db.add_all([admin, editor, viewer])
        test_db.commit()

    @pytest.fixture(scope="function")
    def admin_token(self, test_db):
        """獲取管理員 token"""
        admin = test_db.query(User).filter(User.username == "admin").first()
        return create_access_token({"sub": admin.username, "role": admin.role})

    @pytest.fixture(scope="function")
    def editor_token(self, test_db):
        """獲取編輯者 token"""
        editor = test_db.query(User).filter(User.username == "editor").first()
        return create_access_token({"sub": editor.username, "role": editor.role})

    @pytest.fixture(scope="function")
    def viewer_token(self, test_db):
        """獲取查看者 token"""
        viewer = test_db.query(User).filter(User.username == "viewer").first()
        return create_access_token({"sub": viewer.username, "role": viewer.role})

    @pytest.fixture(scope="function")
    def test_files(self, test_db):
        """創建測試檔案"""
        files = [
            File(
                filename="Cr3_XRD_20250104.xy",
                storage_key="test/Cr3_XRD_20250104.xy",
                file_hash="a" * 64,
            ),
            File(
                filename="Sample_A_SEM_2025-01-15_01.tif",
                storage_key="test/Sample_A_SEM_2025-01-15_01.tif",
                file_hash="b" * 64,
            ),
            File(
                filename="EIS_MnO2_20250110.txt",
                storage_key="test/EIS_MnO2_20250110.txt",
                file_hash="c" * 64,
            ),
        ]
        test_db.add_all(files)
        test_db.commit()

        for file in files:
            test_db.refresh(file)

        return files

    def test_auto_classify_single_file_success(self, test_client, test_db, admin_token, test_files):
        """測試成功的單檔案自動分類"""
        file_id = test_files[0].id
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = test_client.post(
            f"/files/{file_id}/auto-classify",
            headers=headers,
        )

        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert "file_id" in data
        assert data["file_id"] == file_id

    def test_auto_classify_nonexistent_file(self, test_client, admin_token):
        """測試分類不存在的檔案"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = test_client.post(
            "/files/9999/auto-classify",
            headers=headers,
        )
        assert response.status_code == 404

    def test_batch_classify_success(self, test_client, test_db, admin_token, test_files):
        """測試批量分類"""
        file_ids = [f.id for f in test_files]
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = test_client.post(
            "/files/classify",
            json={"file_ids": file_ids},
            headers=headers,
        )

        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        assert "results" in data or "successful" in data

    def test_batch_classify_with_invalid_files(self, test_client, test_db, admin_token, test_files):
        """測試含有無效檔案的批量分類"""
        valid_id = test_files[0].id
        invalid_id = 9999
        file_ids = [valid_id, invalid_id]
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = test_client.post(
            "/files/classify",
            json={"file_ids": file_ids},
            headers=headers,
        )

        assert response.status_code == 200

    def test_get_classification_result(self, test_client, test_db, admin_token, test_files):
        """測試獲取分類結果"""
        file_id = test_files[0].id

        # 先執行分類
        headers = {"Authorization": f"Bearer {admin_token}"}
        test_client.post(f"/files/{file_id}/auto-classify", headers=headers)

        # 然後查詢結果
        response = test_client.get(
            f"/files/{file_id}/classification",
            headers=headers,
        )

        # 即使沒有分類，也應該返回 200 或 404
        assert response.status_code in [200, 404]

    def test_classification_stats(self, test_client, test_db, admin_token):
        """測試分類統計端點"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = test_client.get(
            "/files/classifications/stats",
            headers=headers,
        )

        assert response.status_code == 200

    def test_supported_types(self, test_client, admin_token):
        """測試支持的檔案類型端點"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = test_client.get(
            "/files/supported-types",
            headers=headers,
        )

        assert response.status_code == 200

    def test_auto_classify_viewer_no_permission(self, test_client, test_db, viewer_token, test_files):
        """測試查看者無法執行分類"""
        file_id = test_files[0].id
        headers = {"Authorization": f"Bearer {viewer_token}"}

        response = test_client.post(
            f"/files/{file_id}/auto-classify",
            headers=headers,
        )

        # 查看者應該被拒絕
        assert response.status_code in [403, 401]

    def test_batch_classify_editor_permission(self, test_client, test_db, editor_token, test_files):
        """測試編輯者可以執行批量分類"""
        file_ids = [f.id for f in test_files[:2]]
        headers = {"Authorization": f"Bearer {editor_token}"}

        response = test_client.post(
            "/files/classify",
            json={"file_ids": file_ids},
            headers=headers,
        )

        # 編輯者應該被允許
        assert response.status_code == 200

    def test_auto_classify_without_token(self, test_client, test_db, test_files):
        """測試未認證的請求"""
        file_id = test_files[0].id
        response = test_client.post(f"/files/{file_id}/auto-classify")

        # 無 token 時返回 401 或 403
        assert response.status_code in [401, 403]
