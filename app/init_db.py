"""
資料庫初始化腳本

【目的】
用於 Docker 容器啟動時自動初始化資料庫結構和預設數據

【用法】
python -m app.init_db

【功能】
1. 建立所有資料表結構
2. 建立預設的系統管理員帳號（可選）
3. 建立初始標籤分類（可選）
4. 執行資料庫遷移（若需要）
"""

import os
import sys
import logging
from sqlalchemy import text, inspect
from .database import engine, SessionLocal, Base
from .models import User, RoleEnum
from .security import hash_password

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_all_tables():
    """建立所有資料表"""
    logger.info("開始建立資料表...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ 資料表建立完成")
        return True
    except Exception as e:
        logger.error(f"✗ 資料表建立失敗: {e}")
        return False


def check_tables_exist():
    """檢查資料表是否已存在"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"現有資料表: {tables}")
    return len(tables) > 0


def create_default_admin():
    """建立預設管理員帳號"""
    db = SessionLocal()
    try:
        # 檢查是否已存在任何使用者
        existing_user = db.query(User).filter(User.email == "admin@labflow.local").first()
        if existing_user:
            logger.info("✓ 管理員帳號已存在，跳過建立")
            return True
        
        # 建立預設管理員
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin = User(
            email="admin@labflow.local",
            username="admin",
            hashed_password=hash_password(admin_password),
            role=RoleEnum.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        logger.info(f"✓ 預設管理員帳號建立成功")
        logger.info(f"  帳號: admin@labflow.local")
        logger.info(f"  密碼: {admin_password} (建議立即修改)")
        return True
    except Exception as e:
        logger.error(f"✗ 建立管理員失敗: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def create_default_tags():
    """建立預設標籤分類"""
    from .models import Tag
    
    db = SessionLocal()
    try:
        default_tags = [
            "XRD", "SEM", "TEM", "AFM", "鞋陶",
            "Cr-doped", "Ni-doped", "Co-doped", "Fe-doped",
            "alpha", "beta", "gamma",
            "cycle-test", "impedance", "CV", "chronoamperometry"
        ]
        
        existing_count = db.query(Tag).count()
        if existing_count > 0:
            logger.info(f"✓ 標籤已存在 ({existing_count} 個)，跳過建立")
            return True
        
        for tag_name in default_tags:
            try:
                tag = Tag(name=tag_name)
                db.add(tag)
            except ValueError as e:
                logger.warning(f"  跳過無效標籤 '{tag_name}': {e}")
        
        db.commit()
        logger.info(f"✓ 預設標籤建立完成 ({len(default_tags)} 個)")
        return True
    except Exception as e:
        logger.error(f"✗ 建立標籤失敗: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_database():
    """驗證資料庫完整性"""
    logger.info("驗證資料庫...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✓ 資料庫連線正常")
        return True
    except Exception as e:
        logger.error(f"✗ 資料庫連線失敗: {e}")
        return False


def main():
    """主初始化流程"""
    logger.info("=" * 60)
    logger.info("LabFlow 資料庫初始化")
    logger.info("=" * 60)
    
    # 1. 驗證資料庫連線
    if not verify_database():
        sys.exit(1)
    
    # 2. 檢查現有表
    tables_exist = check_tables_exist()
    
    # 3. 建立資料表
    if not create_all_tables():
        sys.exit(1)
    
    # 4. 建立預設管理員（首次初始化時）
    if not tables_exist or os.getenv("FORCE_INIT_ADMIN") == "true":
        create_default_admin()
    
    # 5. 建立預設標籤（首次初始化時）
    if not tables_exist or os.getenv("FORCE_INIT_TAGS") == "true":
        create_default_tags()
    
    logger.info("=" * 60)
    logger.info("✓ 資料庫初始化完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
