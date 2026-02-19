"""
Node handlers for different operation types in the reasoning engine.

Implements specific behaviors for:
  - DATA_INPUT: Data source retrieval and preprocessing
  - TRANSFORM: Data mapping and transformation
  - CALCULATE: Arithmetic and statistical operations
  - CONDITION: Boolean logic and branching decisions
  - OUTPUT: Result aggregation and formatting
"""

import json
import operator
import statistics
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from app import models
from app.storage import LocalStorage

from .node_types import (
    DataInputNodeConfig,
    TransformNodeConfig,
    CalculateNodeConfig,
    ConditionNodeConfig,
    OutputNodeConfig,
    NodeResult,
    NodeStatus,
)


class NodeHandlerError(Exception):
    """Base exception for node handler errors"""
    pass


class DataInputHandler:
    """Handles DATA_INPUT nodes: retrieve data from external sources"""
    
    def execute(
        self,
        config: DataInputNodeConfig,
        global_input: Dict[str, Any],
        node_inputs: Dict[str, Any],
        db: Session,
        storage: LocalStorage,
    ) -> NodeResult:
        """
        Execute data input node.
        
        Data source types:
          - 'global': Use global input data
          - 'constant': Use static constant value
          - 'environment': Read from environment variables
          - 'labflow_file': Read a file managed by LabFlow
          - 'file': Read from file
          - 'database': Query from database
          - 'api': Call external API
        """
        start_time = datetime.now()
        
        try:
            source_type = config.config.get("source_type", "global")
            
            if source_type == "global":
                result = self._from_global(config, global_input)
            elif source_type == "constant":
                result = self._from_constant(config)
            elif source_type == "labflow_file":
                result = self._from_labflow_file(config, db, storage)
            elif source_type == "environment":
                result = self._from_environment(config)
            elif source_type == "file":
                result = self._from_file(config)
            elif source_type == "database":
                result = self._from_database(config, db)
            elif source_type == "api":
                result = self._from_api(config)
            else:
                raise NodeHandlerError(f"Unknown source type: {source_type}")
            
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.COMPLETED,
                output=result,
                error=None,
                started_at=start_time,
                completed_at=datetime.now(),
            )
        
        except Exception as e:
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.FAILED,
                output=None,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(),
            )
    
    def _from_global(self, config: DataInputNodeConfig, global_input: Dict[str, Any]) -> Any:
        """Extract data from global input"""
        key_path = config.config.get("key_path", config.name)
        
        # Support dot notation: "user.name" -> global_input["user"]["name"]
        keys = key_path.split(".")
        value = global_input
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                raise NodeHandlerError(f"Cannot traverse {key} in non-dict value")
        
        if value is None:
            raise NodeHandlerError(f"Key not found in global input: {key_path}")
        
        return value
    
    def _from_constant(self, config: DataInputNodeConfig) -> Any:
        """Return constant value"""
        value = config.config.get("value")
        data_type = config.config.get("data_type", "string")
        
        # Type conversion
        if data_type == "integer":
            return int(value)
        elif data_type == "float":
            return float(value)
        elif data_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            return str(value).lower() in ("true", "1", "yes")
        elif data_type == "list":
            return json.loads(value) if isinstance(value, str) else value
        elif data_type == "dict":
            return json.loads(value) if isinstance(value, str) else value
        else:
            return value

    def _from_labflow_file(self, config: DataInputNodeConfig, db: Session, storage: LocalStorage) -> Any:
        """Read a file managed by LabFlow from the database."""
        file_id = config.config.get("file_id")
        if not file_id:
            raise NodeHandlerError("'file_id' not specified in config for labflow_file source type")

        file_record = db.query(models.File).filter(models.File.id == file_id).first()
        if not file_record:
            raise NodeHandlerError(f"File with id {file_id} not found in the database.")
        
        if not file_record.storage_key:
            raise NodeHandlerError(f"File with id {file_id} has no storage key.")

        file_content = storage.load(file_record.storage_key)
        
        # Return content as bytes, or decode if specified
        encoding = config.config.get("encoding")
        if encoding:
            try:
                return file_content.decode(encoding)
            except (UnicodeDecodeError, AttributeError) as e:
                raise NodeHandlerError(f"Failed to decode file content with encoding '{encoding}': {e}")
        
        return file_content

    def _from_environment(self, config: DataInputNodeConfig) -> Any:
        """Read from environment variables"""
        import os
        
        env_var = config.config.get("env_var")
        if not env_var:
            raise NodeHandlerError("env_var not specified")
        
        value = os.environ.get(env_var)
        if value is None:
            raise NodeHandlerError(f"Environment variable not found: {env_var}")
        
        return value
    
    def _from_file(self, config: DataInputNodeConfig) -> Any:
        """Read from file"""
        file_path = config.config.get("file_path")
        if not file_path:
            raise NodeHandlerError("file_path not specified")
        
        mode = config.config.get("mode", "rb")
        encoding = config.config.get("encoding")
        try:
            if "b" in mode:
                with open(file_path, mode) as handle:
                    return handle.read()
            with open(file_path, mode, encoding=encoding or "utf-8") as handle:
                return handle.read()
        except FileNotFoundError as exc:
            raise NodeHandlerError(f"File not found: {file_path}") from exc
        except OSError as exc:
            raise NodeHandlerError(f"Failed to read file {file_path}: {exc}") from exc
    
    def _from_database(self, config: DataInputNodeConfig, db: Session) -> Any:
        """Query from database"""
        from sqlalchemy import text, select, table, column

        table_name = config.config.get("table_name")
        if not table_name:
            raise NodeHandlerError("'table_name' not specified in config for database source type")

        filters = config.config.get("filters", {})
        select_columns = config.config.get("select_columns", [])
        order_by = config.config.get("order_by")
        limit = config.config.get("limit", 100)

        # Create a table object dynamically
        tbl = table(table_name)
        
        if select_columns:
            cols = [column(c) for c in select_columns]
            query = select(*cols).select_from(tbl)

            # Apply filters
            for col, value in filters.items():
                query = query.where(column(col) == value)

            # Apply ordering
            if order_by:
                query = query.order_by(text(order_by))
            
            # Apply limit
            query = query.limit(limit)

            results = db.execute(query).mappings().all()
        else:
            # Fallback: select all columns with raw SQL
            sql = f"SELECT * FROM {table_name}"
            params = {}
            if filters:
                clauses = []
                for col, value in filters.items():
                    clauses.append(f"{col} = :{col}")
                    params[col] = value
                sql += " WHERE " + " AND ".join(clauses)
            if order_by:
                sql += f" ORDER BY {order_by}"
            sql += " LIMIT :limit"
            params["limit"] = limit

            results = db.execute(text(sql), params).mappings().all()
        
        # Convert RowMapping objects to simple dicts
        return [dict(row) for row in results]
    
    def _from_api(self, config: DataInputNodeConfig) -> Any:
        """Call external API"""
        import requests

        url = config.config.get("url")
        if not url:
            raise NodeHandlerError("url not specified")

        method = str(config.config.get("method", "GET")).upper()
        headers = config.config.get("headers", {})
        params = config.config.get("params")
        payload = config.config.get("json")
        timeout = config.config.get("timeout", 10)

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NodeHandlerError(f"API request failed: {exc}") from exc

        if config.config.get("response", "json") == "text":
            return response.text
        return response.json()


class TransformHandler:
    """Handles TRANSFORM nodes: map and transform data"""
    
    def execute(
        self,
        config: TransformNodeConfig,
        global_input: Dict[str, Any],
        node_inputs: Dict[str, Any],
        db: Session,
        storage: LocalStorage,
    ) -> NodeResult:
        """
        Execute transform node.
        
        Transform types:
          - 'map': Apply function to each element
          - 'filter': Filter elements based on condition
          - 'extract': Extract specific fields
          - 'merge': Merge multiple objects
          - 'flatten': Flatten nested structures
          - 'aggregate': Aggregate multiple values
          - 'format': Format values
        """
        start_time = datetime.now()
        
        try:
            transform_type = config.config.get("transform_type", "map")
            # For most transform nodes, we expect a single, unnamed input.
            # We look for the output of the first connected input node.
            input_value = next(iter(node_inputs.values())) if node_inputs else None

            if input_value is None:
                raise NodeHandlerError("No input data provided")
            
            if transform_type == "map":
                result = self._map(config, input_value)
            elif transform_type == "filter":
                result = self._filter(config, input_value)
            elif transform_type == "extract":
                result = self._extract(config, input_value)
            elif transform_type == "merge":
                result = self._merge(config, node_inputs)
            elif transform_type == "flatten":
                result = self._flatten(config, input_value)
            elif transform_type == "aggregate":
                result = self._aggregate(config, input_value)
            elif transform_type == "format":
                result = self._format(config, input_value)
            else:
                raise NodeHandlerError(f"Unknown transform type: {transform_type}")
            
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.COMPLETED,
                output=result,
                error=None,
                started_at=start_time,
                completed_at=datetime.now(),
            )
        
        except Exception as e:
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.FAILED,
                output=None,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(),
            )
    
    def _map(self, config: TransformNodeConfig, data: Any) -> Any:
        """Apply function to each element"""
        if not isinstance(data, list):
            raise NodeHandlerError("Map requires list input")
        
        operation = config.config.get("operation")
        if not operation:
            raise NodeHandlerError("operation not specified for map")
        
        # Simple operations: multiply, add, square, uppercase, etc.
        if operation == "multiply":
            factor = config.config.get("factor", 1)
            return [x * factor for x in data if isinstance(x, (int, float))]
        elif operation == "uppercase":
            return [str(x).upper() for x in data]
        elif operation == "lowercase":
            return [str(x).lower() for x in data]
        elif operation == "square":
            return [x ** 2 for x in data if isinstance(x, (int, float))]
        elif operation == "absolute":
            return [abs(x) for x in data if isinstance(x, (int, float))]
        else:
            raise NodeHandlerError(f"Unknown map operation: {operation}")
    
    def _filter(self, config: TransformNodeConfig, data: Any) -> Any:
        """Filter elements based on condition"""
        if not isinstance(data, list):
            raise NodeHandlerError("Filter requires list input")
        
        condition = config.config.get("condition")
        operator_name = config.config.get("operator")
        threshold = config.config.get("threshold")
        
        if not all([condition, operator_name, threshold is not None]):
            raise NodeHandlerError("condition, operator, threshold required for filter")
        
        ops = {
            "gt": operator.gt,
            "lt": operator.lt,
            "eq": operator.eq,
            "gte": operator.ge,
            "lte": operator.le,
        }
        
        op_func = ops.get(operator_name)
        if not op_func:
            raise NodeHandlerError(f"Unknown operator: {operator_name}")
        
        return [x for x in data if op_func(x, threshold)]
    
    def _extract(self, config: TransformNodeConfig, data: Any) -> Any:
        """Extract specific fields from objects"""
        if isinstance(data, list):
            fields = config.config.get("fields", [])
            return [
                {k: v for k, v in item.items() if k in fields}
                for item in data
                if isinstance(item, dict)
            ]
        elif isinstance(data, dict):
            fields = config.config.get("fields", [])
            return {k: v for k, v in data.items() if k in fields}
        else:
            raise NodeHandlerError("Extract requires dict or list of dicts")
    
    def _merge(self, config: TransformNodeConfig, node_inputs: Dict[str, Any]) -> Any:
        """Merge multiple objects"""
        merge_keys = config.config.get("merge_keys", [])
        
        result = {}
        for key in merge_keys:
            if key in node_inputs:
                if isinstance(node_inputs[key], dict):
                    result.update(node_inputs[key])
                else:
                    result[key] = node_inputs[key]
        
        return result
    
    def _flatten(self, config: TransformNodeConfig, data: Any) -> List[Any]:
        """Flatten nested structures"""
        def flatten_helper(obj):
            if isinstance(obj, list):
                for item in obj:
                    yield from flatten_helper(item)
            elif isinstance(obj, dict):
                for value in obj.values():
                    yield from flatten_helper(value)
            else:
                yield obj
        
        return list(flatten_helper(data))
    
    def _aggregate(self, config: TransformNodeConfig, data: Any) -> Any:
        """Aggregate multiple values"""
        if not isinstance(data, list):
            raise NodeHandlerError("Aggregate requires list input")
        
        agg_type = config.config.get("aggregation", "sum")
        
        numeric_data = [x for x in data if isinstance(x, (int, float, Decimal))]
        
        if agg_type == "sum":
            return sum(numeric_data)
        elif agg_type == "average":
            return sum(numeric_data) / len(numeric_data) if numeric_data else 0
        elif agg_type == "min":
            return min(numeric_data) if numeric_data else None
        elif agg_type == "max":
            return max(numeric_data) if numeric_data else None
        elif agg_type == "count":
            return len(data)
        elif agg_type == "stdev":
            return statistics.stdev(numeric_data) if len(numeric_data) > 1 else 0
        else:
            raise NodeHandlerError(f"Unknown aggregation: {agg_type}")
    
    def _format(self, config: TransformNodeConfig, data: Any) -> str:
        """Format values"""
        format_type = config.config.get("format", "string")
        
        if format_type == "string":
            return str(data)
        elif format_type == "json":
            return json.dumps(data, default=str)
        elif format_type == "csv":
            if isinstance(data, list):
                return ",".join(str(x) for x in data)
            else:
                return str(data)
        elif format_type == "percent":
            if isinstance(data, (int, float)):
                percent = config.config.get("precision", 2)
                return f"{data * 100:.{percent}f}%"
            else:
                return str(data)
        else:
            return str(data)


class CalculateHandler:
    """Handles CALCULATE nodes: perform calculations"""
    
    def execute(
        self,
        config: CalculateNodeConfig,
        global_input: Dict[str, Any],
        node_inputs: Dict[str, Any],
        db: Session,
        storage: LocalStorage,
    ) -> NodeResult:
        """
        Execute calculate node.
        
        Operation types:
          - 'arithmetic': +, -, *, /, %, **
          - 'comparison': >, <, >=, <=, ==, !=
          - 'logical': and, or, not
          - 'mathematical': sqrt, log, exp, sin, cos, etc.
          - 'statistical': mean, median, variance, etc.
                    - 'analysis': run external analysis adapters
        """
        start_time = datetime.now()
        
        try:
            operation = config.config.get("operation")
            if not operation:
                raise NodeHandlerError("operation not specified")
            
            op_type = config.config.get("operation_type", "arithmetic")
            
            if op_type == "arithmetic":
                result = self._arithmetic(config, node_inputs, operation)
            elif op_type == "comparison":
                result = self._comparison(config, node_inputs, operation)
            elif op_type == "logical":
                result = self._logical(config, node_inputs, operation)
            elif op_type == "mathematical":
                result = self._mathematical(config, node_inputs, operation)
            elif op_type == "statistical":
                result = self._statistical(config, node_inputs, operation)
            elif op_type == "analysis":
                result = self._analysis(config, global_input, node_inputs, db, storage)
            else:
                raise NodeHandlerError(f"Unknown operation type: {op_type}")
            
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.COMPLETED,
                output=result,
                error=None,
                started_at=start_time,
                completed_at=datetime.now(),
            )
        
        except Exception as e:
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.FAILED,
                output=None,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(),
            )
    
    def _arithmetic(self, config: CalculateNodeConfig, inputs: Dict[str, Any], op: str) -> Union[int, float]:
        """Arithmetic operations"""
        operands = config.config.get("operands", [])
        
        if not operands:
            raise NodeHandlerError("operands not specified")
        
        values = []
        for operand in operands:
            if operand in inputs:
                values.append(inputs[operand])
            else:
                raise NodeHandlerError(f"Operand not found: {operand}")
        
        if op == "add":
            return sum(values)
        elif op == "subtract":
            return values[0] - sum(values[1:])
        elif op == "multiply":
            result = 1
            for v in values:
                result *= v
            return result
        elif op == "divide":
            if values[1] == 0:
                raise NodeHandlerError("Division by zero")
            return values[0] / values[1]
        elif op == "modulo":
            if values[1] == 0:
                raise NodeHandlerError("Modulo by zero")
            return values[0] % values[1]
        elif op == "power":
            return values[0] ** values[1]
        else:
            raise NodeHandlerError(f"Unknown arithmetic operation: {op}")
    
    def _comparison(self, config: CalculateNodeConfig, inputs: Dict[str, Any], op: str) -> bool:
        """Comparison operations"""
        left = config.config.get("left")
        right = config.config.get("right")
        
        if left is None or right is None:
            raise NodeHandlerError("left and right operands required")
        
        left_val = inputs.get(left, left)
        right_val = inputs.get(right, right)
        
        if op == "greater_than":
            return left_val > right_val
        elif op == "less_than":
            return left_val < right_val
        elif op == "greater_equal":
            return left_val >= right_val
        elif op == "less_equal":
            return left_val <= right_val
        elif op == "equal":
            return left_val == right_val
        elif op == "not_equal":
            return left_val != right_val
        else:
            raise NodeHandlerError(f"Unknown comparison operation: {op}")
    
    def _logical(self, config: CalculateNodeConfig, inputs: Dict[str, Any], op: str) -> bool:
        """Logical operations"""
        operands = config.config.get("operands", [])
        values = [inputs.get(operand, operand) for operand in operands]
        
        if op == "and":
            return all(values)
        elif op == "or":
            return any(values)
        elif op == "not":
            return not values[0] if values else False
        else:
            raise NodeHandlerError(f"Unknown logical operation: {op}")
    
    def _mathematical(self, config: CalculateNodeConfig, inputs: Dict[str, Any], op: str) -> float:
        """Mathematical operations"""
        import math
        
        value_key = config.config.get("value")
        value = inputs.get(value_key, value_key)
        
        if op == "sqrt":
            return math.sqrt(value)
        elif op == "log":
            base = config.config.get("base", 10)
            return math.log(value, base)
        elif op == "exp":
            return math.exp(value)
        elif op == "sin":
            return math.sin(value)
        elif op == "cos":
            return math.cos(value)
        elif op == "tan":
            return math.tan(value)
        elif op == "abs":
            return abs(value)
        elif op == "ceil":
            return math.ceil(value)
        elif op == "floor":
            return math.floor(value)
        else:
            raise NodeHandlerError(f"Unknown mathematical operation: {op}")
    
    def _statistical(self, config: CalculateNodeConfig, inputs: Dict[str, Any], op: str) -> float:
        """Statistical operations"""
        data_key = config.config.get("data")
        data = inputs.get(data_key, data_key)
        
        if not isinstance(data, list):
            raise NodeHandlerError("Statistical operations require list input")
        
        numeric_data = [x for x in data if isinstance(x, (int, float, Decimal))]
        
        if op == "mean":
            return statistics.mean(numeric_data) if numeric_data else 0
        elif op == "median":
            return statistics.median(numeric_data) if numeric_data else 0
        elif op == "mode":
            return statistics.mode(numeric_data) if numeric_data else 0
        elif op == "stdev":
            return statistics.stdev(numeric_data) if len(numeric_data) > 1 else 0
        elif op == "variance":
            return statistics.variance(numeric_data) if len(numeric_data) > 1 else 0
        else:
            raise NodeHandlerError(f"Unknown statistical operation: {op}")

    def _analysis(
        self,
        config: CalculateNodeConfig,
        global_input: Dict[str, Any],
        inputs: Dict[str, Any],
        db: Session,
        storage: LocalStorage,
    ) -> Dict[str, Any]:
        """Execute external analysis adapter."""
        tool_id = config.config.get("tool_id") or config.config.get("operation")
        if not tool_id:
            raise NodeHandlerError("tool_id is required for analysis operation")

        file_id = config.config.get("file_id")
        file_id_key = config.config.get("file_id_key")
        if file_id is None and file_id_key:
            if file_id_key in inputs:
                file_id = inputs.get(file_id_key)
            else:
                file_id = global_input.get(file_id_key)

        if file_id is None:
            raise NodeHandlerError("file_id is required for analysis operation")

        if db is None:
            raise NodeHandlerError("db_session is required for analysis operation")

        parameters = dict(config.config.get("parameters", {}))
        parameters_key = config.config.get("parameters_key")
        if parameters_key:
            extra = inputs.get(parameters_key) or global_input.get(parameters_key)
            if isinstance(extra, dict):
                parameters.update(extra)

        from app.services.analysis_service import AnalysisService

        service = AnalysisService(db=db, storage=storage)
        return service.run_tool(
            tool_id=tool_id,
            file_id=int(file_id),
            parameters=parameters,
            store_output=False,
        )


class ConditionHandler:
    """Handles CONDITION nodes: branching logic"""
    
    def execute(
        self,
        config: ConditionNodeConfig,
        global_input: Dict[str, Any],
        node_inputs: Dict[str, Any],
        db: Session,
        storage: LocalStorage,
    ) -> NodeResult:
        """
        Execute condition node.
        
        Returns:
          - For IF/SWITCH: returns path to follow
          - For FILTER: returns boolean
        """
        start_time = datetime.now()
        
        try:
            condition_type = config.config.get("condition_type", "if")
            
            if condition_type == "if":
                result = self._if_condition(config, node_inputs)
            elif condition_type == "switch":
                result = self._switch_condition(config, node_inputs)
            elif condition_type == "filter":
                result = self._filter_condition(config, node_inputs)
            else:
                raise NodeHandlerError(f"Unknown condition type: {condition_type}")
            
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.COMPLETED,
                output=result,
                error=None,
                started_at=start_time,
                completed_at=datetime.now(),
            )
        
        except Exception as e:
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.FAILED,
                output=None,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(),
            )
    
    def _if_condition(self, config: ConditionNodeConfig, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """IF-THEN-ELSE branching"""
        condition = config.config.get("condition")
        true_path = config.config.get("true_path", "true")
        false_path = config.config.get("false_path", "false")
        
        if not condition:
            raise NodeHandlerError("condition not specified")
        
        # Evaluate condition
        result = self._evaluate(condition, inputs)
        
        return {
            "condition_result": result,
            "next_node": true_path if result else false_path,
            "path_taken": "true" if result else "false",
        }
    
    def _switch_condition(self, config: ConditionNodeConfig, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """SWITCH multi-way branching"""
        variable = config.config.get("variable")
        cases = config.config.get("cases", {})
        default_path = config.config.get("default_path", "default")
        
        if variable not in inputs:
            raise NodeHandlerError(f"Variable not found: {variable}")
        
        value = inputs[variable]
        next_node = cases.get(str(value), default_path)
        
        return {
            "variable": variable,
            "value": value,
            "next_node": next_node,
        }
    
    def _filter_condition(self, config: ConditionNodeConfig, inputs: Dict[str, Any]) -> bool:
        """FILTER boolean condition"""
        condition = config.config.get("condition")
        
        if not condition:
            raise NodeHandlerError("condition not specified")
        
        return self._evaluate(condition, inputs)
    
    def _evaluate(self, condition: str, inputs: Dict[str, Any]) -> bool:
        """Evaluate condition string with input values"""
        # Replace variable references with actual values
        safe_dict = inputs.copy()
        safe_dict.update({
            "True": True,
            "False": False,
            "None": None,
        })
        
        try:
            return bool(eval(condition, {"__builtins__": {}}, safe_dict))
        except Exception as e:
            raise NodeHandlerError(f"Condition evaluation failed: {e}")


class OutputHandler:
    """Handles OUTPUT nodes: result aggregation and formatting"""
    
    def execute(
        self,
        config: OutputNodeConfig,
        global_input: Dict[str, Any],
        node_inputs: Dict[str, Any],
        db: Session,
        storage: LocalStorage,
    ) -> NodeResult:
        """
        Execute output node.
        
        Output types:
          - 'return': Return output
          - 'store': Store in database
          - 'send': Send to external system
          - 'log': Log output
        """
        start_time = datetime.now()
        
        try:
            output_type = config.config.get("output_type", "return")
            
            if output_type == "return":
                result = self._return_output(config, node_inputs)
            elif output_type == "store":
                result = self._store_output(config, global_input, node_inputs, db)
            elif output_type == "send":
                result = self._send_output(config, node_inputs)
            elif output_type == "log":
                result = self._log_output(config, node_inputs)
            else:
                raise NodeHandlerError(f"Unknown output type: {output_type}")
            
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.COMPLETED,
                output=result,
                error=None,
                started_at=start_time,
                completed_at=datetime.now(),
            )
        
        except Exception as e:
            return NodeResult(
                node_id=config.node_id,
                status=NodeStatus.FAILED,
                output=None,
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now(),
            )
    
    def _return_output(self, config: OutputNodeConfig, inputs: Dict[str, Any]) -> Any:
        """Return output directly"""
        output_format = config.config.get("output_format", "raw")
        fields = config.config.get("fields", [])
        
        if output_format == "raw":
            # Return all inputs
            return inputs
        elif output_format == "selected":
            # Return only selected fields
            return {k: v for k, v in inputs.items() if k in fields}
        elif output_format == "merged":
            # Merge all inputs into single object
            result = {}
            for value in inputs.values():
                if isinstance(value, dict):
                    result.update(value)
                else:
                    result["value"] = value
            return result
        else:
            return inputs
    
    def _store_output(
        self,
        config: OutputNodeConfig,
        global_input: Dict[str, Any],
        inputs: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        """Store output to database when possible, with safe fallback."""
        if db is None:
            return {
                "status": "stored",
                "message": "Output storage skipped: no database session",
            }

        store_target = config.config.get("store_target", "conclusion")
        file_id = self._get_file_id(config, global_input, inputs)
        if not file_id:
            return {
                "status": "stored",
                "message": "Output storage skipped: missing file_id",
            }

        if store_target == "conclusion":
            content = self._resolve_input_value(
                config.config.get("content_key"),
                inputs,
                config.config.get("content"),
            )
            if content is None:
                return {
                    "status": "stored",
                    "message": "Output storage skipped: missing content",
                }
            conclusion = models.Conclusion(file_id=file_id, content=str(content))
            db.add(conclusion)
            db.commit()
            return {
                "status": "stored",
                "target": "conclusion",
                "id": conclusion.id,
            }

        if store_target == "annotation":
            data = self._resolve_input_value(
                config.config.get("data_key"),
                inputs,
                config.config.get("data"),
            )
            if data is None:
                return {
                    "status": "stored",
                    "message": "Output storage skipped: missing data",
                }
            if not isinstance(data, dict):
                data = {"value": data}
            source = config.config.get("source", "auto")
            annotation = models.Annotation(file_id=file_id, data=data, source=source)
            db.add(annotation)
            db.commit()
            return {
                "status": "stored",
                "target": "annotation",
                "id": annotation.id,
            }

        raise NodeHandlerError(f"Unknown store_target: {store_target}")
    
    def _send_output(self, config: OutputNodeConfig, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Send output to external system when configured."""
        url = config.config.get("url")
        if not url:
            return {
                "status": "sent",
                "message": "Output sending skipped: no url configured",
            }

        import requests

        method = str(config.config.get("method", "POST")).upper()
        headers = config.config.get("headers", {})
        timeout = config.config.get("timeout", 10)
        payload = config.config.get("payload", inputs)

        response = requests.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return {
            "status": "sent",
            "http_status": response.status_code,
        }
    
    def _log_output(self, config: OutputNodeConfig, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Log output"""
        import logging
        
        logger = logging.getLogger("reasoning_engine")
        logger.info(f"Output from node {config.node_id}: {json.dumps(inputs, default=str)}")
        
        return {
            "status": "logged",
            "message": "Output logged successfully",
        }

    def _get_file_id(
        self,
        config: OutputNodeConfig,
        global_input: Dict[str, Any],
        inputs: Dict[str, Any],
    ) -> Optional[int]:
        file_id = config.config.get("file_id")
        if file_id:
            return file_id

        file_id_key = config.config.get("file_id_key")
        if file_id_key:
            if file_id_key in inputs:
                return inputs.get(file_id_key)
            return global_input.get(file_id_key)

        return None

    def _resolve_input_value(
        self,
        key: Optional[str],
        inputs: Dict[str, Any],
        fallback: Optional[Any] = None,
    ) -> Optional[Any]:
        if key:
            return inputs.get(key)

        if fallback is not None:
            return fallback

        if len(inputs) == 1:
            return next(iter(inputs.values()))

        return None


# Handler registry
HANDLER_REGISTRY: Dict[str, Callable] = {
    "data_input": DataInputHandler.execute,
    "transform": TransformHandler.execute,
    "calculate": CalculateHandler.execute,
    "condition": ConditionHandler.execute,
    "output": OutputHandler.execute,
}


def get_handler(node_type: str) -> Callable:
    """Get handler for node type"""
    handler = HANDLER_REGISTRY.get(str(node_type).lower())
    if not handler:
        raise NodeHandlerError(f"No handler for node type: {node_type}")
    return handler
