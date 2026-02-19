"""
Integration base types for external analysis tools.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolParameter:
    name: str
    type: str
    required: bool = False
    default: Optional[Any] = None
    description: str = ""


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    version: str
    description: str
    input_types: List[str]
    parameters: List[ToolParameter] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)


@dataclass
class ToolContext:
    file_id: Optional[int] = None
    filename: Optional[str] = None
    file_bytes: Optional[bytes] = None
    file_path: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    status: str
    output: Dict[str, Any] = field(default_factory=dict)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    conclusion: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class ToolAdapter:
    spec: ToolSpec

    def run(self, context: ToolContext) -> ToolResult:
        raise NotImplementedError
