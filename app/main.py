"""
LabFlow API - 實驗室資料管理系統後端

功能概覽：
- 檔案管理：上傳檔案、自動去重（基於 SHA-256）、查詢檔案列表
- 標籤系統：建立標籤、為檔案添加多對多標籤關聯
- 結論記錄：為檔案附加實驗結論文字
- 註解系統：為檔案添加結構化 JSON 註解（支援自動/手動來源）

技術架構：
- 框架：FastAPI
- 資料庫：SQLite + SQLAlchemy ORM
- 儲存層：LocalStorage（可抽換）
- 註解層：LocalAnnotationProvider（可抽換）

主要端點：
- GET  /                              健康檢查
- POST /files/                        上傳檔案
- GET  /files/                        取得檔案列表
- POST /tags/                         建立標籤
- POST /files/{id}/tags/{tag_id}      為檔案添加標籤
- POST /files/{id}/conclusions/       為檔案添加結論
- POST /files/{id}/annotations/       為檔案添加註解
- GET  /files/{id}/annotations/       取得檔案的所有註解

設計特點：
- 檔案去重：透過 file_hash 避免重複儲存相同檔案
- 依賴注入：使用 Depends(get_db) 管理資料庫連線生命週期
- 抽象化：storage 和 annotation_provider 可輕鬆替換實作（如雲端儲存、遠端註解服務）

環境變數：
- STORAGE_PATH：檔案儲存路徑（預設：data/managed）
"""

import os
import time
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import annotation, database, i18n, models, schemas, security
from .api.classification_routes import router as classification_router
from .api.reasoning_routes import router as reasoning_router
from .logging_config import configure_logging, get_logger, log_with_context
from .models import file_tags
from .services.analysis_service import AnalysisService, AnalysisServiceError
from .services.classification_service import FileClassificationService
from .services.reasoning_service import ReasoningService
from .services.script_service import ScriptService
from .storage import LocalStorage, calculate_file_hash

# 設定日誌
configure_logging()
logger = get_logger(__name__)

# 初始化資料庫 (若 labflow.db 不存在會自動建立)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="LabFlow API",
    description="實驗室研究資料管理系統 - 支援檔案去重、標籤、結論、結構化標註、JWT 身份驗證",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_with_context(
            logger,
            "error",
            "Request failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
            error=str(exc),
        )
        raise
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-Id"] = request_id
    log_with_context(
        logger,
        "info",
        "Request completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    """自定義 OpenAPI 文檔"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="LabFlow API",
        version="0.2.0",
        description="""
        # LabFlow - 實驗室研究資料管理系統

        ## 功能概覽

        - **檔案管理**: 上傳檔案、自動去重、查詢列表
        - **標籤系統**: 建立標籤、為檔案添加多對多標籤
        - **結論記錄**: 為檔案附加實驗結論文字
        - **結構化標註**: 為檔案添加 JSON 格式的結構化標註
        - **身份驗證**: JWT Bearer Token 認證、用戶管理、RBAC
        - **批量操作**: 批量上傳、批量刪除、批量建立標籤
        - **性能優化**: Redis 快取、資料庫索引、查詢優化

        ## 認證

        大多數 API 需要 JWT Bearer Token 認證。

        1. 使用 `POST /auth/login` 或 `POST /auth/register` 取得令牌
        2. 在請求頭中添加: `Authorization: Bearer <token>`

        ## 版本歷史

        - **v0.2.0**: 生產就緒版本
          - JWT 認證與 RBAC
          - 批量操作 API
          - 性能優化（索引、快取、查詢優化）
          - 完整測試覆蓋
          - 結構化日誌
        - **v0.1.1**: 資料同步功能
        - **v0.1.0**: MVP 版本

        ## 部署指南

        ### 本地開發
        ```bash
        python -m venv .venv
        .venv/Scripts/activate
        pip install -r requirements.txt
        python -m uvicorn app.main:app --reload
        ```

        ### Docker 部署
        ```bash
        docker-compose up -d
        ```

        ### 初始化資料庫
        ```bash
        python -m app.init_db
        ```

        ## API 端點組織

        - `/auth/` - 認證端點
        - `/users/` - 用戶管理
        - `/files/` - 檔案管理
        - `/tags/` - 標籤管理
        - `/admin/` - 系統管理
        """,
        routes=app.routes,
    )

    # 添加自定義標籤分組
    openapi_schema["tags"] = [
        {"name": "認證", "description": "使用者認證與令牌管理"},
        {"name": "檔案管理", "description": "檔案上傳、刪除、查詢"},
        {"name": "標籤系統", "description": "標籤管理與標籤關聯"},
        {"name": "結論與標註", "description": "結論記錄與結構化標註"},
        {"name": "批量操作", "description": "批量上傳、刪除、建立"},
        {"name": "系統維護", "description": "管理員工具與系統管理"},
        {"name": "分析工具", "description": "外部分析工具與整合算法"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(reasoning_router)
app.include_router(classification_router)

# Annotation provider (本地實作)
annotation_provider = annotation.LocalAnnotationProvider()

# 建立全域 storage 實例，會使用環境變數 STORAGE_PATH（若未設定則預設 data/managed）
storage = LocalStorage()

# 建立全域檔案分類服務實例
classification_service = FileClassificationService()

# 最大上傳大小（bytes），可由環境變數覆寫，預設 50 MiB
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))

# 本地離線模式（預設 true）
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "true").strip().lower() in {"1", "true", "yes"}


# 取得資料庫連線的依賴
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_offline_write(current_user: Dict[str, Any], operation: str = "修改") -> None:
    """
    檢查離線用戶是否嘗試修改操作

    Args:
        current_user: 當前用戶信息
        operation: 操作名稱（用於錯誤訊息）

    Raises:
        HTTPException: 若為離線用戶且嘗試修改
    """
    if security.is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"離線模式下不允許執行 {operation} 操作。請登錄後執行此操作。",
        )


# 定義接收資料的格式
class AnnotationCreate(BaseModel):
    """標註資料模型"""

    data: Dict[str, Any] = Field(..., description="標註內容 (支援任意 JSON 結構)")
    source: str = Field(default="manual", description="標註來源 (manual/auto/imported)")


# --- API 路由 ---


@app.get("/")
def read_root():
    """根路徑：API 運行狀態確認"""
    return {"message": "LabFlow API is running!"}


@app.get("/health")
def health_check():
    """健康檢查端點"""
    return {"status": "ok", "offline_mode": OFFLINE_MODE, "mode": "local"}


# ==================== 國際化 (i18n) 端點 ====================


@app.get("/i18n/locales", tags=["i18n"])
def get_available_locales():
    """
    獲取所有可用的語言代碼

    Returns:
        可用語言代碼列表，例如 ["zh", "en"]
    """
    return {"locales": i18n.get_available_locales()}


@app.get("/i18n/translations/{locale}", tags=["i18n"])
def get_translations(locale: str):
    """
    獲取指定語言的所有翻譯

    Args:
        locale: 語言代碼，例如 "zh", "en"

    Returns:
        該語言的完整翻譯字典
    """
    manager = i18n.get_i18n_manager()

    if locale not in manager.translations:
        raise HTTPException(status_code=404, detail=f"語言 '{locale}' 不存在")

    return {"locale": locale, "translations": manager.translations[locale]}


@app.get("/i18n/translate/{locale}/{key:path}", tags=["i18n"])
def translate_key(locale: str, key: str):
    """
    獲取指定語言和鍵的翻譯

    Args:
        locale: 語言代碼，例如 "zh", "en"
        key: 翻譯鍵，支持點分隔的嵌套結構，例如 "common.welcome"

    Returns:
        翻譯後的文本
    """
    translator = i18n.get_translator(locale)
    translation = translator(key)

    return {"locale": locale, "key": key, "translation": translation}


@app.get(
    "/analysis/tools", response_model=List[schemas.AnalysisToolSpec], tags=["分析工具"]
)
def list_analysis_tools(db: Session = Depends(get_db)):
    service = AnalysisService(db, storage)
    return service.list_tools()


@app.post(
    "/analysis/run", response_model=schemas.AnalysisRunResponse, tags=["分析工具"]
)
def run_analysis(request: schemas.AnalysisRunRequest, db: Session = Depends(get_db)):
    service = AnalysisService(db, storage)
    try:
        result = service.run_tool(
            tool_id=request.tool_id,
            file_id=request.file_id,
            parameters=request.parameters,
            store_output=request.store_output,
        )
    except AnalysisServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


# ==================== 身份驗證端點 ====================


@app.post(
    "/auth/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    用戶註冊端點

    - 檢查用戶名稱和郵件是否已存在
    - 對密碼進行 bcrypt 雜湊
    - 預設角色為 viewer
    """
    # 檢查用戶名稱是否已存在
    existing_user = (
        db.query(models.User).filter(models.User.username == user_data.username).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用戶名稱已存在"
        )

    # 檢查郵件是否已存在
    if user_data.email:
        existing_email = (
            db.query(models.User).filter(models.User.email == user_data.email).first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="郵件已被使用"
            )

    # 建立新用戶
    hashed_password = security.hash_password(user_data.password)
    db_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role="viewer",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"新用戶已註冊: {user_data.username}")
    return db_user


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    用戶登錄端點

    - 驗證用戶名稱和密碼
    - 返回 access_token 和 refresh_token
    """
    # 查詢用戶
    user = (
        db.query(models.User)
        .filter(models.User.username == login_data.username)
        .first()
    )

    if not user or not security.verify_password(
        login_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用戶名稱或密碼不正確"
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="帳號已停用")

    # 建立令牌
    access_token = security.create_access_token(
        {"sub": user.id, "username": user.username, "role": user.role}
    )

    refresh_token = security.create_refresh_token(
        {"sub": user.id, "username": user.username}
    )

    logger.info(f"用戶登錄: {user.username}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/auth/refresh", response_model=schemas.TokenResponse)
def refresh_token(token_req: security.TokenRequest, db: Session = Depends(get_db)):
    """
    令牌刷新端點

    - 使用 refresh_token 獲取新的 access_token
    """
    try:
        payload = security.verify_token(token_req.refresh_token)
        user_id = payload.get("sub")
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的刷新令牌"
            )

        # 從資料庫重新查詢用戶信息
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用戶不存在或已停用"
            )

        # 建立新的 access_token
        access_token = security.create_access_token(
            {"sub": user.id, "username": user.username, "role": user.role}
        )

        # 建立新的 refresh_token
        new_refresh_token = security.create_refresh_token(
            {"sub": user.id, "username": user.username}
        )

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    except security.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的刷新令牌"
        )


@app.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_info(
    current_user: Dict[str, Any] = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得當前用戶信息

    - 需要提供有效的 Bearer token
    """
    user = db.query(models.User).filter(models.User.id == current_user["id"]).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用戶不存在")

    return user


@app.get("/users/", response_model=List[schemas.UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    列出所有用戶（需要管理員權限）
    """
    current_user = security.get_current_admin(security.get_current_user(authorization))
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    更新用戶（管理員或用戶自己）
    """
    current_user = security.get_current_user(authorization)

    # 檢查是否為管理員或修改自己的帳號
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="無權限修改其他用戶"
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用戶不存在")

    if user_update.email:
        user.email = user_update.email

    if user_update.role and current_user["role"] == "admin":
        user.role = user_update.role

    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    刪除用戶（管理員權限）
    """
    current_user = security.get_current_admin(security.get_current_user(authorization))

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用戶不存在")

    db.delete(user)
    db.commit()
    logger.info(f"用戶已刪除: {user.username}")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


# ==================== 檔案管理端點 ====================


@app.post("/files/", response_model=schemas.File, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    auto_classify: bool = True,
    auto_tag: bool = True,
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    上傳檔案端點

    功能：
    - 自動計算 SHA-256 指紋
    - 若相同檔案已存在，直接回傳既有記錄（去重）
    - 否則儲存檔案並建立資料庫記錄
    - 可選：自動分類並添加標籤

    參數：
    - file: 上傳的檔案
    - auto_classify: 是否自動分類檔案 (預設: True)
    - auto_tag: 是否自動添加標籤 (預設: True)

    回傳：
    - 201: 檔案上傳成功 (或去重後回傳既有檔案)
    - 400: 檔案驗證失敗
    - 403: 離線模式下無法上傳
    - 500: 伺服器錯誤
    """
    # 檢查離線用戶是否嘗試上傳
    check_offline_write(current_user, "檔案上傳")
    try:
        # 驗證檔案不為空
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="檔案名稱不能為空"
            )

        # 檢查檔案大小以避免超大檔案上傳（若後端儲存或資源有限）
        try:
            await file.seek(0, os.SEEK_END)
            size = await file.tell()
            await file.seek(0)
        except Exception:
            size = None

        if size is not None and size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"檔案大小超過上限 ({MAX_UPLOAD_SIZE} bytes)",
            )

        # 計算檔案指紋，檢查是否已存在相同檔案
        file_hash = await calculate_file_hash(file)
        existing = (
            db.query(models.File).filter(models.File.file_hash == file_hash).first()
        )
        if existing:
            logger.info(f"檔案已存在（去重）: {file.filename} (ID: {existing.id})")
            return existing

        # 使用注入的 storage 實作來儲存檔案
        # 若 storage 支援以 hash 命名的儲存方法，優先使用以避免檔名衝突
        if hasattr(storage, "save_with_hash"):
            storage_key = await storage.save_with_hash(file, file_hash)
        else:
            storage_key = await storage.save(file)
        logger.info(f"檔案已儲存: {file.filename} -> {storage_key}")

        db_file = models.File(
            filename=file.filename, storage_key=storage_key, file_hash=file_hash
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        # 自動分類和標籤
        if auto_classify:
            try:
                classification_result = classification_service.classify_file(
                    file.filename
                )
                logger.info(
                    f"檔案分類完成: {file.filename} -> {classification_result.file_type} "
                    f"(confidence: {classification_result.confidence:.2f})"
                )

                # 自動添加標籤
                if auto_tag and classification_result.suggested_tags:
                    for tag_name in classification_result.suggested_tags:
                        # 查找或創建標籤
                        tag = (
                            db.query(models.Tag)
                            .filter(models.Tag.name == tag_name)
                            .first()
                        )
                        if not tag:
                            tag = models.Tag(name=tag_name)
                            db.add(tag)
                            db.commit()
                            db.refresh(tag)
                            logger.info(f"創建新標籤: {tag_name}")

                        # 添加標籤到檔案（避免重複）
                        if tag not in db_file.tags:
                            db_file.tags.append(tag)

                    db.commit()
                    db.refresh(db_file)
                    logger.info(
                        f"已自動添加 {len(classification_result.suggested_tags)} 個標籤"
                    )

                # 將分類元數據存儲為註解
                if classification_result.metadata:
                    annotation = models.Annotation(
                        file_id=db_file.id,
                        data={
                            "classification": {
                                "file_type": classification_result.file_type,
                                "confidence": classification_result.confidence,
                                "metadata": classification_result.metadata,
                            }
                        },
                        source="auto_classification",
                    )
                    db.add(annotation)
                    db.commit()
                    logger.info("已存儲分類元數據為註解")

            except Exception as e:
                logger.error(f"自動分類失敗: {str(e)}")
                # 分類失敗不影響檔案上傳

        return db_file

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上傳檔案失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案上傳失敗: {str(e)}",
        )


@app.get("/files/", response_model=List[schemas.File])
def read_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    取得所有檔案列表
    - 支援分頁（skip/limit）
    """
    files = db.query(models.File).offset(skip).limit(limit).all()
    return files


@app.get("/files/search")
def search_files(
    q: str | None = None,
    tag_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    搜尋檔案，支援 q (檔名子字串) 與 tag_id 篩選，回傳分頁物件 {items,total,limit,offset}
    """
    query = db.query(models.File)
    if q:
        query = query.filter(models.File.filename.ilike(f"%{q}%"))
    if tag_id:
        query = query.join(models.File.tags).filter(models.Tag.id == tag_id)

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total, "limit": limit, "offset": skip}


@app.get("/files/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )
    return file


@app.get("/files/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )
    path = file.storage_key
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="實體檔案不存在"
        )
    return FileResponse(
        path, media_type="application/octet-stream", filename=file.filename
    )


@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    """刪除檔案"""
    # 檢查離線用戶
    check_offline_write(current_user, "檔案刪除")

    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )
    # 刪除實體檔案（若存在）並刪除 DB 紀錄
    try:
        if file.storage_key:
            storage.delete(file.storage_key)
    except Exception:
        logger.exception("刪除實體檔案時發生錯誤")
    db.delete(file)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@app.get("/tags/", response_model=List[schemas.Tag])
def list_tags(db: Session = Depends(get_db)):
    tags = db.query(models.Tag).all()
    return tags


@app.post("/files/{file_id}/tags", status_code=status.HTTP_200_OK)
def add_tag_to_file_body(
    file_id: int,
    payload: Dict[str, int],
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    新增標籤關聯（接受 body: {"tag_id": int}），相容於文件規格
    """
    check_offline_write(current_user, "標籤添加")

    tag_id = payload.get("tag_id")
    if tag_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="tag_id is required"
        )

    file = db.query(models.File).filter(models.File.id == file_id).first()
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"標籤 ID {tag_id} 不存在"
        )

    if tag in file.tags:
        logger.info(f"標籤已關聯: 檔案 {file_id} 已有標籤 {tag_id}")
        return file

    file.tags.append(tag)
    db.commit()
    db.refresh(file)
    logger.info(f"標籤已添加: 檔案 {file_id} -> 標籤 {tag_id}")
    return file


@app.delete("/files/{file_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag_from_file(
    file_id: int,
    tag_id: int,
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    check_offline_write(current_user, "標籤移除")

    file = db.query(models.File).filter(models.File.id == file_id).first()
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not file or not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="file or tag not found"
        )
    if tag in file.tags:
        file.tags.remove(tag)
        db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@app.get("/files/{file_id}/conclusions/", response_model=List[schemas.Conclusion])
def get_conclusions(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )
    return (
        db.query(models.Conclusion).filter(models.Conclusion.file_id == file_id).all()
    )


@app.put("/conclusions/{conclusion_id}")
def update_conclusion(
    conclusion_id: int,
    payload: Dict[str, str],
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    check_offline_write(current_user, "結論更新")

    c = (
        db.query(models.Conclusion)
        .filter(models.Conclusion.id == conclusion_id)
        .first()
    )
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conclusion not found"
        )
    content = payload.get("content")
    if content is None or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="content is required"
        )
    c.content = content.strip()
    db.commit()
    db.refresh(c)
    return c


@app.delete("/conclusions/{conclusion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conclusion(
    conclusion_id: int,
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    check_offline_write(current_user, "結論刪除")

    c = (
        db.query(models.Conclusion)
        .filter(models.Conclusion.id == conclusion_id)
        .first()
    )
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conclusion not found"
        )
    db.delete(c)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@app.post("/tags/", response_model=schemas.Tag, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag: schemas.TagCreate,
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    建立標籤端點

    功能：
    - 若標籤名稱已存在，回傳既有標籤（避免重複）
    - 否則建立新標籤

    參數：
    - tag.name: 標籤名稱（必填）

    回傳：
    - 201: 標籤建立成功
    - 400: 標籤名稱不能為空
    - 403: 離線模式下無法建立標籤
    """
    check_offline_write(current_user, "標籤建立")
    if not tag.name or not tag.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="標籤名稱不能為空"
        )

    # 檢查標籤是否已存在
    existing_tag = (
        db.query(models.Tag).filter(models.Tag.name == tag.name.strip()).first()
    )
    if existing_tag:
        logger.info(f"標籤已存在: {tag.name} (ID: {existing_tag.id})")
        return existing_tag

    db_tag = models.Tag(name=tag.name.strip())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    logger.info(f"標籤已建立: {tag.name} (ID: {db_tag.id})")
    return db_tag


@app.post(
    "/files/{file_id}/tags/{tag_id}",
    response_model=schemas.File,
    status_code=status.HTTP_200_OK,
)
def add_tag_to_file(
    file_id: int,
    tag_id: int,
    current_user: Dict[str, Any] = Depends(security.get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    為檔案添加標籤端點

    功能：
    - 建立檔案與標籤的多對多關聯
    - 避免重複添加相同標籤

    參數：
    - file_id: 檔案 ID
    - tag_id: 標籤 ID

    回傳：
    - 200: 標籤添加成功
    - 404: 檔案或標籤不存在
    """
    check_offline_write(current_user, "標籤添加")

    file = db.query(models.File).filter(models.File.id == file_id).first()
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"標籤 ID {tag_id} 不存在"
        )

    # 避免重複添加
    if tag in file.tags:
        logger.info(f"標籤已關聯: 檔案 {file_id} 已有標籤 {tag_id}")
        return file

    file.tags.append(tag)
    db.commit()
    db.refresh(file)
    logger.info(f"標籤已添加: 檔案 {file_id} -> 標籤 {tag_id}")
    return file


@app.post(
    "/files/{file_id}/conclusions/",
    response_model=schemas.Conclusion,
    status_code=status.HTTP_201_CREATED,
)
def create_conclusion(
    file_id: int, conclusion: schemas.ConclusionCreate, db: Session = Depends(get_db)
):
    """
    為檔案添加結論端點

    功能：
    - 用於記錄實驗結果、觀察或分析結論
    - 支援 Markdown 格式長文字

    參數：
    - file_id: 檔案 ID
    - conclusion.content: 結論內容

    回傳：
    - 201: 結論新增成功
    - 400: 結論內容不能為空
    - 404: 檔案不存在
    """
    if not conclusion.content or not conclusion.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="結論內容不能為空"
        )

    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )

    db_conclusion = models.Conclusion(
        file_id=file_id, content=conclusion.content.strip()
    )
    db.add(db_conclusion)
    db.commit()
    db.refresh(db_conclusion)
    logger.info(f"結論已新增: 檔案 {file_id} (結論 ID: {db_conclusion.id})")
    return db_conclusion


# --- Annotation endpoints ---
@app.post(
    "/files/{file_id}/annotations/",
    response_model=schemas.Annotation,
    status_code=status.HTTP_201_CREATED,
)
def add_annotation(file_id: int, ann: AnnotationCreate, db: Session = Depends(get_db)):
    """
    為檔案添加註解端點

    功能：
    - 支援任意 JSON 結構（data 欄位）
    - 可標記來源（manual/auto/imported）
    - 透過 annotation_provider 處理，便於未來擴展（如遠端服務）

    參數：
    - file_id: 檔案 ID
    - ann.data: 標註內容 (JSON)
    - ann.source: 標註來源

    回傳：
    - 201: 標註新增成功
    - 400: 標註內容為空
    - 404: 檔案不存在
    """
    try:
        # 驗證檔案是否存在
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"檔案 ID {file_id} 不存在",
            )

        # 驗證標註資料不為空
        if not ann.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="標註內容不能為空"
            )

        # 透過「供應商」來處理，而不是直接寫 DB
        # 這樣未來換供應商時，這行程式碼幾乎不用改
        result = annotation_provider.add_annotation(db, file_id, ann.data, ann.source)
        logger.info(f"標註已新增: 檔案 {file_id} (來源: {ann.source})")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"新增標註失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"新增標註失敗: {str(e)}",
        )


@app.get("/files/{file_id}/annotations/", response_model=List[schemas.Annotation])
def get_annotations(file_id: int, db: Session = Depends(get_db)):
    """
    取得檔案的所有註解端點

    功能：
    - 透過 annotation_provider 查詢

    參數：
    - file_id: 檔案 ID

    回傳：
    - 200: 註解列表 (若無則為空陣列)
    - 404: 檔案不存在
    """
    # 檢查檔案是否存在
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案 ID {file_id} 不存在"
        )

    return annotation_provider.get_annotations(db, file_id)


# --- 系統維護端點 ---
@app.post("/admin/sync-files/", response_model=dict, status_code=status.HTTP_200_OK)
def sync_files(db: Session = Depends(get_db)):
    """
    同步資料庫與實體檔案系統

    功能：
    - 掃描資料庫中的所有檔案記錄
    - 檢查對應的實體檔案是否存在
    - 刪除孤立記錄（實體檔案不存在的記錄）
    - 檢測新增的實體檔案（不在資料庫的檔案，可選）

    回傳：
    - deleted_files: 刪除的孤立記錄數
    - orphaned_ids: 被刪除的檔案 ID 列表
    - status: "success" 或 "error"
    - message: 詳細訊息
    """
    try:
        # 查詢所有檔案記錄
        all_files = db.query(models.File).all()
        orphaned_ids = []

        print(f"[SYNC] 開始同步，掃描 {len(all_files)} 筆記錄...")

        for file_record in all_files:
            storage_key = file_record.storage_key

            # 檢查實體檔案是否存在
            if not storage_key or not os.path.exists(storage_key):
                logger.warning(
                    f"[SYNC] 發現孤立記錄：ID {file_record.id}, filename={file_record.filename}"
                )
                orphaned_ids.append(file_record.id)

                # 刪除相關的標籤關聯、註解、結論
                db.query(file_tags).filter(
                    file_tags.c.file_id == file_record.id
                ).delete()
                db.query(models.Annotation).filter(
                    models.Annotation.file_id == file_record.id
                ).delete()
                db.query(models.Conclusion).filter(
                    models.Conclusion.file_id == file_record.id
                ).delete()

                # 刪除檔案記錄
                db.delete(file_record)

        # 提交變更
        if orphaned_ids:
            db.commit()
            logger.info(f"[SYNC] 已刪除 {len(orphaned_ids)} 筆孤立記錄")

        return {
            "status": "success",
            "message": f"同步完成：刪除 {len(orphaned_ids)} 筆孤立記錄",
            "deleted_files": len(orphaned_ids),
            "orphaned_ids": orphaned_ids,
        }

    except Exception as e:
        logger.error(f"[SYNC] 同步失敗: {str(e)}")
        return {
            "status": "error",
            "message": f"同步失敗: {str(e)}",
            "deleted_files": 0,
            "orphaned_ids": [],
        }


@app.get("/admin/file-status/", response_model=dict, status_code=status.HTTP_200_OK)
def get_file_status(db: Session = Depends(get_db)):
    """
    取得檔案系統狀態

    回傳：
    - total_db_records: 資料庫中的檔案記錄數
    - valid_files: 實體檔案存在的記錄數
    - orphaned_files: 孤立記錄數（實體檔案遺失）
    - orphaned_details: 孤立記錄的詳細資訊
    """
    try:
        all_files = db.query(models.File).all()
        orphaned_details = []
        valid_count = 0

        for file_record in all_files:
            storage_key = file_record.storage_key
            if storage_key and os.path.exists(storage_key):
                valid_count += 1
            else:
                orphaned_details.append(
                    {
                        "id": file_record.id,
                        "filename": file_record.filename,
                        "storage_key": storage_key,
                        "created_at": file_record.created_at.isoformat()
                        if file_record.created_at
                        else None,
                    }
                )

        return {
            "total_db_records": len(all_files),
            "valid_files": valid_count,
            "orphaned_files": len(orphaned_details),
            "orphaned_details": orphaned_details,
        }

    except Exception as e:
        logger.error(f"[STATUS] 無法取得狀態: {str(e)}")
        return {
            "total_db_records": 0,
            "valid_files": 0,
            "orphaned_files": 0,
            "orphaned_details": [],
            "error": str(e),
        }


# --- 批量操作端點 (v0.2+) ---


@app.post("/files/batch-delete", status_code=status.HTTP_200_OK)
def batch_delete_files(file_ids: List[int] = None, db: Session = Depends(get_db)):
    """
    批量刪除檔案

    【功能】
    - 一次刪除多個檔案
    - 自動刪除關聯的標籤、結論、標註
    - 刪除實體檔案

    【參數】
    file_ids: 檔案 ID 列表

    【回傳】
    - deleted_count: 已刪除的檔案數
    - failed_ids: 刪除失敗的檔案 ID
    """
    if not file_ids:
        file_ids = []

    deleted_count = 0
    failed_ids = []

    try:
        for file_id in file_ids:
            try:
                file = db.query(models.File).filter(models.File.id == file_id).first()
                if not file:
                    failed_ids.append(file_id)
                    continue

                # 刪除實體檔案
                try:
                    if file.storage_key and os.path.exists(file.storage_key):
                        os.remove(file.storage_key)
                except Exception as e:
                    logger.warning(f"無法刪除實體檔案 {file.storage_key}: {e}")

                # 刪除資料庫記錄
                db.delete(file)
                deleted_count += 1

            except Exception as e:
                logger.error(f"刪除檔案 {file_id} 失敗: {e}")
                failed_ids.append(file_id)

        db.commit()
        logger.info(f"批量刪除完成: {deleted_count} 成功, {len(failed_ids)} 失敗")

        return {
            "deleted_count": deleted_count,
            "failed_ids": failed_ids,
            "status": "success" if len(failed_ids) == 0 else "partial",
        }

    except Exception as e:
        logger.error(f"批量刪除失敗: {e}")
        return {
            "deleted_count": 0,
            "failed_ids": file_ids,
            "status": "error",
            "error": str(e),
        }


@app.post("/tags/batch-create", status_code=status.HTTP_201_CREATED)
def batch_create_tags(tag_names: List[str] = None, db: Session = Depends(get_db)):
    """
    批量建立標籤

    【功能】
    - 一次建立多個標籤
    - 自動跳過已存在的標籤
    - 返回已建立和已存在的標籤列表

    【參數】
    tag_names: 標籤名稱列表

    【回傳】
    - created_count: 新建立的標籤數
    - existing_count: 已存在的標籤數
    - created_tags: 新建立的標籤
    - existing_tags: 已存在的標籤
    """
    if not tag_names:
        tag_names = []

    created_tags = []
    existing_tags = []

    try:
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if not tag_name:
                continue

            # 檢查標籤是否已存在
            existing_tag = (
                db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            )
            if existing_tag:
                existing_tags.append({"id": existing_tag.id, "name": existing_tag.name})
            else:
                # 建立新標籤
                new_tag = models.Tag(name=tag_name)
                db.add(new_tag)
                db.flush()
                created_tags.append({"id": new_tag.id, "name": new_tag.name})

        db.commit()
        logger.info(
            f"批量建立標籤完成: {len(created_tags)} 新建, {len(existing_tags)} 已存在"
        )

        return {
            "created_count": len(created_tags),
            "existing_count": len(existing_tags),
            "created_tags": created_tags,
            "existing_tags": existing_tags,
            "status": "success",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"批量建立標籤失敗: {e}")
        return {
            "created_count": 0,
            "existing_count": len(existing_tags),
            "created_tags": [],
            "existing_tags": existing_tags,
            "status": "error",
            "error": str(e),
        }


class FileBatchUploadRequest(BaseModel):
    """批量上傳請求結構"""

    pass  # 由多部分檔案表單提供


@app.post("/files/batch-upload", status_code=status.HTTP_201_CREATED)
async def batch_upload_files(
    files: List[UploadFile] = File(...), db: Session = Depends(get_db)
):
    """
    批量上傳檔案

    【功能】
    - 一次上傳多個檔案
    - 自動去重（相同內容的檔案只儲存一份）
    - 返回已上傳和已存在的檔案列表

    【參數】
    files: 檔案列表（multipart/form-data）

    【回傳】
    - uploaded_count: 新上傳的檔案數
    - duplicated_count: 重複的檔案數
    - uploaded_files: 新上傳的檔案信息
    - duplicated_files: 重複的檔案信息
    """
    uploaded_files = []
    duplicated_files = []

    try:
        for file in files:
            try:
                # 計算檔案 hash
                file_hash = await calculate_file_hash(file)

                # 檢查檔案是否已存在
                existing_file = (
                    db.query(models.File)
                    .filter(models.File.file_hash == file_hash)
                    .first()
                )

                if existing_file:
                    duplicated_files.append(
                        {
                            "id": existing_file.id,
                            "filename": existing_file.filename,
                            "file_hash": existing_file.file_hash,
                            "created_at": existing_file.created_at.isoformat()
                            if existing_file.created_at
                            else None,
                        }
                    )
                    continue

                # 儲存檔案
                await file.seek(0)
                storage_key = await storage.save(file_hash, file)

                # 建立資料庫記錄
                db_file = models.File(
                    filename=file.filename, storage_key=storage_key, file_hash=file_hash
                )
                db.add(db_file)
                db.flush()

                uploaded_files.append(
                    {
                        "id": db_file.id,
                        "filename": db_file.filename,
                        "file_hash": db_file.file_hash,
                        "created_at": db_file.created_at.isoformat()
                        if db_file.created_at
                        else None,
                    }
                )

            except Exception as e:
                logger.error(f"上傳檔案 {file.filename} 失敗: {e}")

        db.commit()
        logger.info(
            f"批量上傳完成: {len(uploaded_files)} 新上傳, {len(duplicated_files)} 重複"
        )

        return {
            "uploaded_count": len(uploaded_files),
            "duplicated_count": len(duplicated_files),
            "uploaded_files": uploaded_files,
            "duplicated_files": duplicated_files,
            "status": "success",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"批量上傳失敗: {e}")
        return {
            "uploaded_count": 0,
            "duplicated_count": len(duplicated_files),
            "uploaded_files": [],
            "duplicated_files": duplicated_files,
            "status": "error",
            "error": str(e),
        }


@app.post("/reasoning-chains", tags=["推理鏈"], status_code=status.HTTP_201_CREATED)
def create_reasoning_chain(
    chain_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """
    建立新的推理鏈

    參數:
      - name: 推理鏈名稱
      - description: 推理鏈描述
      - nodes: 節點配置陣列
    """
    try:
        service = ReasoningService(db, storage=storage)
        chain = service.create_chain(
            name=chain_data.get("name"),
            description=chain_data.get("description", ""),
            nodes=chain_data.get("nodes", []),
            created_by_id=current_user["id"],
            is_template=chain_data.get("is_template", False),
        )
        logger.info(f"建立推理鏈: {chain.id}")
        return {
            "id": str(chain.id),
            "name": chain.name,
            "description": chain.description,
            "is_template": chain.is_template,
            "created_at": chain.created_at.isoformat() if chain.created_at else None,
            "updated_at": chain.updated_at.isoformat() if chain.updated_at else None,
        }
    except Exception as e:
        logger.error(f"建立推理鏈失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reasoning-chains", tags=["推理鏈"])
def list_reasoning_chains(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """取得推理鏈列表"""
    try:
        service = ReasoningService(db, storage=storage)
        chains = service.list_chains(skip=skip, limit=limit)
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "is_template": c.is_template,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in chains
        ]
    except Exception as e:
        logger.error(f"列表推理鏈失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reasoning-chains/{chain_id}", tags=["推理鏈"])
def get_reasoning_chain(
    chain_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """取得推理鏈詳細資訊"""
    try:
        service = ReasoningService(db, storage=storage)
        chain = service.get_chain(UUID(chain_id))
        if not chain:
            raise HTTPException(status_code=404, detail="推理鏈不存在")
        return {
            "id": str(chain.id),
            "name": chain.name,
            "description": chain.description,
            "nodes": chain.nodes,
            "is_template": chain.is_template,
            "created_at": chain.created_at.isoformat() if chain.created_at else None,
            "updated_at": chain.updated_at.isoformat() if chain.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得推理鏈失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/reasoning-chains/{chain_id}", tags=["推理鏈"])
def update_reasoning_chain(
    chain_id: str,
    update_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """更新推理鏈"""
    try:
        service = ReasoningService(db, storage=storage)
        chain = service.update_chain(
            chain_id=UUID(chain_id),
            name=update_data.get("name"),
            description=update_data.get("description"),
            nodes=update_data.get("nodes"),
        )
        if not chain:
            raise HTTPException(status_code=404, detail="推理鏈不存在")
        logger.info(f"更新推理鏈: {chain_id}")
        return {
            "id": str(chain.id),
            "name": chain.name,
            "description": chain.description,
            "updated_at": chain.updated_at.isoformat() if chain.updated_at else None,
        }
    except Exception as e:
        logger.error(f"更新推理鏈失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete(
    "/reasoning-chains/{chain_id}",
    tags=["推理鏈"],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reasoning_chain(
    chain_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """刪除推理鏈"""
    try:
        service = ReasoningService(db, storage=storage)
        service.delete_chain(UUID(chain_id))
        logger.info(f"刪除推理鏈: {chain_id}")
    except Exception as e:
        logger.error(f"刪除推理鏈失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/reasoning-chains/{chain_id}/execute", tags=["推理鏈"])
def execute_reasoning_chain(
    chain_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """執行推理鏈"""
    try:
        service = ReasoningService(db, storage=storage)
        input_data = (
            payload.get("input_data")
            if isinstance(payload, dict) and "input_data" in payload
            else payload
        )
        if input_data is None:
            input_data = {}
        model_name = payload.get("model_name") if isinstance(payload, dict) else None
        tool_name = payload.get("tool_name") if isinstance(payload, dict) else None
        execution = service.execute_chain(
            UUID(chain_id),
            input_data,
            user_id=current_user["id"],
            model_name=model_name,
            tool_name=tool_name,
        )
        logger.info(f"執行推理鏈: {chain_id}, 執行ID: {execution.id}")
        return {
            "execution_id": str(execution.id),
            "chain_id": str(execution.chain_id),
            "status": execution.status,
            "user_id": execution.user_id,
            "model_name": execution.model_name,
            "tool_name": execution.tool_name,
            "started_at": execution.started_at.isoformat()
            if execution.started_at
            else None,
        }
    except Exception as e:
        logger.error(f"執行推理鏈失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/executions/{execution_id}", tags=["推理鏈"])
def get_execution_result(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """取得推理鏈執行結果"""
    try:
        service = ReasoningService(db, storage=storage)
        execution = service.get_execution(UUID(execution_id))
        if not execution:
            raise HTTPException(status_code=404, detail="執行記錄不存在")

        def normalize_json(value: Any) -> Any:
            if value is None:
                return {}
            if isinstance(value, (dict, list)):
                return value
            if isinstance(value, str):
                import json

                try:
                    return json.loads(value)
                except Exception:
                    return {}
            return {}

        def normalize_error(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, (dict, list)):
                return value
            if isinstance(value, str):
                import json

                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        results = normalize_json(execution.results)
        input_data = normalize_json(execution.input_data)

        return {
            "execution_id": str(execution.id),
            "chain_id": str(execution.chain_id),
            "status": execution.status,
            "user_id": execution.user_id,
            "model_name": execution.model_name,
            "tool_name": execution.tool_name,
            "input_data": input_data,
            "results": results,
            "error": normalize_error(execution.error_log),
            "started_at": execution.started_at.isoformat()
            if execution.started_at
            else None,
            "completed_at": execution.completed_at.isoformat()
            if execution.completed_at
            else None,
            "execution_time_ms": execution.execution_time_ms,
        }
    except Exception as e:
        logger.error(f"取得執行結果失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 腳本 (Script) 端點 - v0.3 新增
# ============================================================================


@app.post("/scripts", tags=["腳本"], status_code=status.HTTP_201_CREATED)
def create_script(
    script_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """建立新腳本"""
    try:
        service = ScriptService(db)
        script = service.create_script(
            name=script_data.get("name"),
            content=script_data.get("content"),
            category=script_data.get("category", "general"),
            parameters=script_data.get("parameters", {}),
            created_by_id=current_user["id"],
            version=script_data.get("version", "1.0.0"),
        )
        logger.info(f"建立腳本: {script.id}")
        return {
            "id": str(script.id),
            "name": script.name,
            "category": script.category,
            "created_at": script.created_at.isoformat() if script.created_at else None,
        }
    except Exception as e:
        logger.error(f"建立腳本失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/scripts", tags=["腳本"])
def list_scripts(
    skip: int = 0,
    limit: int = 10,
    category: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """取得腳本列表"""
    try:
        service = ScriptService(db)
        scripts = service.list_scripts(skip=skip, limit=limit, category=category)

        return [
            {
                "id": str(s.id),
                "name": s.name,
                "category": s.category,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scripts
        ]
    except Exception as e:
        logger.error(f"列表腳本失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/scripts/{script_id}", tags=["腳本"])
def get_script(
    script_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """取得腳本詳細資訊"""
    try:
        service = ScriptService(db)
        script = service.get_script(UUID(script_id))
        if not script:
            raise HTTPException(status_code=404, detail="腳本不存在")

        return {
            "id": str(script.id),
            "name": script.name,
            "content": script.content,
            "category": script.category,
            "version": script.version,
            "parameters": script.parameters,
            "created_at": script.created_at.isoformat() if script.created_at else None,
            "updated_at": script.updated_at.isoformat() if script.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得腳本失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/scripts/{script_id}", tags=["腳本"])
def update_script(
    script_id: str,
    update_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """更新腳本"""
    try:
        service = ScriptService(db)
        script = service.update_script(
            script_id=UUID(script_id),
            name=update_data.get("name"),
            content=update_data.get("content"),
            category=update_data.get("category"),
            parameters=update_data.get("parameters"),
            version=update_data.get("version"),
        )
        if not script:
            raise HTTPException(status_code=404, detail="腳本不存在")
        logger.info(f"更新腳本: {script_id}")
        return {
            "id": str(script.id),
            "name": script.name,
            "updated_at": script.updated_at.isoformat() if script.updated_at else None,
        }
    except Exception as e:
        logger.error(f"更新腳本失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete(
    "/scripts/{script_id}", tags=["腳本"], status_code=status.HTTP_204_NO_CONTENT
)
def delete_script(
    script_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """刪除腳本"""
    try:
        service = ScriptService(db)
        service.delete_script(UUID(script_id))
        logger.info(f"刪除腳本: {script_id}")
    except Exception as e:
        logger.error(f"刪除腳本失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/scripts/{script_id}/execute", tags=["腳本"])
def execute_script(
    script_id: str,
    input_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    """執行腳本"""
    try:
        service = ScriptService(db)
        execution = service.execute_script(UUID(script_id), input_data)
        logger.info(f"執行腳本: {script_id}, 執行ID: {execution.id}")
        return {
            "execution_id": str(execution.id),
            "script_id": str(execution.script_id),
            "status": execution.status,
            "started_at": execution.started_at.isoformat()
            if execution.started_at
            else None,
        }
    except Exception as e:
        logger.error(f"執行腳本失敗: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 檔案自動分類端點 ====================


@app.post(
    "/files/{file_id}/classify",
    response_model=schemas.FileClassificationResponse,
    tags=["檔案管理"],
)
def classify_file(
    file_id: int,
    auto_tag: bool = True,
    auto_create_tags: bool = True,
    db: Session = Depends(get_db),
):
    """
    手動觸發檔案分類

    功能：
    - 對指定檔案進行自動分類
    - 提取元數據
    - 建議標籤
    - 可選：自動創建和添加標籤

    參數：
    - file_id: 檔案ID
    - auto_tag: 是否自動添加標籤 (預設: True)
    - auto_create_tags: 是否自動創建不存在的標籤 (預設: True)

    回傳：
    - 200: 分類成功
    - 404: 檔案不存在
    - 500: 分類失敗
    """
    try:
        # 查詢檔案
        db_file = db.query(models.File).filter(models.File.id == file_id).first()
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"檔案 ID {file_id} 不存在",
            )

        # 進行分類
        classification_result = classification_service.classify_file(db_file.filename)
        logger.info(
            f"檔案分類完成: {db_file.filename} -> {classification_result.file_type} "
            f"(confidence: {classification_result.confidence:.2f})"
        )

        tags_created = []
        tags_added = []

        # 自動添加標籤
        if auto_tag and classification_result.suggested_tags:
            for tag_name in classification_result.suggested_tags:
                # 查找或創建標籤
                tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                if not tag and auto_create_tags:
                    tag = models.Tag(name=tag_name)
                    db.add(tag)
                    db.commit()
                    db.refresh(tag)
                    tags_created.append(tag_name)
                    logger.info(f"創建新標籤: {tag_name}")

                # 添加標籤到檔案（避免重複）
                if tag and tag not in db_file.tags:
                    db_file.tags.append(tag)
                    tags_added.append(tag_name)

            db.commit()
            db.refresh(db_file)
            logger.info(f"已自動添加 {len(tags_added)} 個標籤")

        # 更新或創建分類註解
        annotation = (
            db.query(models.Annotation)
            .filter(
                models.Annotation.file_id == file_id,
                models.Annotation.source == "auto_classification",
            )
            .first()
        )

        annotation_data = {
            "classification": {
                "file_type": classification_result.file_type,
                "confidence": classification_result.confidence,
                "metadata": classification_result.metadata,
            }
        }

        if annotation:
            annotation.data = annotation_data
        else:
            annotation = models.Annotation(
                file_id=file_id, data=annotation_data, source="auto_classification"
            )
            db.add(annotation)

        db.commit()
        logger.info("已更新分類註解")

        return schemas.FileClassificationResponse(
            file_id=file_id,
            filename=db_file.filename,
            classification=classification_result,
            tags_created=tags_created,
            tags_added=tags_added,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分類檔案失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分類檔案失敗: {str(e)}",
        )


@app.post(
    "/files/classify/batch",
    response_model=schemas.BatchClassificationResponse,
    tags=["檔案管理"],
)
def batch_classify_files(
    request: schemas.BatchClassificationRequest, db: Session = Depends(get_db)
):
    """
    批量分類檔案

    功能：
    - 對多個檔案進行批量分類
    - 自動添加標籤
    - 返回統計信息

    參數：
    - request: 批量分類請求（包含檔案ID列表和選項）

    回傳：
    - 200: 批量分類完成
    - 400: 請求格式錯誤
    - 500: 分類失敗
    """
    try:
        results = []
        errors = []
        successful = 0
        failed = 0

        for file_id in request.file_ids:
            try:
                # 查詢檔案
                db_file = (
                    db.query(models.File).filter(models.File.id == file_id).first()
                )
                if not db_file:
                    errors.append(
                        {"file_id": file_id, "error": f"檔案 ID {file_id} 不存在"}
                    )
                    failed += 1
                    continue

                # 進行分類
                classification_result = classification_service.classify_file(
                    db_file.filename
                )

                tags_created = []
                tags_added = []

                # 自動添加標籤
                if request.auto_tag and classification_result.suggested_tags:
                    for tag_name in classification_result.suggested_tags:
                        # 查找或創建標籤
                        tag = (
                            db.query(models.Tag)
                            .filter(models.Tag.name == tag_name)
                            .first()
                        )
                        if not tag and request.auto_create_tags:
                            tag = models.Tag(name=tag_name)
                            db.add(tag)
                            db.commit()
                            db.refresh(tag)
                            tags_created.append(tag_name)

                        # 添加標籤到檔案（避免重複）
                        if tag and tag not in db_file.tags:
                            db_file.tags.append(tag)
                            tags_added.append(tag_name)

                    db.commit()
                    db.refresh(db_file)

                # 更新或創建分類註解
                annotation = (
                    db.query(models.Annotation)
                    .filter(
                        models.Annotation.file_id == file_id,
                        models.Annotation.source == "auto_classification",
                    )
                    .first()
                )

                annotation_data = {
                    "classification": {
                        "file_type": classification_result.file_type,
                        "confidence": classification_result.confidence,
                        "metadata": classification_result.metadata,
                    }
                }

                if annotation:
                    annotation.data = annotation_data
                else:
                    annotation = models.Annotation(
                        file_id=file_id,
                        data=annotation_data,
                        source="auto_classification",
                    )
                    db.add(annotation)

                db.commit()

                results.append(
                    schemas.FileClassificationResponse(
                        file_id=file_id,
                        filename=db_file.filename,
                        classification=classification_result,
                        tags_created=tags_created,
                        tags_added=tags_added,
                    )
                )

                successful += 1
                logger.info(f"分類檔案成功: {db_file.filename} (ID: {file_id})")

            except Exception as e:
                errors.append({"file_id": file_id, "error": str(e)})
                failed += 1
                logger.error(f"分類檔案失敗 (ID: {file_id}): {str(e)}")

        return schemas.BatchClassificationResponse(
            total=len(request.file_ids),
            successful=successful,
            failed=failed,
            results=results,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量分類失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量分類失敗: {str(e)}",
        )


@app.get(
    "/classification/stats",
    response_model=schemas.ClassificationStatsResponse,
    tags=["檔案管理"],
)
def get_classification_stats(db: Session = Depends(get_db)):
    """
    獲取檔案分類統計信息

    功能：
    - 統計已分類檔案的類型分佈
    - 計算平均置信度
    - 統計未分類檔案數量

    回傳：
    - 200: 統計信息
    """
    try:
        # 查詢所有包含分類註解的檔案
        annotations = (
            db.query(models.Annotation)
            .filter(models.Annotation.source == "auto_classification")
            .all()
        )

        if not annotations:
            return schemas.ClassificationStatsResponse(
                total=0,
                by_type={},
                avg_confidence=0.0,
                unknown_count=0,
                unknown_rate=0.0,
            )

        type_counts = {}
        total_confidence = 0.0
        unknown_count = 0

        for annotation in annotations:
            classification_data = annotation.data.get("classification", {})
            file_type = classification_data.get("file_type", "Unknown")
            confidence = classification_data.get("confidence", 0.0)

            # 統計類型分佈
            type_counts[file_type] = type_counts.get(file_type, 0) + 1

            # 累計置信度
            total_confidence += confidence

            # 統計未知類型
            if file_type == "Unknown":
                unknown_count += 1

        total = len(annotations)

        return schemas.ClassificationStatsResponse(
            total=total,
            by_type=type_counts,
            avg_confidence=total_confidence / total if total > 0 else 0.0,
            unknown_count=unknown_count,
            unknown_rate=unknown_count / total if total > 0 else 0.0,
        )

    except Exception as e:
        logger.error(f"獲取統計信息失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取統計信息失敗: {str(e)}",
        )


@app.get("/classification/supported-types", tags=["檔案管理"])
def get_supported_file_types():
    """
    獲取支援的檔案類型

    回傳：
    - 200: 支援的檔案類型和對應的擴展名
    """
    try:
        supported_types = classification_service.get_supported_types()
        return {"supported_types": supported_types, "total_types": len(supported_types)}
    except Exception as e:
        logger.error(f"獲取支援類型失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取支援類型失敗: {str(e)}",
        )
