"""
資料庫連線配置模組 (Database Configuration Module)

【功能】
初始化 SQLAlchemy ORM 引擎、Session 工廠與基礎模型類別，
提供統一的資料庫連線管理與依賴注入介面。

【核心元件】
1. engine: SQLAlchemy 資料庫引擎（負責實際連線）
2. SessionLocal: Session 工廠（用於建立資料庫會話）
3. Base: 宣告式基礎類別（所有 Model 的父類別）
4. get_db(): 依賴注入函式（FastAPI 路由專用）

【資料庫支援】
- 開發環境：SQLite (預設 labflow.db)
- 生產環境：透過環境變數 DATABASE_URL 指定
  範例：postgresql://user:pass@localhost/dbname

【使用方式】
# 在 models.py 中定義資料表
from .database import Base
class User(Base):
    __tablename__ = "users"
    ...

# 在 main.py 中建立資料表
from .database import engine, Base
Base.metadata.create_all(bind=engine)

# 在 API 路由中注入資料庫
from fastapi import Depends
from .database import get_db

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

【設計模式】
- 工廠模式 (Factory Pattern)：SessionLocal 作為 Session 工廠
- 依賴注入 (Dependency Injection)：get_db() 自動管理連線生命週期

【版本】v1.0
【最後更新】2025/01/07
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# ========== 資料庫連線配置 ==========

# 從環境變數讀取資料庫連線字串，若未設定則使用本機 SQLite
# 環境變數範例：
#   - SQLite:     sqlite:///./labflow.db
#   - PostgreSQL: postgresql://user:password@localhost/labflow
#   - MySQL:      mysql+pymysql://user:password@localhost/labflow
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./labflow.db")

# ========== 建立資料庫引擎 ==========

# SQLite 專用設定：允許多執行緒存取同一連線
# 其他資料庫（PostgreSQL/MySQL）不需要此設定
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

# 建立引擎（Engine）：負責管理資料庫連線池與 SQL 方言
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# ========== 建立 Session 工廠 ==========

# SessionLocal 是一個類別工廠，每次呼叫會產生新的 Session 實例
# - autocommit=False: 需手動呼叫 commit() 才會提交變更
# - autoflush=False:  不會在查詢前自動執行 flush()
# - bind=engine:      綁定到上面建立的引擎
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ========== 建立 ORM 基礎類別 ==========

# 所有資料表模型（Model）都必須繼承此類別
# 範例：class User(Base): ...
Base = declarative_base()

# ========== 依賴注入函式 ==========

def get_db():
    """
    FastAPI 依賴注入函式：提供資料庫 Session
    
    【生命週期】
    1. 建立 Session（進入 try 區塊）
    2. yield 給路由函式使用
    3. 路由執行完畢後自動關閉連線（finally 區塊）
    
    【使用範例】
    @app.get("/items")
    def read_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
    
    【錯誤處理】
    若路由發生例外，Session 仍會在 finally 區塊正確關閉，
    避免連線洩漏（connection leak）
    """
    db = SessionLocal()
    try:
        yield db  # 將 Session 交給路由函式
    finally:
        db.close()  # 確保連線釋放
