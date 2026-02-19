"""
同步功能測試 - 驗證資料同步和孤立記錄刪除
"""
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models
import os

client = TestClient(app)


def test_file_status_empty():
    """測試空系統的檔案狀態"""
    # 清空資料庫
    db = SessionLocal()
    db.query(models.File).delete()
    db.query(models.Tag).delete()
    db.commit()
    db.close()
    
    response = client.get("/admin/file-status/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_db_records"] == 0
    assert data["valid_files"] == 0
    assert data["orphaned_files"] == 0


def test_sync_files_with_orphaned():
    """測試同步功能 - 刪除孤立記錄"""
    db = SessionLocal()
    
    # 清空資料庫
    db.query(models.File).delete()
    db.query(models.Tag).delete()
    db.commit()
    
    # 建立孤立記錄（不存在的實體檔案）
    orphaned_file = models.File(
        filename="nonexistent.txt",
        storage_key="data/managed/nonexistent.txt",
        file_hash="0" * 64
    )
    db.add(orphaned_file)
    db.commit()
    db.refresh(orphaned_file)
    orphaned_id = orphaned_file.id
    
    # 驗證孤立記錄存在
    response = client.get("/admin/file-status/")
    data = response.json()
    assert data["total_db_records"] == 1
    assert data["orphaned_files"] == 1
    
    # 執行同步
    response = client.post("/admin/sync-files/")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["deleted_files"] == 1
    assert orphaned_id in result["orphaned_ids"]
    
    # 驗證孤立記錄已刪除
    response = client.get("/admin/file-status/")
    data = response.json()
    assert data["total_db_records"] == 0
    assert data["orphaned_files"] == 0
    
    db.close()


def test_sync_with_valid_file():
    """測試同步功能 - 保留有效檔案"""
    db = SessionLocal()
    
    # 清空資料庫
    db.query(models.File).delete()
    db.commit()
    
    # 建立有效檔案（實體檔案存在）
    # 先建立實體檔案
    test_file_path = "data/managed/test_sync.txt"
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
    with open(test_file_path, "w") as f:
        f.write("test content")
    
    try:
        # 建立資料庫記錄
        valid_file = models.File(
            filename="test_sync.txt",
            storage_key=test_file_path,
            file_hash="1" * 64
        )
        db.add(valid_file)
        db.commit()
        db.refresh(valid_file)
        
        # 驗證有效檔案
        response = client.get("/admin/file-status/")
        data = response.json()
        assert data["total_db_records"] == 1
        assert data["valid_files"] == 1
        assert data["orphaned_files"] == 0
        
        # 執行同步（應該不刪除任何東西）
        response = client.post("/admin/sync-files/")
        assert response.status_code == 200
        result = response.json()
        assert result["deleted_files"] == 0
        assert result["orphaned_ids"] == []
        
        # 驗證檔案仍然存在
        response = client.get("/admin/file-status/")
        data = response.json()
        assert data["total_db_records"] == 1
        assert data["valid_files"] == 1
    
    finally:
        # 清理
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        db.query(models.File).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_file_status_empty()
    test_sync_files_with_orphaned()
    test_sync_with_valid_file()
    print("✅ 所有同步功能測試通過！")
