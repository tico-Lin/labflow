"""
標註系統抽象層 (Annotation Provider Abstraction Layer)

【功能】
提供標註資料的統一存取介面，支援多種後端實作（本地 SQLite / 第三方標註平台）

【設計模式】
- 策略模式 (Strategy Pattern)：透過抽象基類定義標準介面
- 依賴反轉原則 (DIP)：上層邏輯依賴抽象介面，不依賴具體實作

【架構層級】
BaseAnnotationProvider (抽象介面)
    ├─ LocalAnnotationProvider (本地 SQLite 實作)
    └─ LabelStudioProvider (未來擴充：第三方標註平台)

【核心方法】
- add_annotation(): 新增標註資料
- get_annotations(): 查詢檔案的所有標註

【使用情境】
當需要切換標註後端（例如從本地改用雲端標註服務）時，
只需替換 Provider 實作，無需修改業務邏輯層程式碼。

【版本】v1.0
【最後更新】2025/01/07
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from . import models

# --- 1. 定義標準介面 (合約) ---
class BaseAnnotationProvider(ABC):
    """
    標註供應商抽象基類
    
    所有標註後端（本地 / 雲端）必須繼承此類並實作所有抽象方法
    """
    
    @abstractmethod
    def add_annotation(self, db: Session, file_id: int, data: Dict[str, Any], source: str) -> models.Annotation:
        """
        新增一筆標註
        
        Args:
            db: 資料庫 Session
            file_id: 關聯的檔案 ID
            data: 標註內容（JSON 格式）
            source: 標註來源（manual/auto/imported）
            
        Returns:
            models.Annotation: 已建立的標註物件
        """
        pass

    @abstractmethod
    def get_annotations(self, db: Session, file_id: int) -> List[models.Annotation]:
        """
        取得檔案的所有標註
        
        Args:
            db: 資料庫 Session
            file_id: 檔案 ID
            
        Returns:
            List[models.Annotation]: 標註列表
        """
        pass

# --- 2. 實作本地供應商 (存到 SQLite) ---
class LocalAnnotationProvider(BaseAnnotationProvider):
    """
    本地標註供應商
    
    將標註資料直接存入本地 SQLite 資料庫
    適用於單機版或不需要協作標註的情境
    """
    
    def add_annotation(self, db: Session, file_id: int, data: Dict[str, Any], source: str = "manual") -> models.Annotation:
        """新增標註至本地資料庫"""
        db_annotation = models.Annotation(
            file_id=file_id,
            data=data,
            source=source
        )
        db.add(db_annotation)
        db.commit()
        db.refresh(db_annotation)
        return db_annotation

    def get_annotations(self, db: Session, file_id: int) -> List[models.Annotation]:
        """從本地資料庫查詢標註"""
        return db.query(models.Annotation).filter(models.Annotation.file_id == file_id).all()


