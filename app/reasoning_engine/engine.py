"""
推理引擎核心

提供推理鏈的執行引擎，包括：
  1. 拓撲排序：驗證 DAG 並確定執行順序
  2. 節點執行：按順序執行每個節點
  3. 結果追蹤：記錄執行過程和結果
  4. 錯誤處理：捕捉和記錄異常

架構：
  ReasoningEngine
    ├── _topological_sort(): 拓撲排序
    ├── _validate_dag(): 驗證有向無環圖
    ├── _get_node_handler(): 獲取節點處理器
    ├── _execute_node(): 執行單個節點
    └── execute_chain(): 完整推理鏈執行

作者：LabFlow Team
日期：2026-02-14
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from .node_types import (
    NodeConfig,
    NodeInput,
    NodeType,
    NodeStatus,
    NodeResult,
    ReasoningNode,
    validate_node_config,
    DataInputNodeConfig,
    TransformNodeConfig,
    CalculateNodeConfig,
    ConditionNodeConfig,
    OutputNodeConfig,
)
from .handlers import (
    DataInputHandler,
    TransformHandler,
    CalculateHandler,
    ConditionHandler,
    OutputHandler,
    HANDLER_REGISTRY,
)
from app import models


logger = logging.getLogger(__name__)


class ReasoningEngineException(Exception):
    """推理引擎異常基類"""
    pass


class DAGValidationError(ReasoningEngineException):
    """DAG 驗證錯誤"""
    pass


class NodeExecutionError(ReasoningEngineException):
    """節點執行錯誤"""
    pass


class NodeExecutor:
    """節點執行器：負責單節點執行與錯誤封裝"""

    def __init__(self, db_session=None, storage=None, persist_execution: bool = True):
        self.db = db_session
        self.storage = storage
        self.data_input_handler = DataInputHandler()
        self.transform_handler = TransformHandler()
        self.calculate_handler = CalculateHandler()
        self.condition_handler = ConditionHandler()
        self.output_handler = OutputHandler()

    def execute(self, node_config: Dict[str, Any], inputs: Dict[str, Any], global_input: Optional[Dict[str, Any]] = None) -> NodeResult:
        node_id = node_config.get("node_id")
        node_type = node_config.get("node_type")
        if isinstance(node_type, NodeType):
            node_type = node_type.value
        else:
            node_type = str(node_type).lower() if node_type is not None else None

        start_time = datetime.now()

        try:
            validate_node_config(node_config)
            if node_type == NodeType.DATA_INPUT.value:
                config = DataInputNodeConfig(**node_config)
                return self.data_input_handler.execute(config, global_input or {}, inputs, self.db, self.storage)
            if node_type == NodeType.TRANSFORM.value:
                config = TransformNodeConfig(**node_config)
                return self.transform_handler.execute(config, global_input or {}, inputs, self.db, self.storage)
            if node_type == NodeType.CALCULATE.value:
                config = CalculateNodeConfig(**node_config)
                return self.calculate_handler.execute(config, global_input or {}, inputs, self.db, self.storage)
            if node_type == NodeType.CONDITION.value:
                config = ConditionNodeConfig(**node_config)
                return self.condition_handler.execute(config, global_input or {}, inputs, self.db, self.storage)
            if node_type == NodeType.OUTPUT.value:
                config = OutputNodeConfig(**node_config)
                return self.output_handler.execute(config, global_input or {}, inputs, self.db, self.storage)

            raise NodeExecutionError(f"不支持的節點類型: {node_type}")
        except Exception as e:
            logger.exception(f"節點 {node_id} 執行失敗")
            completed_time = datetime.now()
            execution_time_ms = (completed_time - start_time).total_seconds() * 1000

            return NodeResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                error=str(e),
                started_at=start_time,
                completed_at=completed_time,
                execution_time_ms=execution_time_ms,
            )


class ReasoningEngine:
    """
    推理引擎核心
    
    責任：
      1. 驗證推理鏈結構（確保是 DAG）
      2. 確定節點執行順序（拓撲排序）
      3. 按順序執行節點並收集結果
      4. 處理錯誤並追蹤執行過程
    
    使用示例：
      engine = ReasoningEngine(db_session)
      results = engine.execute_chain(
          chain_id="chain-123",
          input_data={"file_id": "file-456"}
      )
    """
    
    def __init__(
        self,
        db_session=None,
        storage=None,
        persist_execution: bool = True,
        enable_parallel: bool = False,
        max_workers: Optional[int] = None,
    ):
        """
        初始化推理引擎
        
        參數：
          db_session: SQLAlchemy 資料庫會話（可選）
          storage: 檔案儲存物件 (可選)
        """
        self.db = db_session
        self.storage = storage
        self.executor = NodeExecutor(db_session=db_session, storage=storage)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.persist_execution = persist_execution
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
    
    def execute_chain(
        self,
        nodes: List[Dict[str, Any]],
        input_data: Optional[Dict[str, Any]] = None,
        timeout: int = 3600,
        chain_id: Optional[str] = None,
        enable_parallel: Optional[bool] = None,
        max_workers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        執行完整推理鏈
        
        參數：
          nodes: 節點配置列表
          input_data: 初始輸入數據
          timeout: 整條鏈的執行超時（秒）
        
        返回：
          {
            "status": "completed" | "failed",
            "results": {node_id: node_result},
            "errors": [...],
            "execution_time_ms": 1234.5
          }
        
        異常：
          - DAGValidationError: 鏈結構無效
          - NodeExecutionError: 節點執行失敗
        """
        start_time = datetime.now()
        chain_start = time.monotonic()
        results = {}
        execution_order = []
        errors = []
        chain_timed_out = False

        use_parallel = self.enable_parallel if enable_parallel is None else enable_parallel
        effective_max_workers = max_workers or self.max_workers

        if use_parallel and self.db is not None:
            logger.warning("Parallel execution disabled due to shared db_session; use per-thread sessions.")
            use_parallel = False
        
        try:
            # 1. 驗證 DAG 結構
            logger.info(f"驗證推理鏈結構 ({len(nodes)} 個節點)")
            self._validate_dag(nodes)
            
            # 2. 拓撲排序
            logger.info("執行拓撲排序")
            execution_order = self._topological_sort(nodes)

            # 3. 執行節點
            if use_parallel:
                results, errors, chain_timed_out = self._execute_chain_parallel(
                    nodes=nodes,
                    input_data=input_data,
                    timeout=timeout,
                    chain_start=chain_start,
                    max_workers=effective_max_workers,
                )
            else:
                results, errors, chain_timed_out = self._execute_chain_sequential(
                    nodes=nodes,
                    input_data=input_data,
                    timeout=timeout,
                    chain_start=chain_start,
                    execution_order=execution_order,
                )
            
            # 計算執行耗時
            end_time = datetime.now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # 判斷整體狀態
            has_failed = any(
                r.status == NodeStatus.FAILED
                for r in results.values()
            )
            overall_status = "failed" if (has_failed or errors or chain_timed_out) else "completed"
            
            response = {
                "status": overall_status,
                "results": {
                    node_id: {
                        "node_id": r.node_id,
                        "status": r.status.value,
                        "output": r.output,
                        "error": r.error,
                        "execution_time_ms": r.execution_time_ms,
                    }
                    for node_id, r in results.items()
                },
                "errors": errors,
                "execution_time_ms": execution_time_ms,
                "execution_order": execution_order,
            }

            self._store_execution(chain_id, input_data, response, errors)

            return response
        
        except Exception as e:
            logger.exception("推理鏈執行失敗")
            end_time = datetime.now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            response = {
                "status": "failed",
                "results": {
                    node_id: {
                        "node_id": r.node_id,
                        "status": r.status.value,
                        "output": r.output,
                        "error": r.error,
                        "execution_time_ms": r.execution_time_ms,
                    }
                    for node_id, r in results.items()
                },
                "errors": errors + [{"error": str(e)}],
                "execution_time_ms": execution_time_ms,
            }
            self._store_execution(chain_id, input_data, response, errors + [{"error": str(e)}])
            return response

    def _execute_chain_sequential(
        self,
        nodes: List[Dict[str, Any]],
        input_data: Optional[Dict[str, Any]],
        timeout: int,
        chain_start: float,
        execution_order: List[str],
    ) -> Tuple[Dict[str, NodeResult], List[Dict[str, Any]], bool]:
        results: Dict[str, NodeResult] = {}
        errors: List[Dict[str, Any]] = []
        chain_timed_out = False
        node_dict = {n["node_id"]: n for n in nodes}

        for node_id in execution_order:
            if self._is_chain_timed_out(chain_start, timeout):
                chain_timed_out = True
                errors.append({"error": f"Chain execution timeout after {timeout} seconds"})
                break

            try:
                node_config = node_dict[node_id]
                logger.info(f"執行節點: {node_id} (類型: {node_config['node_type']})")

                node_inputs = self._collect_inputs(node_config, results)
                node_result = self._execute_with_retry(node_config, node_inputs, input_data)
                results[node_id] = node_result

                if node_result.status == NodeStatus.FAILED:
                    logger.error(f"節點 {node_id} 執行失敗: {node_result.error}")
                    errors.append({
                        "node_id": node_id,
                        "error": node_result.error,
                    })
            except Exception as e:
                logger.exception(f"執行節點 {node_id} 時發生異常")
                errors.append({
                    "node_id": node_id,
                    "error": str(e),
                })

        return results, errors, chain_timed_out

    def _execute_chain_parallel(
        self,
        nodes: List[Dict[str, Any]],
        input_data: Optional[Dict[str, Any]],
        timeout: int,
        chain_start: float,
        max_workers: Optional[int],
    ) -> Tuple[Dict[str, NodeResult], List[Dict[str, Any]], bool]:
        results: Dict[str, NodeResult] = {}
        errors: List[Dict[str, Any]] = []
        chain_timed_out = False

        normalized_nodes = self._normalize_nodes(nodes)
        node_dict = {n["node_id"]: n for n in nodes}
        in_degree = {n.get("node_id"): 0 for n in normalized_nodes}
        graph = defaultdict(list)

        for node in normalized_nodes:
            node_id = node.get("node_id")
            inputs = node.get("inputs", [])
            for input_id in inputs:
                graph[input_id].append(node_id)
                in_degree[node_id] += 1

        ready = deque([n_id for n_id in in_degree if in_degree[n_id] == 0])
        worker_count = max_workers or min(32, (os.cpu_count() or 1) + 4)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            while ready:
                if self._is_chain_timed_out(chain_start, timeout):
                    chain_timed_out = True
                    errors.append({"error": f"Chain execution timeout after {timeout} seconds"})
                    break

                futures = {}
                while ready:
                    node_id = ready.popleft()
                    node_config = node_dict[node_id]
                    node_inputs = self._collect_inputs(node_config, results)
                    futures[executor.submit(self._execute_with_retry, node_config, node_inputs, input_data)] = node_id

                remaining = self._remaining_chain_time(chain_start, timeout)
                try:
                    for future in as_completed(futures, timeout=remaining if remaining is not None else None):
                        node_id = futures[future]
                        try:
                            node_result = future.result()
                        except Exception as exc:
                            logger.exception(f"執行節點 {node_id} 時發生異常")
                            node_result = NodeResult(
                                node_id=node_id,
                                status=NodeStatus.FAILED,
                                output=None,
                                error=str(exc),
                                started_at=datetime.now(),
                                completed_at=datetime.now(),
                            )

                        results[node_id] = node_result

                        if node_result.status == NodeStatus.FAILED:
                            logger.error(f"節點 {node_id} 執行失敗: {node_result.error}")
                            errors.append({
                                "node_id": node_id,
                                "error": node_result.error,
                            })

                        for neighbor in graph.get(node_id, []):
                            in_degree[neighbor] -= 1
                            if in_degree[neighbor] == 0:
                                ready.append(neighbor)
                except FutureTimeoutError:
                    chain_timed_out = True
                    errors.append({"error": f"Chain execution timeout after {timeout} seconds"})
                    for future in futures:
                        future.cancel()
                    break

        return results, errors, chain_timed_out

    def _is_chain_timed_out(self, chain_start: float, timeout: int) -> bool:
        if timeout is None or timeout <= 0:
            return False
        return (time.monotonic() - chain_start) >= timeout

    def _remaining_chain_time(self, chain_start: float, timeout: int) -> Optional[float]:
        if timeout is None or timeout <= 0:
            return None
        remaining = timeout - (time.monotonic() - chain_start)
        return max(0.0, remaining)
    
    def _validate_dag(self, nodes: List[Dict[str, Any]]) -> None:
        """
        驗證節點配置是否構成有向無環圖 (DAG)
        
        檢查項：
          1. 所有節點都有唯一 ID
          2. 輸入引用的節點存在
          3. 不存在循環依賴
        
        異常：
          - DAGValidationError: 驗證失敗
        """
        if not nodes:
            raise DAGValidationError("推理鏈必須至少有一個節點")
        
        normalized_nodes = self._normalize_nodes(nodes)

        # 構建節點 ID 集合
        node_ids = set(n.get("node_id") for n in normalized_nodes)
        if len(node_ids) != len(normalized_nodes):
            raise DAGValidationError("存在重複的節點 ID")
        
        # 檢查輸入參考
        for node in normalized_nodes:
            inputs = node.get("inputs", [])
            for input_node_id in inputs:
                if input_node_id not in node_ids:
                    raise DAGValidationError(
                        f"節點 {node.get('node_id')} 引用了不存在的節點 {input_node_id}"
                    )
        
        # 檢查循環依賴
        if self._has_cycle(normalized_nodes):
            raise DAGValidationError("推理鏈中存在循環依賴")
    
    def _has_cycle(self, nodes: List[Dict[str, Any]]) -> bool:
        """檢查是否存在循環依賴（DFS）"""
        # 構建鄰接表
        graph = defaultdict(list)
        for node in nodes:
            node_id = node.get("node_id")
            inputs = node.get("inputs", [])
            for input_id in inputs:
                graph[input_id].append(node_id)  # 反向邊（依賴關係）
        
        # DFS 檢查循環
        visited = set()
        rec_stack = set()
        
        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node in nodes:
            node_id = node.get("node_id")
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    def _topological_sort(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """
        拓撲排序節點（Kahn 算法）
        
        返回：
          節點 ID 的排序列表（執行順序）
        """
        normalized_nodes = self._normalize_nodes(nodes)

        # 計算入度
        in_degree = {n.get("node_id"): 0 for n in normalized_nodes}
        graph = defaultdict(list)
        
        for node in normalized_nodes:
            node_id = node.get("node_id")
            inputs = node.get("inputs", [])
            for input_id in inputs:
                graph[input_id].append(node_id)
                in_degree[node_id] += 1
        
        # 入度為 0 的節點入隊
        queue = deque([n for n in in_degree if in_degree[n] == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(normalized_nodes):
            raise DAGValidationError("拓撲排序失敗（可能存在循環或不連通的分量）")
        
        return result

    def _normalize_nodes(self, nodes: List[Any]) -> List[Dict[str, Any]]:
        """將節點轉成最小結構（node_id + inputs）。"""
        normalized = []
        for node in nodes:
            if isinstance(node, ReasoningNode):
                inputs = self._extract_input_ids(node.inputs)
                normalized.append({"node_id": node.node_id, "inputs": inputs})
            elif isinstance(node, NodeConfig):
                inputs = self._extract_input_ids(node.inputs)
                normalized.append({"node_id": node.node_id, "inputs": inputs})
            else:
                node_id = node.get("node_id")
                inputs = self._extract_input_ids(node.get("inputs", []))
                normalized.append({"node_id": node_id, "inputs": inputs})
        return normalized

    def _extract_input_ids(self, inputs: Any) -> List[str]:
        """從多種輸入格式提取依賴節點 ID。"""
        if not inputs:
            return []
        input_ids = []
        for item in inputs:
            if isinstance(item, str):
                input_ids.append(item)
            elif isinstance(item, NodeInput):
                input_ids.append(item.source_node_id)
            elif isinstance(item, dict):
                source_id = item.get("source_node_id")
                if source_id:
                    input_ids.append(source_id)
        return input_ids
    
    def _collect_inputs(
        self,
        node_config: Dict[str, Any],
        results: Dict[str, NodeResult]
    ) -> Dict[str, Any]:
        """
        收集節點的輸入數據
        
        參數：
          node_config: 節點配置
          results: 之前節點的執行結果
        
        返回：
          合併的輸入數據
        """
        inputs = node_config.get("inputs", [])
        collected = {}
        
        for input_node_id in inputs:
            if input_node_id in results:
                node_result = results[input_node_id]
                # 使用節點 ID 作為鍵
                collected[input_node_id] = node_result.output
        
        return collected
    
    def _execute_node(
        self,
        node_config: Dict[str, Any],
        inputs: Dict[str, Any],
        global_input: Optional[Dict[str, Any]] = None
    ) -> NodeResult:
        """
        執行單個節點
        
        參數：
          node_config: 節點配置
          inputs: 輸入數據
          global_input: 全局初始輸入
        
        返回：
          NodeResult: 執行結果
        """
        logger.info(f"執行節點 {node_config.get('node_id')} ({node_config.get('node_type')})")
        cache_key = node_config.get("cache_key")
        if cache_key and cache_key in self.cache:
            cached = self.cache[cache_key]
            return NodeResult(
                node_id=node_config.get("node_id"),
                status=NodeStatus.COMPLETED,
                output=cached,
                error=None,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        result = self.executor.execute(node_config, inputs, global_input)
        if cache_key and result.status == NodeStatus.COMPLETED:
            self.cache[cache_key] = result.output
        return result

    def _execute_with_retry(
        self,
        node_config: Dict[str, Any],
        inputs: Dict[str, Any],
        global_input: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        retry_count = int(node_config.get("retry_count", 0))
        retry_delay_seconds = float(node_config.get("retry_delay_seconds", 0))
        retry_backoff_factor = float(node_config.get("retry_backoff_factor", 1.0))
        last_result: Optional[NodeResult] = None
        attempts = retry_count + 1

        for attempt in range(attempts):
            result = self._execute_with_timeout(node_config, inputs, global_input)
            last_result = result
            if result.status != NodeStatus.FAILED:
                return result
            if attempt < attempts - 1 and retry_delay_seconds > 0:
                backoff = retry_delay_seconds * (retry_backoff_factor ** attempt)
                time.sleep(backoff)

        return last_result if last_result else NodeResult(
            node_id=node_config.get("node_id"),
            status=NodeStatus.FAILED,
            output=None,
            error="Node execution failed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    def _execute_with_timeout(
        self,
        node_config: Dict[str, Any],
        inputs: Dict[str, Any],
        global_input: Optional[Dict[str, Any]] = None,
    ) -> NodeResult:
        if self.db is not None:
            # Avoid moving ORM sessions across threads.
            return self._execute_node(node_config, inputs, global_input)

        timeout_seconds = node_config.get("timeout")
        if timeout_seconds is None:
            timeout_seconds = 300
        try:
            timeout_seconds = float(timeout_seconds)
        except (TypeError, ValueError):
            timeout_seconds = 300

        if timeout_seconds <= 0:
            return self._execute_node(node_config, inputs, global_input)

        start_time = datetime.now()
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self._execute_node, node_config, inputs, global_input)
            try:
                return future.result(timeout=timeout_seconds)
            except FutureTimeoutError:
                future.cancel()
                return NodeResult(
                    node_id=node_config.get("node_id"),
                    status=NodeStatus.FAILED,
                    output=None,
                    error=f"Node execution timeout after {timeout_seconds} seconds",
                    started_at=start_time,
                    completed_at=datetime.now(),
                )
        finally:
            executor.shutdown(wait=False)

    def _store_execution(
        self,
        chain_id: Optional[str],
        input_data: Optional[Dict[str, Any]],
        response: Dict[str, Any],
        errors: List[Dict[str, Any]],
    ) -> None:
        if not self.persist_execution or not self.db or not chain_id:
            return

        status = response.get("status", "failed")
        results = response.get("results")
        error_log = None
        if errors:
            error_log = str(errors)

        execution = models.ReasoningExecution(
            chain_id=chain_id,
            status=status,
            input_data=input_data,
            results=results,
            error_log=error_log,
            completed_at=datetime.now(),
            execution_time_ms=response.get("execution_time_ms"),
        )
        self.db.add(execution)
        self.db.commit()

    # ========================================================================
    # 節點處理已移至 handlers.py 模塊
    # 支持以下節點類型：
    #   - DATA_INPUT: 數據輸入節點
    #   - TRANSFORM: 數據轉換節點
    #   - CALCULATE: 計算節點
    #   - CONDITION: 條件分支節點
    #   - OUTPUT: 輸出節點
    # ========================================================================
