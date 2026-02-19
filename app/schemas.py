"""
Pydantic Schemas for File Management System
用途：定義 API 資料驗證與 ORM 物件轉換的 Schema
結構：Base（共用欄位） → Create（新增驗證） → Response（含 ID/時間戳）
實體：Tag（標籤）、Conclusion（結論）、Annotation（標註）、File（檔案 + 關聯）
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ==================== User（用戶）====================
class UserBase(BaseModel):
    """用戶基礎欄位"""
    username: str = Field(..., min_length=3, max_length=50, description="用戶名稱")
    email: Optional[str] = Field(None, description="電子郵件")

class UserCreate(UserBase):
    """新增用戶時的驗證 Schema"""
    password: str = Field(..., min_length=6, description="密碼")

class UserUpdate(BaseModel):
    """更新用戶時的驗證 Schema"""
    email: Optional[str] = None
    role: Optional[str] = Field(None, description="角色 (admin/editor/viewer)")

class UserResponse(UserBase):
    """用戶回傳 Schema"""
    id: int
    role: str = Field(..., description="用戶角色")
    is_active: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }

class UserLogin(BaseModel):
    """用戶登錄請求"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """令牌回應"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# ==================== Tag（標籤）====================
class TagBase(BaseModel):
    """標籤基礎欄位"""
    name: str = Field(..., min_length=1, max_length=100, description="標籤名稱")

class TagCreate(TagBase):
    """新增標籤時的驗證 Schema"""
    pass

class Tag(TagBase):
    """標籤回傳 Schema（含 ID）"""
    id: int
    
    model_config = {
        "from_attributes": True
    }

# ==================== Conclusion（結論）====================
class ConclusionBase(BaseModel):
    """結論基礎欄位"""
    content: str = Field(..., min_length=1, description="結論內容")

class ConclusionCreate(ConclusionBase):
    """新增結論時的驗證 Schema"""
    pass

class Conclusion(ConclusionBase):
    """結論回傳 Schema（含 ID 與時間戳）"""
    id: int
    file_id: int = Field(..., description="關聯的檔案 ID")
    created_at: datetime = Field(..., description="建立時間")
    
    model_config = {
        "from_attributes": True
    }

# ==================== Annotation（標註）====================
class AnnotationBase(BaseModel):
    """標註基礎欄位"""
    data: Dict[str, Any] = Field(..., description="標註內容 (JSON 格式)")
    source: str = Field(default="manual", description="標註來源 (manual/auto/imported)")

class AnnotationCreate(AnnotationBase):
    """新增標註時的驗證 Schema"""
    pass

class Annotation(AnnotationBase):
    """標註回傳 Schema（含 ID 與時間戳）"""
    id: int
    file_id: int = Field(..., description="關聯的檔案 ID")
    created_at: datetime = Field(..., description="建立時間")
    
    model_config = {
        "from_attributes": True
    }

# ==================== File（檔案）====================
class FileBase(BaseModel):
    """檔案基礎欄位"""
    filename: str = Field(..., min_length=1, description="檔案名稱")

class FileCreate(FileBase):
    """新增檔案時的驗證 Schema（Phase 3 前為模擬）"""
    storage_key: str = Field(..., description="儲存路徑/雲端 key")
    file_hash: str = Field(..., description="檔案雜湊值（去重用）")

class File(FileBase):
    """檔案回傳 Schema（含關聯的標籤與結論）"""
    id: int
    storage_key: str = Field(..., description="儲存路徑")
    file_hash: str = Field(..., description="檔案 SHA256 雜湊值")
    created_at: datetime = Field(..., description="建立時間")
    tags: List[Tag] = Field(default_factory=list, description="關聯的標籤")
    conclusions: List[Conclusion] = Field(default_factory=list, description="關聯的結論")
    annotations: List[Annotation] = Field(default_factory=list, description="關聯的標註")

    model_config = {
        "from_attributes": True
    }

# ==================== Analysis (External Tools) ====================
class AnalysisToolSpec(BaseModel):
    id: str
    name: str
    version: str
    description: str
    input_types: List[str]
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)


class AnalysisRunRequest(BaseModel):
    tool_id: str
    file_id: int
    parameters: Dict[str, Any] = Field(default_factory=dict)
    store_output: bool = True


class AnalysisStored(BaseModel):
    conclusion_id: Optional[int] = None
    annotation_ids: List[int] = Field(default_factory=list)


class AnalysisRunResponse(BaseModel):
    status: str
    output: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    stored: AnalysisStored

# ==================== Reasoning (v0.3 Phase 1) ====================
class ReasoningNodeConfig(BaseModel):
    node_id: str = Field(..., description="Node ID")
    node_type: str = Field(..., description="Node type")
    name: Optional[str] = Field(None, description="Node name")
    inputs: List[str] = Field(default_factory=list, description="Upstream node IDs")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node config payload")

    model_config = {
        "extra": "allow",
    }


class ReasoningChainCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Chain name")
    description: Optional[str] = Field("", description="Chain description")
    nodes: List[ReasoningNodeConfig] = Field(default_factory=list, description="Chain nodes")
    is_template: bool = Field(False, description="Template chain")


class ReasoningChainUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    nodes: Optional[List[ReasoningNodeConfig]] = Field(None, description="Chain nodes")
    is_template: Optional[bool] = Field(None, description="Template chain")


class ReasoningChainResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_template: bool
    created_at: Optional[str]
    updated_at: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None


class ReasoningExecuteRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    model_name: Optional[str] = None
    tool_name: Optional[str] = None


class ReasoningExecutionSummary(BaseModel):
    execution_id: str
    chain_id: str
    status: str
    user_id: Optional[int] = None
    model_name: Optional[str] = None
    tool_name: Optional[str] = None
    started_at: Optional[str] = None


class ReasoningExecutionDetail(ReasoningExecutionSummary):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Any] = None
    completed_at: Optional[str] = None
    execution_time_ms: Optional[float] = None


class ReasoningChainHistory(BaseModel):
    chain_id: str
    period_days: int
    total_executions: int
    completed: int
    failed: int
    success_rate: float
    avg_execution_time_ms: float

# ==================== File Classification（檔案自動分類）====================
class ClassificationResult(BaseModel):
    """檔案分類結果"""
    file_type: str = Field(..., description="檔案類型 (XRD, SEM, EIS, CV, Excel, Image, Data, Unknown)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 (0.0-1.0)")
    suggested_tags: List[str] = Field(default_factory=list, description="建議的標籤")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="提取的元數據 (sample, date, instrument等)")
    source: str = Field(default="auto", description="分類來源 (auto/manual)")

class FileClassificationResponse(BaseModel):
    """檔案分類響應"""
    file_id: int
    filename: str
    classification: ClassificationResult
    tags_created: List[str] = Field(default_factory=list, description="自動創建的標籤")
    tags_added: List[str] = Field(default_factory=list, description="已添加的標籤")

class BatchClassificationRequest(BaseModel):
    """批量分類請求"""
    file_ids: List[int] = Field(..., min_items=1, description="需要分類的檔案ID列表")
    auto_tag: bool = Field(default=True, description="是否自動添加標籤")
    auto_create_tags: bool = Field(default=True, description="是否自動創建不存在的標籤")

class BatchClassificationResponse(BaseModel):
    """批量分類響應"""
    total: int
    successful: int
    failed: int
    results: List[FileClassificationResponse]
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="錯誤信息")

class ClassificationStatsResponse(BaseModel):
    """分類統計響應"""
    total: int
    by_type: Dict[str, int]
    avg_confidence: float
    unknown_count: int
    unknown_rate: float
