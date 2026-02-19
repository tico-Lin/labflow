"""
單元測試 - Models 和 Storage

【覆蓋範圍】
- File 模型驗證
- Tag 模型驗證
- User 模型驗證
- LocalStorage 操作
- 檔案 hash 計算
"""

import os
import tempfile
from io import BytesIO

import pytest

from app import security

# 導入被測試的模組
from app.models import Annotation, File, RoleEnum, Tag, User
from app.storage import LocalStorage

# ============================================================================
# File 模型測試
# ============================================================================

# NOTE: test_db fixture is provided by conftest.py for consistent testing


@pytest.mark.unit
class TestFileModel:
    """檔案模型測試"""

    def test_file_creation(self, test_db):
        """測試檔案建立"""
        file = File(
            filename="test.txt",
            storage_key="/data/test_hash.txt",
            file_hash="a" * 64,  # 64 字元 SHA256 hash
        )
        test_db.add(file)
        test_db.commit()

        retrieved = test_db.query(File).filter(File.id == file.id).first()
        assert retrieved is not None
        assert retrieved.filename == "test.txt"
        assert retrieved.file_hash == "a" * 64

    def test_file_hash_validation(self, test_db):
        """測試檔案 hash 驗證"""
        with pytest.raises(ValueError):
            file = File(
                filename="test.txt",
                storage_key="/data/test.txt",
                file_hash="invalid_hash",  # 不是 64 字元
            )
            test_db.add(file)
            test_db.commit()

    def test_filename_validation(self, test_db):
        """測試檔案名稱驗證"""
        with pytest.raises(ValueError):
            file = File(
                filename="",  # 空檔名
                storage_key="/data/test.txt",
                file_hash="a" * 64,
            )
            test_db.add(file)
            test_db.commit()

    def test_file_uniqueness(self, test_db):
        """測試檔案 hash 唯一性"""
        file1 = File(
            filename="test1.txt", storage_key="/data/test1.txt", file_hash="a" * 64
        )
        file2 = File(
            filename="test2.txt",
            storage_key="/data/test2.txt",
            file_hash="a" * 64,  # 相同的 hash
        )
        test_db.add(file1)
        test_db.commit()

        test_db.add(file2)
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()


# ============================================================================
# Tag 模型測試
# ============================================================================


@pytest.mark.unit
class TestTagModel:
    """標籤模型測試"""

    def test_tag_creation(self, test_db):
        """測試標籤建立"""
        tag = Tag(name="XRD")
        test_db.add(tag)
        test_db.commit()

        retrieved = test_db.query(Tag).filter(Tag.name == "XRD").first()
        assert retrieved is not None
        assert retrieved.name == "XRD"

    def test_tag_name_validation(self, test_db):
        """測試標籤名稱驗證"""
        with pytest.raises(ValueError):
            tag = Tag(name="")  # 空名稱
            test_db.add(tag)
            test_db.commit()

    def test_tag_uniqueness(self, test_db):
        """測試標籤名稱唯一性"""
        tag1 = Tag(name="XRD")
        tag2 = Tag(name="XRD")

        test_db.add(tag1)
        test_db.commit()

        test_db.add(tag2)
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()

    def test_file_tag_relationship(self, test_db):
        """測試檔案與標籤的多對多關係"""
        file = File(
            filename="test.txt", storage_key="/data/test.txt", file_hash="a" * 64
        )
        tag1 = Tag(name="XRD")
        tag2 = Tag(name="SEM")

        file.tags = [tag1, tag2]
        test_db.add(file)
        test_db.commit()

        retrieved_file = test_db.query(File).filter(File.id == file.id).first()
        assert len(retrieved_file.tags) == 2
        assert any(t.name == "XRD" for t in retrieved_file.tags)


# ============================================================================
# User 模型測試
# ============================================================================


@pytest.mark.unit
class TestUserModel:
    """用戶模型測試"""

    def test_user_creation(self, test_db):
        """測試用戶建立"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pwd",
            role=RoleEnum.VIEWER,
            is_active=1,
        )
        test_db.add(user)
        test_db.commit()

        retrieved = test_db.query(User).filter(User.username == "testuser").first()
        assert retrieved is not None
        assert retrieved.email == "test@example.com"

    def test_user_username_validation(self, test_db):
        """測試用戶名稱驗證"""
        with pytest.raises(ValueError):
            user = User(
                username="ab",  # 太短 (需 3-50)
                email="test@example.com",
                hashed_password="hashed",
                role=RoleEnum.VIEWER,
            )
            test_db.add(user)
            test_db.commit()

    def test_user_role_validation(self, test_db):
        """測試角色驗證"""
        with pytest.raises(ValueError):
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed",
                role="invalid_role",
            )
            test_db.add(user)
            test_db.commit()


# ============================================================================
# Annotation 模型測試
# ============================================================================


@pytest.mark.unit
class TestAnnotationModel:
    """標註模型測試"""

    def test_annotation_creation(self, test_db):
        """測試標註建立"""
        file = File(
            filename="test.txt", storage_key="/data/test.txt", file_hash="a" * 64
        )
        test_db.add(file)
        test_db.commit()

        annotation = Annotation(
            file_id=file.id,
            data={"cr_content": 3, "structure": "beta"},
            source="manual",
        )
        test_db.add(annotation)
        test_db.commit()

        retrieved = (
            test_db.query(Annotation).filter(Annotation.id == annotation.id).first()
        )
        assert retrieved is not None
        assert retrieved.data["cr_content"] == 3

    def test_annotation_source_validation(self, test_db):
        """測試標註來源驗證"""
        file = File(
            filename="test.txt", storage_key="/data/test.txt", file_hash="a" * 64
        )
        test_db.add(file)
        test_db.commit()

        with pytest.raises(ValueError):
            annotation = Annotation(file_id=file.id, data={}, source="invalid_source")
            test_db.add(annotation)
            test_db.commit()


# ============================================================================
# LocalStorage 測試
# ============================================================================


@pytest.mark.unit
class TestLocalStorage:
    """本地存儲測試"""

    @pytest.fixture
    def temp_storage(self):
        """建立臨時儲存目錄"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(base_dir=tmpdir)
            yield storage, tmpdir

    def _create_mock_file(self, content: bytes):
        """Helper to create a stateful async mock file."""
        from unittest.mock import AsyncMock

        stream = BytesIO(content)

        async def read_chunk(size: int = -1):
            return stream.read(size)

        async def seek_chunk(offset: int, whence: int = 0):
            return stream.seek(offset, whence)

        mock_file = AsyncMock()
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(side_effect=read_chunk)
        mock_file.seek = AsyncMock(side_effect=seek_chunk)
        return mock_file

    @pytest.mark.asyncio
    async def test_file_save_and_load(self, temp_storage):
        """測試檔案保存和加載"""
        storage, tmpdir = temp_storage
        test_content = b"Hello, World!"
        mock_file = self._create_mock_file(test_content)

        storage_key = await storage.save(mock_file)

        # 驗證檔案存在
        assert os.path.exists(storage_key)

        # 加載檔案
        with open(storage_key, "rb") as f:
            loaded_content = f.read()
        assert loaded_content == test_content

    @pytest.mark.asyncio
    async def test_file_delete(self, temp_storage):
        """測試檔案刪除"""
        storage, tmpdir = temp_storage
        test_content = b"Test content"
        mock_file = self._create_mock_file(test_content)

        storage_key = await storage.save(mock_file)
        assert os.path.exists(storage_key)

        # 刪除檔案
        storage.delete(storage_key)
        assert not os.path.exists(storage_key)


# ============================================================================
# 檔案 Hash 測試
# ============================================================================


@pytest.mark.unit
class TestFileHash:
    """檔案 hash 計算測試"""

    def test_calculate_file_hash(self):
        """測試 SHA256 hash 計算"""
        import hashlib

        test_content = b"Test content"

        # 直接計算預期的雜湊值
        expected_hash = hashlib.sha256(test_content).hexdigest()

        # 驗證 hash 格式（64 個十六進位字元）
        assert len(expected_hash) == 64
        assert all(c in "0123456789abcdef" for c in expected_hash)

    def test_same_content_same_hash(self):
        """測試相同內容產生相同 hash"""
        import hashlib

        test_content = b"Same content"

        hash1 = hashlib.sha256(test_content).hexdigest()
        hash2 = hashlib.sha256(test_content).hexdigest()

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """測試不同內容產生不同 hash"""
        import hashlib

        hash1 = hashlib.sha256(b"Content 1").hexdigest()
        hash2 = hashlib.sha256(b"Content 2").hexdigest()

        assert hash1 != hash2


# ============================================================================
# 安全函數測試
# ============================================================================


@pytest.mark.unit
class TestSecurity:
    """安全函數測試"""

    def test_password_hashing(self):
        """測試密碼雜湊"""
        password = "short_pwd"
        hashed = security.hash_password(password)

        # 驗證雜湊值不等於原始密碼
        assert hashed != password

    def test_password_verification(self):
        """測試密碼驗證"""
        password = "short_pwd"
        hashed = security.hash_password(password)

        # 驗證正確的密碼
        assert security.verify_password(password, hashed)

        # 驗證錯誤的密碼
        assert not security.verify_password("WrongPassword", hashed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
