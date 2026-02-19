"""
節點類型定義和數據類

定義了推理鏈中所有可用的節點類型，以及節點的數據結構。

支持的節點類型：
  - DATA_INPUT: 數據輸入（選擇檔案或手動輸入）
  - TRANSFORM: 數據轉換（平滑、單位轉換等）
  - CALCULATE: 計算（峰位擬合、阻抗分析等）
  - CONDITION: 條件判斷（if-else 邏輯）
  - OUTPUT: 輸出（生成圖表、寫入結論等）

作者：LabFlow Team
日期：2026-02-14
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


class NodeType(str, Enum):
    """節點類型枚舉"""
    DATA_INPUT = "data_input"      # 數據輸入
    TRANSFORM = "transform"        # 數據轉換
    CALCULATE = "calculate"        # 計算
    CONDITION = "condition"        # 條件判斷
    OUTPUT = "output"              # 輸出


class NodeStatus(str, Enum):
    """節點執行狀態枚舉"""
    PENDING = "pending"            # 等待中
    RUNNING = "running"            # 執行中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 執行失敗
    SKIPPED = "skipped"            # 被跳過（例如條件不符）


@dataclass
class NodeInput:
    """節點輸入配置"""
    source_node_id: str           # 源節點 ID
    output_key: Optional[str] = None  # 源節點的輸出鍵（如果為 None，使用全部輸出）


@dataclass
class NodeOutput:
    """節點輸出定義"""
    key: str                      # 輸出鍵名
    type: str = "any"             # 輸出數據類型（any/string/number/array/object）
    description: Optional[str] = None  # 輸出描述


@dataclass
class NodeConfig:
    """
    節點配置類
    
    表示推理鏈中的一個節點。
    
    屬性：
      - node_id: 在鏈中的唯一 ID
      - node_type: 節點類型
      - name: 節點名稱（用於展示）
      - description: 節點描述
      - config: 節點特定配置（JSON 格式，由各節點類型自行解釋）
      - inputs: 輸入節點列表
      - outputs: 輸出定義列表
      - timeout: 節點執行超時時間（秒）
      - retry_count: 失敗重試次數
    """
    node_id: str
    node_type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_backoff_factor: float = 1.0
    description: Optional[str] = None
    
    def __post_init__(self):
        """驗證節點配置"""
        if not self.node_id:
            raise ValueError("節點 ID 不能為空")
        if not self.name:
            raise ValueError("節點名稱不能為空")
        if self.timeout <= 0:
            raise ValueError("節點超時必須大於 0")
        if self.retry_count < 0:
            raise ValueError("重試次數不能為負數")
        if self.retry_delay_seconds < 0:
            raise ValueError("重試延遲不能為負數")
        if self.retry_backoff_factor < 1:
            raise ValueError("重試退避係數必須 >= 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式（用於序列化）"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "retry_backoff_factor": self.retry_backoff_factor,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConfig":
        """從字典格式建立 NodeConfig（用於反序列化）"""
        raw_type = data.get("node_type", "data_input")
        if isinstance(raw_type, NodeType):
            data["node_type"] = raw_type
        else:
            data["node_type"] = NodeType(str(raw_type).lower())
        return cls(**data)


@dataclass
class NodeResult:
    """節點執行結果"""
    node_id: str
    status: NodeStatus
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    
    def __post_init__(self):
        """計算執行耗時"""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = delta.total_seconds() * 1000


@dataclass
class ReasoningNode:
    """推理鏈節點（包含配置與執行狀態）"""
    config: NodeConfig
    status: NodeStatus = NodeStatus.PENDING
    last_result: Optional[NodeResult] = None

    @property
    def node_id(self) -> str:
        return self.config.node_id

    @property
    def node_type(self) -> NodeType:
        return self.config.node_type

    @property
    def inputs(self) -> List[Any]:
        return self.config.inputs

    def to_dict(self) -> Dict[str, Any]:
        return self.config.to_dict()


# ============================================================================
# 節點類型特定配置結構
# ============================================================================

@dataclass
class DataInputNodeConfig:
    """
    數據輸入節點配置
    
    屬性：
      - node_id: 節點 ID
      - node_type: 節點類型
      - name: 節點名稱
      - config: 節點配置 (source_type, key_path, etc.)
      - inputs: 輸入列表
      - outputs: 輸出列表
      - timeout: 超時時間
      - retry_count: 重試次數
    """
    node_id: str
    node_type: str
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_backoff_factor: float = 1.0


@dataclass
class TransformNodeConfig:
    """
    數據轉換節點配置
    
    屬性：
      - node_id: 節點 ID
      - node_type: 節點類型
      - name: 節點名稱
      - config: 節點配置 (transform_type, operation, etc.)
      - inputs: 輸入列表
      - outputs: 輸出列表
      - timeout: 超時時間
      - retry_count: 重試次數
    """
    node_id: str
    node_type: str
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_backoff_factor: float = 1.0


@dataclass
class CalculateNodeConfig:
    """
    計算節點配置
    
    屬性：
      - node_id: 節點 ID
      - node_type: 節點類型
      - name: 節點名稱
      - config: 節點配置 (operation, operation_type, etc.)
      - inputs: 輸入列表
      - outputs: 輸出列表
      - timeout: 超時時間
      - retry_count: 重試次數
    """
    node_id: str
    node_type: str
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_backoff_factor: float = 1.0


@dataclass
class ConditionNodeConfig:
    """
    條件判斷節點配置
    
    屬性：
      - node_id: 節點 ID
      - node_type: 節點類型
      - name: 節點名稱
      - config: 節點配置 (condition_mode, condition, etc.)
      - inputs: 輸入列表
      - outputs: 輸出列表
      - timeout: 超時時間
      - retry_count: 重試次數
    """
    node_id: str
    node_type: str
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_backoff_factor: float = 1.0


@dataclass
class OutputNodeConfig:
    """
    輸出節點配置
    
    屬性：
      - node_id: 節點 ID
      - node_type: 節點類型
      - name: 節點名稱
      - config: 節點配置 (output_type, output_format, etc.)
      - inputs: 輸入列表
      - outputs: 輸出列表
      - timeout: 超時時間
      - retry_count: 重試次數
    """
    node_id: str
    node_type: str
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_backoff_factor: float = 1.0


def _require_config_value(node_id: str, config: Dict[str, Any], key: str) -> None:
    value = config.get(key)
    if value is None or value == "":
        raise ValueError(f"Node {node_id}: missing required config '{key}'")


def _normalize_node_type(raw_type: Any) -> NodeType:
    if isinstance(raw_type, NodeType):
        return raw_type
    if raw_type is None:
        raise ValueError("node_type is required")
    try:
        return NodeType(str(raw_type).lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported node_type: {raw_type}") from exc


def validate_node_config(node_config: Dict[str, Any]) -> None:
    """Validate minimal required fields for a node config."""
    if not node_config:
        raise ValueError("node_config is required")

    node_id = node_config.get("node_id")
    if not node_id:
        raise ValueError("node_id is required")

    node_type = _normalize_node_type(node_config.get("node_type"))
    config = node_config.get("config") or {}

    timeout = node_config.get("timeout")
    if timeout is not None:
        try:
            if float(timeout) <= 0:
                raise ValueError(f"Node {node_id}: timeout must be > 0")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Node {node_id}: invalid timeout") from exc

    retry_count = node_config.get("retry_count", 0)
    try:
        if int(retry_count) < 0:
            raise ValueError(f"Node {node_id}: retry_count must be >= 0")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Node {node_id}: invalid retry_count") from exc

    retry_delay_seconds = node_config.get("retry_delay_seconds", 0)
    try:
        if float(retry_delay_seconds) < 0:
            raise ValueError(f"Node {node_id}: retry_delay_seconds must be >= 0")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Node {node_id}: invalid retry_delay_seconds") from exc

    retry_backoff_factor = node_config.get("retry_backoff_factor", 1.0)
    try:
        if float(retry_backoff_factor) < 1:
            raise ValueError(f"Node {node_id}: retry_backoff_factor must be >= 1")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Node {node_id}: invalid retry_backoff_factor") from exc

    if node_type == NodeType.DATA_INPUT:
        source_type = config.get("source_type", "global")
        required = {
            "constant": "value",
            "labflow_file": "file_id",
            "environment": "env_var",
            "file": "file_path",
            "database": "table_name",
            "api": "url",
        }
        required_key = required.get(source_type)
        if required_key:
            _require_config_value(node_id, config, required_key)
    elif node_type == NodeType.TRANSFORM:
        transform_type = config.get("transform_type", "map")
        if transform_type == "map":
            _require_config_value(node_id, config, "operation")
        elif transform_type == "filter":
            _require_config_value(node_id, config, "condition")
            _require_config_value(node_id, config, "operator")
            if "threshold" not in config:
                raise ValueError(f"Node {node_id}: missing required config 'threshold'")
    elif node_type == NodeType.CALCULATE:
        op_type = config.get("operation_type", "arithmetic")
        if op_type == "arithmetic":
            _require_config_value(node_id, config, "operation")
            operands = config.get("operands", [])
            if not operands:
                raise ValueError(f"Node {node_id}: missing required config 'operands'")
        elif op_type == "comparison":
            _require_config_value(node_id, config, "operation")
            _require_config_value(node_id, config, "left")
            _require_config_value(node_id, config, "right")
        elif op_type == "logical":
            _require_config_value(node_id, config, "operation")
            operands = config.get("operands", [])
            if not operands:
                raise ValueError(f"Node {node_id}: missing required config 'operands'")
        elif op_type == "mathematical":
            _require_config_value(node_id, config, "operation")
            _require_config_value(node_id, config, "value")
        elif op_type == "statistical":
            _require_config_value(node_id, config, "operation")
            _require_config_value(node_id, config, "data")
        elif op_type == "analysis":
            if not config.get("tool_id") and not config.get("operation"):
                raise ValueError(f"Node {node_id}: missing required config 'tool_id'")
        else:
            raise ValueError(f"Node {node_id}: unknown operation_type '{op_type}'")
    elif node_type == NodeType.CONDITION:
        condition_type = config.get("condition_type", "if")
        if condition_type == "if":
            _require_config_value(node_id, config, "condition")
        elif condition_type == "switch":
            _require_config_value(node_id, config, "variable")
            cases = config.get("cases")
            if not isinstance(cases, dict) or not cases:
                raise ValueError(f"Node {node_id}: missing required config 'cases'")
        elif condition_type == "filter":
            _require_config_value(node_id, config, "condition")
        else:
            raise ValueError(f"Node {node_id}: unknown condition_type '{condition_type}'")
    elif node_type == NodeType.OUTPUT:
        output_type = config.get("output_type", "return")
        if output_type not in {"return", "store", "send", "log"}:
            raise ValueError(f"Node {node_id}: unknown output_type '{output_type}'")
