"""
資料庫查詢優化工具

【功能】
提供分頁、預加載、優化查詢等工具

【工具】
- PaginationParams: 分頁參數模型
- optimize_file_query: 最佳化檔案查詢
- paginate: 分頁查詢工具
"""

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import desc, func
from typing import List, Tuple, Optional, Any, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PaginationParams(BaseModel):
    """分頁參數"""
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁筆數")
    sort_by: Optional[str] = Field(default=None, description="排序欄位")
    order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="排序順序")
    
    def get_offset(self) -> int:
        """取得查詢偏移量"""
        return (self.page - 1) * self.page_size
    
    def get_limit(self) -> int:
        """取得查詢限制"""
        return self.page_size


class PaginationResult(BaseModel):
    """分頁結果"""
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


def paginate(
    query,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    order: str = "desc"
) -> Tuple[List[T], int]:
    """
    分頁查詢
    
    參數：
        query: SQLAlchemy 查詢對象
        page: 頁碼（從 1 開始）
        page_size: 每頁筆數
        sort_by: 排序欄位名稱
        order: 排序順序 (asc/desc)
    
    返回：
        (資料列表, 總筆數)
    """
    # 取得總筆數
    total = query.count()
    
    # 排序
    if sort_by:
        froms = query.statement.get_final_froms()
        if froms and hasattr(froms[0].c, sort_by):
            sort_column = getattr(froms[0].c, sort_by)
        else:
            sort_column = None
    else:
        sort_column = None
    if sort_column is not None:
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
    
    # 分頁
    offset = (page - 1) * page_size
    data = query.limit(page_size).offset(offset).all()
    
    return data, total


def optimize_file_query(db: Session, with_relations: bool = True):
    """
    最佳化檔案查詢
    
    使用關聯預加載 (joinedload/selectinload) 減少資料庫往返
    """
    from .models import File
    
    query = db.query(File)
    
    if with_relations:
        # 使用 selectinload 預加載關聯
        # selectinload 更適合一對多和多對多關係
        query = query.options(
            selectinload(File.tags),
            selectinload(File.conclusions),
            selectinload(File.annotations)
        )
    
    return query


def optimize_user_query(db: Session):
    """最佳化使用者查詢"""
    from .models import User
    return db.query(User)


def get_files_with_pagination(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    order: str = "desc"
) -> PaginationResult:
    """
    取得檔案列表（含分頁）
    
    使用範例：
    ```python
    result = get_files_with_pagination(db, page=1, page_size=10)
    for file in result.data:
        print(file.filename)
    ```
    """
    query = optimize_file_query(db)
    
    # 應用排序
    from .models import File
    if sort_by == "created_at":
        if order == "desc":
            query = query.order_by(desc(File.created_at))
        else:
            query = query.order_by(File.created_at)
    elif sort_by == "filename":
        if order == "desc":
            query = query.order_by(desc(File.filename))
        else:
            query = query.order_by(File.filename)
    
    # 應用分頁
    total = query.count()
    offset = (page - 1) * page_size
    data = query.limit(page_size).offset(offset).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return PaginationResult(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


def get_file_by_id(db: Session, file_id: int):
    """
    根據 ID 取得檔案（含所有關聯）
    
    預加載：tags, conclusions, annotations
    """
    from .models import File
    return optimize_file_query(db).filter(File.id == file_id).first()


def bulk_get_files(db: Session, file_ids: List[int]):
    """
    批量取得檔案
    
    避免 N+1 查詢問題
    """
    from .models import File
    return optimize_file_query(db).filter(File.id.in_(file_ids)).all()


class QueryStats:
    """查詢統計"""
    _query_count = 0
    _total_time = 0.0
    
    @classmethod
    def reset(cls):
        """重設統計"""
        cls._query_count = 0
        cls._total_time = 0.0
    
    @classmethod
    def get_stats(cls) -> dict:
        """取得統計信息"""
        return {
            "query_count": cls._query_count,
            "total_time": cls._total_time,
            "avg_time": cls._total_time / cls._query_count if cls._query_count > 0 else 0
        }
