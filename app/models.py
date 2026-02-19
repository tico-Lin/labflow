"""
=============================================================================
研究資料管理系統 - ORM 模型定義
=============================================================================
目的：
  建立實驗檔案（XRD/SEM/電化學數據等）的結構化儲存與標註系統

核心功能：
  1. 檔案管理 (File)：
     - 支援檔案指紋去重 (SHA256)
     - 儲存路徑抽象化（本地/雲端相容）
  
  2. 標籤系統 (Tag)：
     - 多對多關係，支援分類（如 "XRD", "Cr-doped", "beta-MnO2"）
  
  3. 結論記錄 (Conclusion)：
     - 儲存分析結論、實驗筆記（支援 Markdown 長文字）
  
  4. 標註資料 (Annotation)：
     - JSON 格式儲存結構化資訊
     - 範例：{"cr_content": 3, "structure": "beta", "lattice_a": 9.785}
     - 支援多來源標註（手動/AI 模型/外部工具）

資料庫關係：
  File 1--N Conclusion  (一個檔案可有多筆結論)
  File 1--N Annotation  (一個檔案可有多筆標註)
  File N--N Tag         (檔案與標籤多對多)

技術棧：
  - SQLAlchemy ORM
  - 支援 SQLite/PostgreSQL 等多種後端
  
作者：忘憂
最後更新：2026-01-07
=============================================================================
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, JSON, CheckConstraint, Enum, Index, Float
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from .database import Base
import enum
from sqlalchemy_utils import UUIDType
import uuid

# =============================================================================
# 角色枚舉 (Role Enum)
# =============================================================================
class RoleEnum(str, enum.Enum):
    """用戶角色枚舉"""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

# =============================================================================
# 關聯表：檔案與標籤的多對多關係
# =============================================================================
file_tags = Table(
    "file_tags",
    Base.metadata,
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

# =============================================================================
# 檔案表 (File)
# =============================================================================
class File(Base):
    """
    核心檔案元資料表
    
    欄位說明：
      - filename: 原始檔名（必填，長度 1-255 字元）
      - storage_key: 儲存路徑標識符（必填，唯一）
      - file_hash: SHA256 指紋，用於檔案去重（必填，唯一）
    
    驗證約束：
      - 檔案名稱和 hash 不能為空字串
      - file_hash 應為 64 字元的十六進位字串
    
    關聯：
      - tags: 多對多標籤
      - conclusions: 一對多結論
      - annotations: 一對多標註
    """
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    
    # 儲存路徑標識符 (Storage Key)，未來對應到本地路徑或 S3 Key
    storage_key = Column(String, unique=True, nullable=False, index=True)
    
    # 檔案指紋，用於去重 (SHA256) - 64 個十六進位字符
    file_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # 關聯
    tags = relationship("Tag", secondary=file_tags, back_populates="files")
    conclusions = relationship("Conclusion", back_populates="file", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="file", cascade="all, delete-orphan")
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_file_created_at', 'created_at'),
        Index('idx_file_hash_created', 'file_hash', 'created_at'),
    )
    
    # 驗證方法
    @validates('filename')
    def validate_filename(self, key, value):
        """驗證檔案名稱"""
        if not value or not value.strip():
            raise ValueError("檔案名稱不能為空")
        if len(value) > 255:
            raise ValueError("檔案名稱長度不能超過 255 字元")
        return value.strip()
    
    @validates('file_hash')
    def validate_file_hash(self, key, value):
        """驗證檔案 hash"""
        if not value or len(value) != 64:
            raise ValueError("檔案 hash 必須是 64 字元的 SHA256 雜湊值")
        return value.lower()
    
    def __repr__(self):
        return f"<File(id={self.id}, filename={self.filename}, hash={self.file_hash[:16]}...)>"

# =============================================================================
# 標籤表 (Tag)
# =============================================================================
class Tag(Base):
    """
    標籤分類表
    
    特性：
      - 標籤名稱唯一（unique=True）
      - 支援多對多關聯檔案
    
    使用範例：
      "XRD", "SEM", "Cr-doped", "beta-MnO2", "cycle-test"
    """
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # 標籤名稱不可重複，長度限制

    # 關聯
    files = relationship("File", secondary=file_tags, back_populates="tags")

    @validates('name')
    def validate_name(self, key, value):
      if not value or not value.strip():
        raise ValueError("標籤名稱不能為空")
      if len(value.strip()) > 100:
        raise ValueError("標籤名稱長度不能超過 100 字元")
      return value.strip()

# =============================================================================
# 結論表 (Conclusion)
# =============================================================================
class Conclusion(Base):
    """
    分析結論記錄表
    
    用途：
      - 儲存對檔案的分析結論、實驗筆記
      - 支援 Markdown 格式長文字
    
    未來擴充：
      - content 可改為 JSON，儲存結構化推理鏈結果
    """
    __tablename__ = "conclusions"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # 關聯
    file = relationship("File", back_populates="conclusions")
    
    # 性能優化：索引查詢
    __table_args__ = (
        Index('idx_conclusion_file_created', 'file_id', 'created_at'),
    )

    @validates('content')
    def validate_content(self, key, value):
      if not value or not value.strip():
        raise ValueError("結論內容不能為空")
      return value.strip()

# =============================================================================
# 標註表 (Annotation)
# =============================================================================
class Annotation(Base):
    """
    結構化標註資料表
    
    核心特性：
      - data 欄位為 JSON 格式，彈性儲存各類標註
      - source 欄位記錄標註來源（手動/AI/外部工具）
    
    JSON 範例：
      材料參數：{"cr_content": 3, "structure": "beta", "lattice_a": 9.785}
      影像標註：{"bbox": [10, 20, 100, 100], "label": "crack"}
      電化學：{"rate_capability": 85.3, "cycle_number": 1000}
    
    來源標記範例：
      - "manual": 手動標註
      - "ai_model_v1": AI 模型自動標註
      - "label_studio": 外部標註工具匯入
    """
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), index=True)
    
    # JSON 格式儲存結構化標註
    data = Column(JSON, nullable=False)
    
    # 記錄標註來源
    source = Column(String(50), default="manual", nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # 關聯
    file = relationship("File", back_populates="annotations")
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_annotation_file_source', 'file_id', 'source'),
        Index('idx_annotation_created', 'created_at'),
    )

    @validates('source')
    def validate_source(self, key, value):
      allowed = {"manual", "ai_model_v1", "label_studio", "auto", "imported"}
      v = (value or "manual").strip()
      if v not in allowed:
        raise ValueError(f"標註來源必須為 {allowed} 之一")
      return v

# =============================================================================
# 用戶表 (User)
# =============================================================================
class User(Base):
    """
    用戶帳號表
    
    欄位說明：
      - username: 用戶名稱（唯一，長度 3-50）
      - email: 電子郵件（可選，唯一）
      - hashed_password: 雜湊密碼
      - role: 用戶角色（admin/editor/viewer）
      - is_active: 帳號是否啟用
    
    角色說明：
      - admin: 管理員，可建立/刪除用戶、設置角色
      - editor: 編輯者，可上傳檔案、標籤、註解
      - viewer: 瀏覽者，只讀檔案和標籤
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=RoleEnum.VIEWER, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)  # SQLite 用 0/1 代表 False/True
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    @validates('username')
    def validate_username(self, key, value):
        if not value or not value.strip():
            raise ValueError("用戶名稱不能為空")
        value = value.strip()
        if len(value) < 3 or len(value) > 50:
            raise ValueError("用戶名稱長度必須在 3-50 字元之間")
        return value
    
    @validates('role')
    def validate_role(self, key, value):
        allowed = {RoleEnum.ADMIN, RoleEnum.EDITOR, RoleEnum.VIEWER}
        if value not in allowed:
            raise ValueError(f"角色必須為 {allowed} 之一")
        return value
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

# =============================================================================
# 審計日誌表 (Audit Log)
# =============================================================================
class AuditLog(Base):
    """
    審計日誌表
    
    用途：記錄用戶對系統的操作
    
    欄位說明：
      - user_id: 執行操作的用戶 ID
      - action: 操作類型（create, update, delete, download）
      - resource_type: 資源類型（file, tag, user）
      - resource_id: 資源 ID
      - details: 操作詳情（JSON）
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(Integer)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_audit_user_created', 'user_id', 'created_at'),
        Index('idx_audit_action_resource', 'action', 'resource_type'),
    )
    
    def __repr__(self):
        return f"<AuditLog(user_id={self.user_id}, action={self.action}, resource_type={self.resource_type})>"


# =============================================================================
# 推理鏈表 (ReasoningChain) - v0.3 新增
# =============================================================================
class ReasoningChain(Base):
    """
    推理鏈定義表
    
    用途：
      - 儲存推理鏈的定義（名稱、描述、節點配置）
      - 支援版本管理和執行歷史追蹤
    
    欄位說明：
      - id: 推理鏈的唯一識別符（UUID）
      - name: 推理鏈名稱
      - description: 推理鏈描述
      - nodes: JSONB 格式存儲的節點配置陣列
        格式範例：
        [
          {"id": "node_1", "type": "DATA_INPUT", "config": {"file_type": "xrd"}},
          {"id": "node_2", "type": "CALCULATE", "config": {"algorithm": "phase_purity"}, "inputs": ["node_1"]},
          {"id": "node_3", "type": "OUTPUT", "config": {"format": "json"}, "inputs": ["node_2"]}
        ]
      - is_template: 是否為模板鏈（預定義的常用推理流程）
      - created_by_id: 建立者用戶 ID
      - created_at: 建立時間
      - updated_at: 最後更新時間
    
    關聯：
      - executions: 一對多執行記錄
      - created_by: 指向 User 表的建立者
    """
    __tablename__ = "reasoning_chains"
    
    id = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    nodes = Column(JSON, nullable=False)  # JSONB 存儲節點配置
    is_template = Column(Integer, default=0, nullable=False)  # 0 = False, 1 = True
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 關聯
    executions = relationship("ReasoningExecution", back_populates="chain", cascade="all, delete-orphan")
    node_items = relationship("ReasoningNode", back_populates="chain", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_reasoning_chain_name', 'name'),
        Index('idx_reasoning_chain_template', 'is_template'),
        Index('idx_reasoning_chain_created', 'created_at'),
    )
    
    @validates('name')
    def validate_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("推理鏈名稱不能為空")
        if len(value.strip()) > 255:
            raise ValueError("推理鏈名稱長度不能超過 255 字元")
        return value.strip()
    
    @validates('nodes')
    def validate_nodes(self, key, value):
        if not isinstance(value, list):
            raise ValueError("節點配置必須是陣列")
        if len(value) == 0:
            raise ValueError("推理鏈至少需要一個節點")
        return value
    
    def __repr__(self):
        return f"<ReasoningChain(id={self.id}, name={self.name}, nodes_count={len(self.nodes)})>"


# =============================================================================
# 推理節點表 (ReasoningNode) - v0.3 新增
# =============================================================================
class ReasoningNode(Base):
    """
    推理節點定義表
    
    用途：
      - 將推理鏈的節點拆分為可查詢的結構化資料
      - 支援節點級別的查詢與管理
    
    欄位說明：
      - id: 節點的唯一識別符（UUID）
      - chain_id: 所屬推理鏈 ID
      - node_id: 節點在鏈中的唯一 ID
      - node_type: 節點類型
      - name: 節點名稱
      - config: 節點配置（JSON）
      - inputs: 輸入節點 ID 列表（JSON）
      - outputs: 輸出定義（JSON）
      - position: 佈局位置（JSON）
      - created_at: 建立時間
      - updated_at: 更新時間
    
    關聯：
      - chain: 指向 ReasoningChain 表
    """
    __tablename__ = "reasoning_nodes"
    
    id = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    chain_id = Column(UUIDType(binary=False), ForeignKey("reasoning_chains.id"), nullable=False, index=True)
    node_id = Column(String(128), nullable=False, index=True)
    node_type = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=True)
    inputs = Column(JSON, nullable=True)
    outputs = Column(JSON, nullable=True)
    position = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 關聯
    chain = relationship("ReasoningChain", back_populates="node_items")
    
    # 性能優化：複合索引
    __table_args__ = (
      Index('idx_reasoning_node_chain_node', 'chain_id', 'node_id'),
      Index('idx_reasoning_node_chain_type', 'chain_id', 'node_type'),
    )
    
    @validates('node_id')
    def validate_node_id(self, key, value):
      if not value or not value.strip():
        raise ValueError("節點 ID 不能為空")
      if len(value.strip()) > 128:
        raise ValueError("節點 ID 長度不能超過 128 字元")
      return value.strip()
    
    @validates('node_type')
    def validate_node_type(self, key, value):
      if not value or not value.strip():
        raise ValueError("節點類型不能為空")
      if len(value.strip()) > 50:
        raise ValueError("節點類型長度不能超過 50 字元")
      return value.strip()
    
    @validates('name')
    def validate_name(self, key, value):
      if not value or not value.strip():
        raise ValueError("節點名稱不能為空")
      if len(value.strip()) > 255:
        raise ValueError("節點名稱長度不能超過 255 字元")
      return value.strip()
    
    def __repr__(self):
      return f"<ReasoningNode(id={self.id}, chain_id={self.chain_id}, node_id={self.node_id}, type={self.node_type})>"


# =============================================================================
# 推理執行表 (ReasoningExecution) - v0.3 新增
# =============================================================================
class ReasoningExecution(Base):
    """
    推理鏈執行記錄表
    
    用途：
      - 記錄每次推理鏈的執行過程、結果和錯誤信息
      - 支援執行歷史查詢和性能分析
    
    欄位說明：
      - id: 執行記錄的唯一識別符（UUID）
      - chain_id: 關聯的推理鏈 ID
      - user_id: 執行者用戶 ID
      - model_name: 使用的模型名稱（可選）
      - tool_name: 使用的工具名稱（可選）
      - status: 執行狀態（running/completed/failed）
      - input_data: JSONB 格式的輸入參數
      - results: JSONB 格式的執行結果
        格式範例：
        {
          "node_1": {"file": {...}},
          "node_2": {"phase_purity": 95.2},
          "node_3": {"output": {...}}
        }
      - error_log: 錯誤日誌（如果執行失敗）
      - started_at: 開始時間
      - completed_at: 完成時間（失敗時也會記錄）
      - execution_time_ms: 執行耗時（毫秒）
    
    關聯：
      - chain: 指向 ReasoningChain 表
    """
    __tablename__ = "reasoning_executions"
    
    id = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    chain_id = Column(UUIDType(binary=False), ForeignKey("reasoning_chains.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    model_name = Column(String(100), nullable=True, index=True)
    tool_name = Column(String(100), nullable=True, index=True)
    status = Column(String(50), default="running", nullable=False, index=True)  # running/completed/failed
    input_data = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_ms = Column(Float, nullable=True)  # 執行耗時（毫秒）
    
    # 關聯
    chain = relationship("ReasoningChain", back_populates="executions")
    executed_by = relationship("User", foreign_keys=[user_id])
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_execution_chain_status', 'chain_id', 'status'),
        Index('idx_execution_started', 'started_at'),
        Index('idx_execution_status', 'status'),
      Index('idx_execution_user_started', 'user_id', 'started_at'),
    )
    
    @validates('status')
    def validate_status(self, key, value):
        allowed = {'running', 'completed', 'failed'}
        if value not in allowed:
            raise ValueError(f"執行狀態必須為 {allowed} 之一")
        return value
    
    def __repr__(self):
        return f"<ReasoningExecution(id={self.id}, chain_id={self.chain_id}, status={self.status})>"


# =============================================================================
# 腳本表 (Script) - v0.3 新增
# =============================================================================
class Script(Base):
    """
    可執行腳本庫表
    
    用途：
      - 儲存可在推理節點中執行的 Python 腳本
      - 支援版本管理和參數定義
    
    欄位說明：
      - id: 腳本的唯一識別符（UUID）
      - name: 腳本名稱
      - content: 腳本代碼內容
      - parameters: JSONB 格式的參數定義
        格式範例：
        {
          "parameters": [
            {"name": "sample_id", "type": "string", "required": true},
            {"name": "temperature", "type": "float", "required": false, "default": 25.0}
          ]
        }
      - category: 腳本分類（custom/builtin/analysis/transform）
      - version: 版本號
      - created_by_id: 建立者用戶 ID
      - created_at: 建立時間
      - updated_at: 最後更新時間
    
    關聯：
      - executions: 一對多腳本執行記錄
      - created_by: 指向 User 表的建立者
    """
    __tablename__ = "scripts"
    
    id = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)
    category = Column(String(50), default="custom", nullable=False, index=True)
    version = Column(String(20), default="1.0.0", nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 關聯
    executions = relationship("ScriptExecution", back_populates="script", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_script_name', 'name'),
        Index('idx_script_category', 'category'),
        Index('idx_script_created', 'created_at'),
    )
    
    @validates('name')
    def validate_name(self, key, value):
        if not value or not value.strip():
            raise ValueError("腳本名稱不能為空")
        if len(value.strip()) > 255:
            raise ValueError("腳本名稱長度不能超過 255 字元")
        return value.strip()
    
    def __repr__(self):
        return f"<Script(id={self.id}, name={self.name}, version={self.version})>"


# =============================================================================
# 腳本執行記錄表 (ScriptExecution) - v0.3 新增
# =============================================================================
class ScriptExecution(Base):
    """
    腳本執行記錄表
    
    用途：
      - 記錄每次腳本的執行過程、參數和結果
    
    欄位說明：
      - id: 執行記錄的唯一識別符（UUID）
      - script_id: 關聯的腳本 ID
      - status: 執行狀態（running/completed/failed）
      - input_params: JSONB 格式的輸入參數
      - result: JSONB 格式的執行結果
      - error: 錯誤信息（如果失敗）
      - started_at: 開始時間
      - completed_at: 完成時間
      - execution_time_ms: 執行耗時（毫秒）
    
    關聯：
      - script: 指向 Script 表
    """
    __tablename__ = "script_executions"
    
    id = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    script_id = Column(UUIDType(binary=False), ForeignKey("scripts.id"), nullable=False, index=True)
    status = Column(String(50), default="running", nullable=False, index=True)
    input_params = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    
    # 關聯
    script = relationship("Script", back_populates="executions")
    
    # 性能優化：複合索引
    __table_args__ = (
        Index('idx_script_exec_script_status', 'script_id', 'status'),
        Index('idx_script_exec_started', 'started_at'),
    )
    
    @validates('status')
    def validate_status(self, key, value):
        allowed = {'running', 'completed', 'failed'}
        if value not in allowed:
            raise ValueError(f"執行狀態必須為 {allowed} 之一")
        return value
    
    def __repr__(self):
        return f"<ScriptExecution(id={self.id}, script_id={self.script_id}, status={self.status})>"

