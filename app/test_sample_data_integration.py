"""
使用sample数据的端到端集成测试

这个测试使用sample目录中的真实数据文件测试系统功能。
"""

import hashlib
from pathlib import Path

from app.models import User

# Sample数据目录
SAMPLE_DIR = Path(__file__).parent.parent / "sample"


def simple_hash(password: str) -> str:
    """简单哈希函数用于测试"""
    return hashlib.sha256(password.encode()).hexdigest()


class TestSampleDataIntegration:
    """使用真实sample数据的集成测试"""

    def test_sample_files_exist(self):
        """验证sample目录中的文件存在"""
        assert SAMPLE_DIR.exists(), f"Sample目录不存在: {SAMPLE_DIR}"

        expected_files = [
            "2025-11-28_TPS19A_MYTHEN_20000.instprm",
            "20251203 nmo.txt",
            "bataMnO2.cif",
            "MOCr00012.xye",
            "NMOC5_60s-scan_id-57208-seq_num-0001-_newport_delta-47.10.xye",
            "PDF#44-0141.txt",
        ]

        for filename in expected_files:
            file_path = SAMPLE_DIR / filename
            assert file_path.exists(), f"Sample文件不存在: {filename}"

    def test_upload_sample_xrd_file(self, test_client, test_db):
        """測試上傳XRD樣本文件"""
        from app.security import create_access_token

        # 創建管理員
        admin = User(
            username="xrd_admin",
            email="xrd_admin@test.com",
            hashed_password=simple_hash("admin123"),
            role="admin",
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

        token = create_access_token({"sub": admin.username, "role": admin.role})
        admin_auth_header = {"Authorization": f"Bearer {token}"}

        # 讀取sample中的XRD文件
        xrd_file = SAMPLE_DIR / "MOCr00012.xye"

        assert xrd_file.exists(), f"XRD sample文件不存在: {xrd_file}"

        with open(xrd_file, "rb") as f:
            files = {"file": ("MOCr00012.xye", f, "text/plain")}
            response = test_client.post(
                "/files/", files=files, headers=admin_auth_header
            )

        assert response.status_code in [200, 201], f"Upload failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["filename"] == "MOCr00012.xye"

        return data["id"]

    def test_upload_sample_cif_file(self, test_client, test_db):
        """測試上傳CIF結構文件"""
        from app.security import create_access_token

        # 創建管理員
        admin = User(
            username="cif_admin",
            email="cif_admin@test.com",
            hashed_password=simple_hash("admin123"),
            role="admin",
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

        token = create_access_token({"sub": admin.username, "role": admin.role})
        admin_auth_header = {"Authorization": f"Bearer {token}"}

        cif_file = SAMPLE_DIR / "bataMnO2.cif"

        assert cif_file.exists(), f"CIF sample文件不存在: {cif_file}"

        with open(cif_file, "rb") as f:
            files = {"file": ("bataMnO2.cif", f, "chemical/x-cif")}
            response = test_client.post(
                "/files/", files=files, headers=admin_auth_header
            )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["filename"] == "bataMnO2.cif"

    def test_full_workflow_with_sample_data(self, test_client, test_db):
        """完整工作流：上傳、標籤、結論、檢索"""
        from app.security import create_access_token

        # 創建管理員
        admin = User(
            username="workflow_admin",
            email="workflow_admin@test.com",
            hashed_password=simple_hash("admin123"),
            role="admin",
        )
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)

        token = create_access_token({"sub": admin.username, "role": admin.role})
        admin_auth_header = {"Authorization": f"Bearer {token}"}

        # 1. 上傳文件
        sample_file = SAMPLE_DIR / "20251203 nmo.txt"

        assert sample_file.exists(), f"Sample文件不存在: {sample_file}"

        with open(sample_file, "rb") as f:
            files = {"file": ("20251203_nmo.txt", f, "text/plain")}
            response = test_client.post(
                "/files/", files=files, headers=admin_auth_header
            )

        assert response.status_code in [200, 201]
        file_data = response.json()
        file_id = file_data["id"]

        # 2. 創建標籤
        response = test_client.post(
            "/tags/", json={"name": "NMO材料"}, headers=admin_auth_header
        )
        assert response.status_code in [200, 201]
        tag_data = response.json()
        tag_id = tag_data["id"]

        # 3. 為文件添加標籤
        response = test_client.post(
            f"/files/{file_id}/tags/{tag_id}", headers=admin_auth_header
        )
        assert response.status_code == 200

        # 4. 添加結論 (使用正確的字段名)
        response = test_client.post(
            f"/files/{file_id}/conclusions/",
            json={"content": "NMO材料的電化學測試數據"},
            headers=admin_auth_header,
        )
        assert response.status_code in [200, 201]

        # 5. 驗證文件信息
        response = test_client.get(f"/files/{file_id}", headers=admin_auth_header)
        assert response.status_code == 200
        file_info = response.json()
        # File 模型直接返回，包含 id, filename, file_hash, storage_key, created_at, updated_at
        assert file_info["id"] == file_id
        assert file_info["filename"] == "20251203_nmo.txt"

        print(f"✓ 完整工作流測試成功：文件ID={file_id}")


# 這些 fixtures 由 conftest.py 提供
# @pytest.fixture
# def admin_auth_header(test_db: Session):
#     """創建管理員並返回認證header"""
#     from app.security import create_access_token
#
#     admin = User(
#         username="test_admin",
#         email="admin@test.com",
#         hashed_password=simple_hash("admin123"),
#         role="admin",
#     )
#     test_db.add(admin)
#     test_db.commit()
#     test_db.refresh(admin)
#
#     token = create_access_token({"sub": admin.username, "role": admin.role})
#     return {"Authorization": f"Bearer {token}"}
#
#
# @pytest.fixture
# def test_client(test_db):
#     """創建測試客戶端"""
#     return TestClient(app)
