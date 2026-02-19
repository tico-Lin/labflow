import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import shutil
from pathlib import Path
import os
import hashlib
from datetime import datetime
import time
import threading

from app.reasoning_engine.engine import ReasoningEngine, DAGValidationError
from app.reasoning_engine.handlers import get_handler, NodeHandlerError
from app.reasoning_engine.node_types import (
    NodeType,
    NodeResult,
    NodeStatus,
    NodeConfig,
    NodeInput,
    ReasoningNode,
    validate_node_config,
)
from app.models import Base, File, ReasoningChain, ReasoningExecution, Conclusion
from app.storage import LocalStorage

@pytest.fixture(scope="function")
def db_session():
    """Creates a temporary in-memory SQLite database session for a test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def storage():
    """Creates a temporary directory for file storage for a test."""
    temp_dir = tempfile.mkdtemp()
    storage_instance = LocalStorage(base_dir=temp_dir)
    yield storage_instance
    shutil.rmtree(temp_dir)


def test_simple_arithmetic_chain(db_session, storage):
    """
    Tests a simple reasoning chain with two inputs, an addition node, and an output.
    This test does not require db or storage, but fixtures are passed for consistency.
    """
    engine = ReasoningEngine(db_session=None, storage=None)

    # 1. Define the reasoning chain nodes
    nodes = [
        {
            "node_id": "input_A",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Constant A",
            "config": {"source_type": "constant", "value": 10},
        },
        {
            "node_id": "input_B",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Constant B",
            "config": {"source_type": "constant", "value": 5},
        },
        {
            "node_id": "add_node",
            "node_type": NodeType.CALCULATE.value,
            "name": "Add A and B",
            "inputs": ["input_A", "input_B"],
            "config": {
                "operation_type": "arithmetic",
                "operation": "add",
                "operands": ["input_A", "input_B"],
            },
        },
        {
            "node_id": "output_node",
            "node_type": NodeType.OUTPUT.value,
            "name": "Final Result",
            "inputs": ["add_node"],
            "config": {"output_format": "selected", "fields": ["add_node"]},
        },
    ]

    # 2. Execute the chain
    result = engine.execute_chain(nodes=nodes)

    # 3. Assert the results
    assert result["status"] == "completed"
    assert not result["errors"]
    
    # Check the output of the addition node
    add_node_result = result["results"]["add_node"]
    assert add_node_result["status"] == "completed"
    assert add_node_result["output"] == 15

    # Check the final output of the output node
    output_node_result = result["results"]["output_node"]
    assert output_node_result["status"] == "completed"
    assert output_node_result["output"]["add_node"] == 15


def test_chain_with_labflow_file_input(db_session, storage: LocalStorage):
    """
    Tests a chain that reads a file from LabFlow's storage and outputs its content.
    """
    # 1. Setup: Create a dummy file and its database record using the storage object
    file_content = "hello world from labflow file"
    file_content_bytes = file_content.encode('utf-8')
    file_hash = hashlib.sha256(file_content_bytes).hexdigest()
    
    # Manually write file to the temporary storage directory
    storage_key = os.path.join(storage.base_dir, f"{file_hash}.bin")
    with open(storage_key, "wb") as f:
        f.write(file_content_bytes)

    db_file = File(filename="test_file.txt", storage_key=str(storage_key), file_hash=file_hash)
    db_session.add(db_file)
    db_session.commit()
    db_session.refresh(db_file)

    # 2. Define the reasoning chain
    nodes = [
        {
            "node_id": "file_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load File from DB",
            "config": {
                "source_type": "labflow_file",
                "file_id": db_file.id,
                "encoding": "utf-8",  # Specify encoding to get a string back
            },
        },
        {
            "node_id": "output_node",
            "node_type": NodeType.OUTPUT.value,
            "name": "Final Result",
            "inputs": ["file_input"],
            "config": {"output_format": "selected", "fields": ["file_input"]},
        },
    ]

    # 3. Execute the chain
    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)

    # 4. Assert the results
    assert result["status"] == "completed", f"Execution failed with errors: {result['errors']}"
    assert not result["errors"]

    # Check the output of the file input node
    file_input_result = result["results"]["file_input"]
    assert file_input_result["status"] == "completed"
    assert file_input_result["output"] == file_content

    # Check the final output from the output node
    output_node_result = result["results"]["output_node"]
    assert output_node_result["status"] == "completed"
    assert output_node_result["output"]["file_input"] == file_content


def test_chain_with_labflow_file_input_bytes(db_session, storage: LocalStorage):
    """Read LabFlow file without encoding (bytes output)."""
    file_content_bytes = b"binary-data"
    file_hash = hashlib.sha256(file_content_bytes).hexdigest()
    storage_key = os.path.join(storage.base_dir, f"{file_hash}.bin")
    with open(storage_key, "wb") as f:
        f.write(file_content_bytes)

    db_file = File(filename="bin.dat", storage_key=str(storage_key), file_hash=file_hash)
    db_session.add(db_file)
    db_session.commit()

    nodes = [
        {
            "node_id": "file_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load File Bytes",
            "config": {"source_type": "labflow_file", "file_id": db_file.id},
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["file_input"]["output"] == file_content_bytes


def test_chain_with_labflow_file_missing_id(db_session, storage: LocalStorage):
    """Missing labflow file_id should fail."""
    nodes = [
        {
            "node_id": "file_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load File",
            "config": {"source_type": "labflow_file"},
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["file_input"]["status"] == "failed"


def test_chain_with_file_input(tmp_path):
    """Tests a chain that reads a local file and outputs its content."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("local file content", encoding="utf-8")

    nodes = [
        {
            "node_id": "file_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Local File",
            "config": {
                "source_type": "file",
                "file_path": str(file_path),
                "mode": "r",
                "encoding": "utf-8",
            },
        },
        {
            "node_id": "output_node",
            "node_type": NodeType.OUTPUT.value,
            "name": "Final Result",
            "inputs": ["file_input"],
            "config": {"output_format": "selected", "fields": ["file_input"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)

    assert result["status"] == "completed"
    assert result["results"]["file_input"]["output"] == "local file content"


def test_chain_with_file_input_binary(tmp_path):
    """Reads a local file in binary mode."""
    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"binary-data")

    nodes = [
        {
            "node_id": "file_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Local File",
            "config": {
                "source_type": "file",
                "file_path": str(file_path),
                "mode": "rb",
            },
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)

    assert result["status"] == "completed"
    assert result["results"]["file_input"]["output"] == b"binary-data"


def test_chain_with_api_input(monkeypatch):
    """Tests a chain that reads data from an API and outputs its content."""
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "value": 42}

        @property
        def text(self):
            return "ok"

    def fake_request(method, url, headers=None, params=None, json=None, timeout=10):
        return DummyResponse()

    import requests
    monkeypatch.setattr(requests, "request", fake_request)

    nodes = [
        {
            "node_id": "api_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load API",
            "config": {
                "source_type": "api",
                "url": "https://example.test/api",
                "method": "GET",
                "response": "json",
            },
        },
        {
            "node_id": "output_node",
            "node_type": NodeType.OUTPUT.value,
            "name": "Final Result",
            "inputs": ["api_input"],
            "config": {"output_format": "selected", "fields": ["api_input"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)

    assert result["status"] == "completed"
    assert result["results"]["api_input"]["output"]["value"] == 42


def test_chain_with_api_input_text(monkeypatch):
    """API input returns text response when configured."""
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

        @property
        def text(self):
            return "plain"

    def fake_request(method, url, headers=None, params=None, json=None, timeout=10):
        return DummyResponse()

    import requests
    monkeypatch.setattr(requests, "request", fake_request)

    nodes = [
        {
            "node_id": "api_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load API",
            "config": {
                "source_type": "api",
                "url": "https://example.test/api",
                "method": "GET",
                "response": "text",
            },
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["api_input"]["output"] == "plain"


def test_execute_with_retry(monkeypatch):
    """Ensure retry runs until success or attempts exhausted."""
    engine = ReasoningEngine(db_session=None, storage=None)
    calls = {"count": 0}

    def fake_execute(node_config, inputs, global_input=None):
        calls["count"] += 1
        if calls["count"] < 2:
            return NodeResult(
                node_id=node_config.get("node_id"),
                status=NodeStatus.FAILED,
                output=None,
                error="temporary error",
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )
        return NodeResult(
            node_id=node_config.get("node_id"),
            status=NodeStatus.COMPLETED,
            output={"ok": True},
            error=None,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    monkeypatch.setattr(engine.executor, "execute", fake_execute)

    node_config = {
        "node_id": "retry_node",
        "node_type": NodeType.DATA_INPUT.value,
        "retry_count": 1,
    }

    result = engine._execute_with_retry(node_config, inputs={})
    assert result.status == NodeStatus.COMPLETED
    assert calls["count"] == 2


def test_execute_with_timeout(monkeypatch):
    """Ensure per-node timeout fails fast."""
    engine = ReasoningEngine(db_session=None, storage=None)

    def slow_execute(node_config, inputs, global_input=None):
        time.sleep(0.2)
        return NodeResult(
            node_id=node_config.get("node_id"),
            status=NodeStatus.COMPLETED,
            output={"ok": True},
            error=None,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    monkeypatch.setattr(engine.executor, "execute", slow_execute)

    node_config = {
        "node_id": "timeout_node",
        "node_type": NodeType.DATA_INPUT.value,
        "timeout": 0.05,
    }

    result = engine._execute_with_retry(node_config, inputs={})
    assert result.status == NodeStatus.FAILED
    assert "timeout" in (result.error or "").lower()


def test_parallel_execution_overlaps(monkeypatch):
    """Parallel execution should allow concurrent node runs."""
    engine = ReasoningEngine(db_session=None, storage=None, enable_parallel=True, max_workers=2)
    barrier = threading.Barrier(2)

    def concurrent_execute(node_config, inputs, global_input=None):
        barrier.wait(timeout=2)
        return NodeResult(
            node_id=node_config.get("node_id"),
            status=NodeStatus.COMPLETED,
            output={"ok": True},
            error=None,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    monkeypatch.setattr(engine.executor, "execute", concurrent_execute)

    nodes = [
        {
            "node_id": "n1",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "N1",
            "config": {"source_type": "constant", "value": 1},
        },
        {
            "node_id": "n2",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "N2",
            "config": {"source_type": "constant", "value": 2},
        },
    ]

    result = engine.execute_chain(nodes=nodes, enable_parallel=True, max_workers=2)
    assert result["status"] == "completed"


def test_node_cache_hit(monkeypatch):
    """Ensure cache_key uses cached output on subsequent runs."""
    engine = ReasoningEngine(db_session=None, storage=None)
    calls = {"count": 0}

    def fake_execute(node_config, inputs, global_input=None):
        calls["count"] += 1
        return NodeResult(
            node_id=node_config.get("node_id"),
            status=NodeStatus.COMPLETED,
            output={"value": 123},
            error=None,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    monkeypatch.setattr(engine.executor, "execute", fake_execute)

    node_config = {
        "node_id": "cache_node",
        "node_type": NodeType.DATA_INPUT.value,
        "cache_key": "cache_node",
    }

    first = engine._execute_node(node_config, inputs={}, global_input=None)
    second = engine._execute_node(node_config, inputs={}, global_input=None)

    assert first.output == {"value": 123}
    assert second.output == {"value": 123}
    assert calls["count"] == 1


def test_execution_record_persisted(db_session):
    """Ensure execution record is persisted when chain_id is provided."""
    chain = ReasoningChain(
        name="Persist Test",
        description="Persist execution test",
        nodes=[{"node_id": "input", "node_type": "data_input"}],
        is_template=0,
    )
    db_session.add(chain)
    db_session.commit()
    db_session.refresh(chain)

    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Constant",
            "config": {"source_type": "constant", "value": 7},
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=None)
    result = engine.execute_chain(nodes=nodes, chain_id=str(chain.id))

    assert result["status"] == "completed"
    saved = db_session.query(ReasoningExecution).filter(ReasoningExecution.chain_id == chain.id).all()
    assert len(saved) == 1


def test_execution_record_error_log(db_session):
    """Ensure error_log is stored when execution has errors."""
    chain = ReasoningChain(
        name="Persist Error Test",
        description="Persist execution error test",
        nodes=[{"node_id": "input", "node_type": "data_input"}],
        is_template=0,
    )
    db_session.add(chain)
    db_session.commit()
    db_session.refresh(chain)

    nodes = [
        {
            "node_id": "bad",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Bad",
            "config": {"source_type": "unknown"},
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=None)
    result = engine.execute_chain(nodes=nodes, chain_id=str(chain.id))

    assert result["status"] == "failed"
    saved = db_session.query(ReasoningExecution).filter(ReasoningExecution.chain_id == chain.id).all()
    assert saved
    assert saved[0].error_log


def test_data_input_environment(monkeypatch):
    """Ensure environment data input works."""
    monkeypatch.setenv("LF_TEST_ENV", "hello")
    nodes = [
        {
            "node_id": "env_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Env",
            "config": {"source_type": "environment", "env_var": "LF_TEST_ENV"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["env_input"]["output"] == "hello"


def test_data_input_global_dot_path():
    """Global input supports dot path access."""
    nodes = [
        {
            "node_id": "global_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Global",
            "config": {"source_type": "global", "key_path": "user.name"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes, input_data={"user": {"name": "Lin"}})
    assert result["results"]["global_input"]["output"] == "Lin"


def test_data_input_constant_types():
    """Constant input supports type conversion."""
    nodes = [
        {
            "node_id": "bool",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Bool",
            "config": {"source_type": "constant", "value": "true", "data_type": "boolean"},
        },
        {
            "node_id": "list",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "List",
            "config": {"source_type": "constant", "value": "[1,2]", "data_type": "list"},
        },
        {
            "node_id": "dict",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Dict",
            "config": {"source_type": "constant", "value": "{\"a\":1}", "data_type": "dict"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["bool"]["output"] is True
    assert result["results"]["list"]["output"] == [1, 2]
    assert result["results"]["dict"]["output"] == {"a": 1}


def test_data_input_boolean_numeric():
    """Numeric boolean conversion should treat non-zero as True."""
    nodes = [
        {
            "node_id": "bool_num",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "BoolNum",
            "config": {"source_type": "constant", "value": 0, "data_type": "boolean"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["bool_num"]["output"] is False


def test_data_input_global_missing_key():
    """Missing global key should fail."""
    nodes = [
        {
            "node_id": "global_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Global",
            "config": {"source_type": "global", "key_path": "missing"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes, input_data={"user": {"name": "Lin"}})
    assert result["results"]["global_input"]["status"] == "failed"


def test_data_input_global_non_dict_path():
    """Dot path traversal should fail on non-dict value."""
    nodes = [
        {
            "node_id": "global_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Global",
            "config": {"source_type": "global", "key_path": "user.name"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes, input_data={"user": "Lin"})
    assert result["results"]["global_input"]["status"] == "failed"


def test_data_input_file_missing():
    """Missing file path should fail."""
    nodes = [
        {
            "node_id": "file",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "File",
            "config": {"source_type": "file", "file_path": "does_not_exist.txt"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["file"]["status"] == "failed"


def test_data_input_api_error(monkeypatch):
    """API error returns failed status."""
    import requests

    def fake_request(method, url, headers=None, params=None, json=None, timeout=10):
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests, "request", fake_request)

    nodes = [
        {
            "node_id": "api_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "API",
            "config": {"source_type": "api", "url": "https://example.test/api"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["api_input"]["status"] == "failed"


def test_data_input_unknown_source_type():
    """Unknown data input source type should fail."""
    nodes = [
        {
            "node_id": "bad_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Bad Input",
            "config": {"source_type": "unknown"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["bad_input"]["status"] == "failed"


def test_chain_with_database_input_filters(db_session, storage: LocalStorage):
    """Database input supports filters and limit."""
    from app.models import Tag

    db_session.add_all([Tag(name="A"), Tag(name="B")])
    db_session.commit()

    nodes = [
        {
            "node_id": "db_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Tags",
            "config": {
                "source_type": "database",
                "table_name": "tags",
                "select_columns": ["name"],
                "filters": {"name": "A"},
                "limit": 1,
            },
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)
    output = result["results"]["db_input"]["output"]
    assert output == [{"name": "A"}]


def test_chain_with_database_input_order_by(db_session, storage: LocalStorage):
    """Database input supports order_by and default select all columns."""
    from app.models import Tag

    db_session.add_all([Tag(name="B"), Tag(name="A")])
    db_session.commit()

    nodes = [
        {
            "node_id": "db_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Tags",
            "config": {
                "source_type": "database",
                "table_name": "tags",
                "order_by": "name",
            },
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)
    output = result["results"]["db_input"]["output"]
    assert [row["name"] for row in output] == ["A", "B"]


def test_chain_with_database_input_filters_fallback(db_session, storage: LocalStorage):
    """Database input fallback SQL supports filters without select_columns."""
    from app.models import Tag

    db_session.add_all([Tag(name="A"), Tag(name="B")])
    db_session.commit()

    nodes = [
        {
            "node_id": "db_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Tags",
            "config": {
                "source_type": "database",
                "table_name": "tags",
                "filters": {"name": "A"},
                "limit": 10,
            },
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)
    output = result["results"]["db_input"]["output"]
    assert output == [{"id": 1, "name": "A"}]


def test_chain_with_database_input_missing_table(db_session, storage: LocalStorage):
    """Missing table_name should fail."""
    nodes = [
        {
            "node_id": "db_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Tags",
            "config": {"source_type": "database"},
        }
    ]

    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["db_input"]["status"] == "failed"


def test_node_executor_unknown_type():
    """NodeExecutor should fail for unsupported node type."""
    executor = ReasoningEngine().executor
    result = executor.execute({"node_id": "x", "node_type": "nope"}, inputs={}, global_input=None)
    assert result.status == NodeStatus.FAILED


def test_node_executor_accepts_enum_type():
    """NodeExecutor should accept NodeType enum values."""
    executor = ReasoningEngine().executor
    result = executor.execute(
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT,
            "name": "Input",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        inputs={},
        global_input=None,
    )
    assert result.status == NodeStatus.COMPLETED


def test_transform_map_multiply():
    """Transform map multiply operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "map",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Map",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "multiply", "factor": 2},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["map"]["output"] == [2, 4, 6]


def test_transform_map_requires_list():
    """Map should fail when input is not a list."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        {
            "node_id": "map",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Map",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "uppercase"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["map"]["status"] == "failed"


def test_transform_map_uppercase():
    """Transform map uppercase operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": ["a", "b"], "data_type": "list"},
        },
        {
            "node_id": "map",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Map",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "uppercase"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["map"]["output"] == ["A", "B"]


def test_transform_map_unknown_op():
    """Unknown map operation should fail."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1], "data_type": "list"},
        },
        {
            "node_id": "map",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Map",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "unknown"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["map"]["status"] == "failed"


def test_transform_unknown_type():
    """Unknown transform type should fail."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2], "data_type": "list"},
        },
        {
            "node_id": "bad",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Bad",
            "inputs": ["input"],
            "config": {"transform_type": "unknown"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["bad"]["status"] == "failed"


def test_transform_map_lowercase():
    """Transform map lowercase operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": ["A", "B"], "data_type": "list"},
        },
        {
            "node_id": "map",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Map",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "lowercase"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["map"]["output"] == ["a", "b"]


def test_transform_filter_gt():
    """Transform filter operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2, 3, 4], "data_type": "list"},
        },
        {
            "node_id": "filter",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Filter",
            "inputs": ["input"],
            "config": {"transform_type": "filter", "condition": "value", "operator": "gt", "threshold": 2},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["filter"]["output"] == [3, 4]


def test_transform_filter_missing_config():
    """Filter should fail when config is incomplete."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2], "data_type": "list"},
        },
        {
            "node_id": "filter",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Filter",
            "inputs": ["input"],
            "config": {"transform_type": "filter", "operator": "gt", "threshold": 1},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["filter"]["status"] == "failed"


def test_transform_filter_lte():
    """Transform filter lte operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "filter",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Filter",
            "inputs": ["input"],
            "config": {"transform_type": "filter", "condition": "value", "operator": "lte", "threshold": 2},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["filter"]["output"] == [1, 2]


def test_transform_filter_gte():
    """Transform filter gte operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "filter",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Filter",
            "inputs": ["input"],
            "config": {"transform_type": "filter", "condition": "value", "operator": "gte", "threshold": 2},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["filter"]["output"] == [2, 3]


def test_transform_extract_fields():
    """Transform extract operation on dict."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": {"a": 1, "b": 2}, "data_type": "dict"},
        },
        {
            "node_id": "extract",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Extract",
            "inputs": ["input"],
            "config": {"transform_type": "extract", "fields": ["a"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["extract"]["output"] == {"a": 1}


def test_transform_extract_invalid_type():
    """Extract with invalid input type should fail."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "extract",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Extract",
            "inputs": ["input"],
            "config": {"transform_type": "extract", "fields": ["a"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["extract"]["status"] == "failed"


def test_transform_merge():
    """Transform merge operation."""
    nodes = [
        {
            "node_id": "left",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Left",
            "config": {"source_type": "constant", "value": {"a": 1}, "data_type": "dict"},
        },
        {
            "node_id": "right",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Right",
            "config": {"source_type": "constant", "value": {"b": 2}, "data_type": "dict"},
        },
        {
            "node_id": "merge",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Merge",
            "inputs": ["left", "right"],
            "config": {"transform_type": "merge", "merge_keys": ["left", "right"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["merge"]["output"] == {"a": 1, "b": 2}


def test_transform_merge_non_dict():
    """Merge with non-dict value includes raw key output."""
    nodes = [
        {
            "node_id": "left",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Left",
            "config": {"source_type": "constant", "value": {"a": 1}, "data_type": "dict"},
        },
        {
            "node_id": "right",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Right",
            "config": {"source_type": "constant", "value": 2, "data_type": "integer"},
        },
        {
            "node_id": "merge",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Merge",
            "inputs": ["left", "right"],
            "config": {"transform_type": "merge", "merge_keys": ["left", "right"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["merge"]["output"] == {"a": 1, "right": 2}


def test_transform_map_square_absolute():
    """Transform map square and absolute operations."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [-2, -1, 2], "data_type": "list"},
        },
        {
            "node_id": "square",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Square",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "square"},
        },
        {
            "node_id": "absolute",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Absolute",
            "inputs": ["input"],
            "config": {"transform_type": "map", "operation": "absolute"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["square"]["output"] == [4, 1, 4]
    assert result["results"]["absolute"]["output"] == [2, 1, 2]


def test_transform_extract_list():
    """Transform extract operation on list of dicts."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [{"a": 1, "b": 2}], "data_type": "list"},
        },
        {
            "node_id": "extract",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Extract",
            "inputs": ["input"],
            "config": {"transform_type": "extract", "fields": ["b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["extract"]["output"] == [{"b": 2}]


def test_transform_format_percent():
    """Transform format percent operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 0.25, "data_type": "float"},
        },
        {
            "node_id": "format",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Format",
            "inputs": ["input"],
            "config": {"transform_type": "format", "format": "percent", "precision": 1},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["format"]["output"] == "25.0%"


def test_transform_flatten():
    """Transform flatten operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, [2, 3], {"a": 4}], "data_type": "list"},
        },
        {
            "node_id": "flatten",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Flatten",
            "inputs": ["input"],
            "config": {"transform_type": "flatten"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["flatten"]["output"] == [1, 2, 3, 4]


def test_transform_aggregate_mean():
    """Transform aggregate mean operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [2, 4, 6], "data_type": "list"},
        },
        {
            "node_id": "agg",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Agg",
            "inputs": ["input"],
            "config": {"transform_type": "aggregate", "aggregation": "average"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["agg"]["output"] == 4


def test_transform_aggregate_requires_list():
    """Aggregate should fail when input is not a list."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "agg",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Agg",
            "inputs": ["input"],
            "config": {"transform_type": "aggregate", "aggregation": "sum"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["agg"]["status"] == "failed"


def test_transform_aggregate_count():
    """Transform aggregate count operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "agg",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Agg",
            "inputs": ["input"],
            "config": {"transform_type": "aggregate", "aggregation": "count"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["agg"]["output"] == 3


def test_transform_aggregate_stdev():
    """Transform aggregate stdev operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [2, 4, 4, 4, 5, 5, 7, 9], "data_type": "list"},
        },
        {
            "node_id": "agg",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Agg",
            "inputs": ["input"],
            "config": {"transform_type": "aggregate", "aggregation": "stdev"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert pytest.approx(result["results"]["agg"]["output"], rel=1e-6) == 2.138089935299395


def test_transform_aggregate_min_max():
    """Transform aggregate min/max operations."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [2, 5, 1], "data_type": "list"},
        },
        {
            "node_id": "min",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Min",
            "inputs": ["input"],
            "config": {"transform_type": "aggregate", "aggregation": "min"},
        },
        {
            "node_id": "max",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Max",
            "inputs": ["input"],
            "config": {"transform_type": "aggregate", "aggregation": "max"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["min"]["output"] == 1
    assert result["results"]["max"]["output"] == 5


def test_transform_format_json_csv():
    """Transform format json/csv operations."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2], "data_type": "list"},
        },
        {
            "node_id": "json",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Json",
            "inputs": ["input"],
            "config": {"transform_type": "format", "format": "json"},
        },
        {
            "node_id": "csv",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Csv",
            "inputs": ["input"],
            "config": {"transform_type": "format", "format": "csv"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["json"]["output"] == "[1, 2]"
    assert result["results"]["csv"]["output"] == "1,2"


def test_transform_format_percent_non_numeric():
    """Percent format should return str for non-numeric input."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": "n/a", "data_type": "string"},
        },
        {
            "node_id": "format",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Format",
            "inputs": ["input"],
            "config": {"transform_type": "format", "format": "percent"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["format"]["output"] == "n/a"


def test_transform_format_string():
    """Transform format string operation."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 5, "data_type": "integer"},
        },
        {
            "node_id": "format",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Format",
            "inputs": ["input"],
            "config": {"transform_type": "format", "format": "string"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["format"]["output"] == "5"


def test_calculate_arithmetic_add():
    """Calculate arithmetic add."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": 2, "data_type": "integer"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "add",
            "node_type": NodeType.CALCULATE.value,
            "name": "Add",
            "inputs": ["a", "b"],
            "config": {"operation_type": "arithmetic", "operation": "add", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["add"]["output"] == 5


def test_calculate_arithmetic_missing_operands():
    """Arithmetic should fail without operands."""
    nodes = [
        {
            "node_id": "calc",
            "node_type": NodeType.CALCULATE.value,
            "name": "Calc",
            "config": {"operation_type": "arithmetic", "operation": "add"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["calc"]["status"] == "failed"


def test_calculate_arithmetic_power():
    """Calculate arithmetic power operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": 2, "data_type": "integer"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "pow",
            "node_type": NodeType.CALCULATE.value,
            "name": "Power",
            "inputs": ["a", "b"],
            "config": {"operation_type": "arithmetic", "operation": "power", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["pow"]["output"] == 8


def test_calculate_arithmetic_modulo():
    """Calculate arithmetic modulo operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": 5, "data_type": "integer"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": 2, "data_type": "integer"},
        },
        {
            "node_id": "mod",
            "node_type": NodeType.CALCULATE.value,
            "name": "Mod",
            "inputs": ["a", "b"],
            "config": {"operation_type": "arithmetic", "operation": "modulo", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["mod"]["output"] == 1


def test_calculate_arithmetic_subtract():
    """Calculate arithmetic subtract operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": 10, "data_type": "integer"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "sub",
            "node_type": NodeType.CALCULATE.value,
            "name": "Sub",
            "inputs": ["a", "b"],
            "config": {"operation_type": "arithmetic", "operation": "subtract", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["sub"]["output"] == 7


def test_calculate_arithmetic_multiply():
    """Calculate arithmetic multiply operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": 2, "data_type": "integer"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "mul",
            "node_type": NodeType.CALCULATE.value,
            "name": "Mul",
            "inputs": ["a", "b"],
            "config": {"operation_type": "arithmetic", "operation": "multiply", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["mul"]["output"] == 6


def test_calculate_comparison():
    """Calculate comparison operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 10, "data_type": "integer"},
        },
        {
            "node_id": "cmp",
            "node_type": NodeType.CALCULATE.value,
            "name": "Compare",
            "inputs": ["x"],
            "config": {"operation_type": "comparison", "operation": "greater_than", "left": "x", "right": 5},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["cmp"]["output"] is True


def test_calculate_comparison_missing_operands():
    """Comparison should fail when left/right are missing."""
    nodes = [
        {
            "node_id": "cmp",
            "node_type": NodeType.CALCULATE.value,
            "name": "Compare",
            "config": {"operation_type": "comparison", "operation": "greater_than"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["cmp"]["status"] == "failed"


def test_calculate_comparison_not_equal():
    """Calculate comparison not equal operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 10, "data_type": "integer"},
        },
        {
            "node_id": "cmp",
            "node_type": NodeType.CALCULATE.value,
            "name": "Compare",
            "inputs": ["x"],
            "config": {"operation_type": "comparison", "operation": "not_equal", "left": "x", "right": 5},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["cmp"]["output"] is True


def test_calculate_comparison_equal():
    """Calculate comparison equal operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 10, "data_type": "integer"},
        },
        {
            "node_id": "cmp",
            "node_type": NodeType.CALCULATE.value,
            "name": "Compare",
            "inputs": ["x"],
            "config": {"operation_type": "comparison", "operation": "equal", "left": "x", "right": 10},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["cmp"]["output"] is True


def test_calculate_logical_and():
    """Calculate logical and operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": True, "data_type": "boolean"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": False, "data_type": "boolean"},
        },
        {
            "node_id": "logic",
            "node_type": NodeType.CALCULATE.value,
            "name": "Logic",
            "inputs": ["a", "b"],
            "config": {"operation_type": "logical", "operation": "and", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["logic"]["output"] is False


def test_calculate_logical_not():
    """Calculate logical not operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": True, "data_type": "boolean"},
        },
        {
            "node_id": "logic",
            "node_type": NodeType.CALCULATE.value,
            "name": "Logic",
            "inputs": ["a"],
            "config": {"operation_type": "logical", "operation": "not", "operands": ["a"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["logic"]["output"] is False


def test_calculate_logical_or():
    """Calculate logical or operation."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": False, "data_type": "boolean"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": True, "data_type": "boolean"},
        },
        {
            "node_id": "logic",
            "node_type": NodeType.CALCULATE.value,
            "name": "Logic",
            "inputs": ["a", "b"],
            "config": {"operation_type": "logical", "operation": "or", "operands": ["a", "b"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["logic"]["output"] is True


def test_calculate_logical_unknown_op():
    """Logical operation with unknown op should fail."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": True, "data_type": "boolean"},
        },
        {
            "node_id": "logic",
            "node_type": NodeType.CALCULATE.value,
            "name": "Logic",
            "inputs": ["x"],
            "config": {"operation_type": "logical", "operation": "xor", "operands": ["x"]},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["logic"]["status"] == "failed"


def test_calculate_unknown_operation_type():
    """Unknown calculate operation type should fail."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        {
            "node_id": "calc",
            "node_type": NodeType.CALCULATE.value,
            "name": "Calc",
            "inputs": ["x"],
            "config": {"operation_type": "mystery", "operation": "noop"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["calc"]["status"] == "failed"


def test_calculate_mathematical_sqrt():
    """Calculate mathematical sqrt operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 16, "data_type": "integer"},
        },
        {
            "node_id": "sqrt",
            "node_type": NodeType.CALCULATE.value,
            "name": "Sqrt",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "sqrt", "value": "x"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["sqrt"]["output"] == 4


def test_calculate_mathematical_floor():
    """Calculate mathematical floor operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 3.7, "data_type": "float"},
        },
        {
            "node_id": "floor",
            "node_type": NodeType.CALCULATE.value,
            "name": "Floor",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "floor", "value": "x"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["floor"]["output"] == 3


def test_calculate_mathematical_abs():
    """Calculate mathematical abs operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": -2, "data_type": "integer"},
        },
        {
            "node_id": "abs",
            "node_type": NodeType.CALCULATE.value,
            "name": "Abs",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "abs", "value": "x"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["abs"]["output"] == 2


def test_calculate_mathematical_log():
    """Calculate mathematical log operation."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 100, "data_type": "integer"},
        },
        {
            "node_id": "log",
            "node_type": NodeType.CALCULATE.value,
            "name": "Log",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "log", "value": "x", "base": 10},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["log"]["output"] == 2


def test_calculate_mathematical_exp_trig():
    """Calculate mathematical exp/sin/cos/tan operations."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 0, "data_type": "integer"},
        },
        {
            "node_id": "exp",
            "node_type": NodeType.CALCULATE.value,
            "name": "Exp",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "exp", "value": 0},
        },
        {
            "node_id": "sin",
            "node_type": NodeType.CALCULATE.value,
            "name": "Sin",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "sin", "value": "x"},
        },
        {
            "node_id": "cos",
            "node_type": NodeType.CALCULATE.value,
            "name": "Cos",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "cos", "value": "x"},
        },
        {
            "node_id": "tan",
            "node_type": NodeType.CALCULATE.value,
            "name": "Tan",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "tan", "value": "x"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert pytest.approx(result["results"]["exp"]["output"], rel=1e-6) == 1.0
    assert result["results"]["sin"]["output"] == 0.0
    assert result["results"]["cos"]["output"] == 1.0
    assert result["results"]["tan"]["output"] == 0.0


def test_calculate_mathematical_ceil_and_unknown():
    """Calculate mathematical ceil and unknown op error path."""
    nodes = [
        {
            "node_id": "x",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "X",
            "config": {"source_type": "constant", "value": 2.3, "data_type": "float"},
        },
        {
            "node_id": "ceil",
            "node_type": NodeType.CALCULATE.value,
            "name": "Ceil",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "ceil", "value": "x"},
        },
        {
            "node_id": "bad",
            "node_type": NodeType.CALCULATE.value,
            "name": "Bad",
            "inputs": ["x"],
            "config": {"operation_type": "mathematical", "operation": "noop", "value": "x"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["ceil"]["output"] == 3
    assert result["results"]["bad"]["status"] == "failed"


def test_calculate_statistical_mean():
    """Calculate statistical mean operation."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "mean",
            "node_type": NodeType.CALCULATE.value,
            "name": "Mean",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "mean", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["mean"]["output"] == 2


def test_calculate_statistical_variance():
    """Calculate statistical variance operation."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "var",
            "node_type": NodeType.CALCULATE.value,
            "name": "Var",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "variance", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["var"]["output"] > 0


def test_calculate_statistical_mode():
    """Calculate statistical mode operation."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": [1, 1, 2], "data_type": "list"},
        },
        {
            "node_id": "mode",
            "node_type": NodeType.CALCULATE.value,
            "name": "Mode",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "mode", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["mode"]["output"] == 1


def test_calculate_statistical_median():
    """Calculate statistical median operation."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": [1, 3, 2], "data_type": "list"},
        },
        {
            "node_id": "median",
            "node_type": NodeType.CALCULATE.value,
            "name": "Median",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "median", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["median"]["output"] == 2


def test_calculate_statistical_stdev():
    """Calculate statistical stdev operation."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": [1, 2, 3], "data_type": "list"},
        },
        {
            "node_id": "stdev",
            "node_type": NodeType.CALCULATE.value,
            "name": "Stdev",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "stdev", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["stdev"]["output"] > 0


def test_calculate_statistical_invalid_input():
    """Statistical operations require list input."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": 3, "data_type": "integer"},
        },
        {
            "node_id": "mean",
            "node_type": NodeType.CALCULATE.value,
            "name": "Mean",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "mean", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["mean"]["status"] == "failed"


def test_calculate_statistical_unknown_operation():
    """Unknown statistical operation should fail."""
    nodes = [
        {
            "node_id": "data",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Data",
            "config": {"source_type": "constant", "value": [1, 2], "data_type": "list"},
        },
        {
            "node_id": "stat",
            "node_type": NodeType.CALCULATE.value,
            "name": "Stat",
            "inputs": ["data"],
            "config": {"operation_type": "statistical", "operation": "noop", "data": "data"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["stat"]["status"] == "failed"


def test_condition_switch_path():
    """Condition switch returns matched path."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": "B", "data_type": "string"},
        },
        {
            "node_id": "switch",
            "node_type": NodeType.CONDITION.value,
            "name": "Switch",
            "inputs": ["input"],
            "config": {
                "condition_type": "switch",
                "variable": "input",
                "cases": {"A": "path_a", "B": "path_b"},
                "default_path": "path_default",
            },
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["switch"]["output"]["next_node"] == "path_b"


def test_condition_switch_missing_variable():
    """Condition switch should fail when variable is missing."""
    nodes = [
        {
            "node_id": "switch",
            "node_type": NodeType.CONDITION.value,
            "name": "Switch",
            "config": {"condition_type": "switch", "variable": "missing"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["switch"]["status"] == "failed"


def test_condition_filter_bool():
    """Condition filter returns boolean result."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 4, "data_type": "integer"},
        },
        {
            "node_id": "filter",
            "node_type": NodeType.CONDITION.value,
            "name": "Filter",
            "inputs": ["input"],
            "config": {"condition_type": "filter", "condition": "input > 3"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["filter"]["output"] is True


def test_condition_unknown_type():
    """Unknown condition type should fail."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        {
            "node_id": "cond",
            "node_type": NodeType.CONDITION.value,
            "name": "Cond",
            "inputs": ["input"],
            "config": {"condition_type": "unknown"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["cond"]["status"] == "failed"


def test_condition_eval_error():
    """Condition evaluation errors should fail."""
    nodes = [
        {
            "node_id": "cond",
            "node_type": NodeType.CONDITION.value,
            "name": "Cond",
            "config": {"condition_type": "filter", "condition": "missing_var > 1"},
        }
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["cond"]["status"] == "failed"


def test_output_store_send_log():
    """Output handler store/send/log branches."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        {
            "node_id": "store",
            "node_type": NodeType.OUTPUT.value,
            "name": "Store",
            "inputs": ["input"],
            "config": {"output_type": "store"},
        },
        {
            "node_id": "send",
            "node_type": NodeType.OUTPUT.value,
            "name": "Send",
            "inputs": ["input"],
            "config": {"output_type": "send"},
        },
        {
            "node_id": "log",
            "node_type": NodeType.OUTPUT.value,
            "name": "Log",
            "inputs": ["input"],
            "config": {"output_type": "log"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["store"]["output"]["status"] == "stored"
    assert result["results"]["send"]["output"]["status"] == "sent"
    assert result["results"]["log"]["output"]["status"] == "logged"


def test_output_store_conclusion(db_session):
    """Output handler store should create a conclusion when configured."""
    file_record = File(filename="out.txt", storage_key="s1", file_hash="a" * 64)
    db_session.add(file_record)
    db_session.commit()
    db_session.refresh(file_record)

    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": "done"},
        },
        {
            "node_id": "store",
            "node_type": NodeType.OUTPUT.value,
            "name": "Store",
            "inputs": ["input"],
            "config": {
                "output_type": "store",
                "store_target": "conclusion",
                "file_id": file_record.id,
                "content_key": "input",
            },
        },
    ]

    engine = ReasoningEngine(db_session=db_session, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["store"]["status"] == "completed"

    stored = db_session.query(Conclusion).filter(Conclusion.file_id == file_record.id).all()
    assert stored
    assert stored[0].content == "done"


def test_output_selected_and_merged():
    """Output selected and merged formats."""
    nodes = [
        {
            "node_id": "left",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Left",
            "config": {"source_type": "constant", "value": {"a": 1}, "data_type": "dict"},
        },
        {
            "node_id": "right",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Right",
            "config": {"source_type": "constant", "value": {"b": 2}, "data_type": "dict"},
        },
        {
            "node_id": "selected",
            "node_type": NodeType.OUTPUT.value,
            "name": "Selected",
            "inputs": ["left", "right"],
            "config": {"output_format": "selected", "fields": ["left"]},
        },
        {
            "node_id": "merged",
            "node_type": NodeType.OUTPUT.value,
            "name": "Merged",
            "inputs": ["left", "right"],
            "config": {"output_format": "merged"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["selected"]["output"] == {"left": {"a": 1}}
    assert result["results"]["merged"]["output"] == {"a": 1, "b": 2}


def test_output_merged_overwrites_value():
    """Merged output should overwrite the value field with later non-dict inputs."""
    nodes = [
        {
            "node_id": "left",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Left",
            "config": {"source_type": "constant", "value": "first", "data_type": "string"},
        },
        {
            "node_id": "right",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Right",
            "config": {"source_type": "constant", "value": "second", "data_type": "string"},
        },
        {
            "node_id": "merged",
            "node_type": NodeType.OUTPUT.value,
            "name": "Merged",
            "inputs": ["left", "right"],
            "config": {"output_format": "merged"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["merged"]["output"] == {"value": "second"}


def test_output_raw_format():
    """Output raw format returns all inputs."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 10, "data_type": "integer"},
        },
        {
            "node_id": "raw",
            "node_type": NodeType.OUTPUT.value,
            "name": "Raw",
            "inputs": ["input"],
            "config": {"output_format": "raw"},
        },
    ]

    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["raw"]["output"] == {"input": 10}


def test_validate_dag_duplicate_ids():
    """Ensure duplicate node IDs are rejected."""
    engine = ReasoningEngine()
    nodes = [
        {"node_id": "dup", "node_type": "data_input", "name": "A"},
        {"node_id": "dup", "node_type": "data_input", "name": "B"},
    ]
    with pytest.raises(DAGValidationError):
        engine._validate_dag(nodes)


def test_validate_dag_empty():
    """Ensure empty DAG is rejected."""
    engine = ReasoningEngine()
    with pytest.raises(DAGValidationError):
        engine._validate_dag([])


def test_validate_dag_missing_dependency():
    """Ensure missing input references are rejected."""
    engine = ReasoningEngine()
    nodes = [
        {"node_id": "a", "node_type": "data_input", "name": "A"},
        {"node_id": "b", "node_type": "calculate", "name": "B", "inputs": ["missing"]},
    ]
    with pytest.raises(DAGValidationError):
        engine._validate_dag(nodes)


def test_validate_dag_cycle_detected():
    """Ensure cycles are rejected."""
    engine = ReasoningEngine()
    nodes = [
        {"node_id": "a", "node_type": "data_input", "name": "A", "inputs": ["b"]},
        {"node_id": "b", "node_type": "calculate", "name": "B", "inputs": ["a"]},
    ]
    with pytest.raises(DAGValidationError):
        engine._validate_dag(nodes)


def test_topological_sort_cycle_error():
    """Topological sort should fail on cycle."""
    engine = ReasoningEngine()
    nodes = [
        {"node_id": "a", "node_type": "data_input", "inputs": ["b"]},
        {"node_id": "b", "node_type": "calculate", "inputs": ["a"]},
    ]
    with pytest.raises(DAGValidationError):
        engine._topological_sort(nodes)


def test_execute_chain_empty_nodes_failed():
    """execute_chain should fail for empty node list."""
    engine = ReasoningEngine()
    result = engine.execute_chain(nodes=[])
    assert result["status"] == "failed"
    assert result["errors"]


def test_extract_input_ids_from_dict():
    """Extract input ids should handle dict with source_node_id."""
    engine = ReasoningEngine()
    inputs = [{"source_node_id": "a"}, {"source_node_id": "b"}]
    assert engine._extract_input_ids(inputs) == ["a", "b"]


def test_execute_chain_node_config_missing_type():
    """Missing node_type should be recorded as a per-node error."""
    nodes = [
        {
            "node_id": "bad",
            "name": "Bad",
        }
    ]
    engine = ReasoningEngine()
    result = engine.execute_chain(nodes=nodes)
    assert result["status"] == "failed"
    assert result["errors"]


def test_node_config_validation_errors():
    """NodeConfig should validate required fields and limits."""
    with pytest.raises(ValueError):
        NodeConfig(node_id="", node_type=NodeType.DATA_INPUT, name="x")
    with pytest.raises(ValueError):
        NodeConfig(node_id="x", node_type=NodeType.DATA_INPUT, name="")
    with pytest.raises(ValueError):
        NodeConfig(node_id="x", node_type=NodeType.DATA_INPUT, name="x", timeout=0)
    with pytest.raises(ValueError):
        NodeConfig(node_id="x", node_type=NodeType.DATA_INPUT, name="x", retry_count=-1)


def test_validate_node_config_missing_node_type():
    """Missing node_type should raise validation error."""
    with pytest.raises(ValueError):
        validate_node_config({"node_id": "n1", "name": "N1"})


def test_validate_node_config_data_input_missing_required():
    """DATA_INPUT with file source requires file_path."""
    with pytest.raises(ValueError):
        validate_node_config({
            "node_id": "n1",
            "node_type": "data_input",
            "name": "N1",
            "config": {"source_type": "file"},
        })


def test_validate_node_config_calculate_missing_operands():
    """CALCULATE arithmetic requires operands."""
    with pytest.raises(ValueError):
        validate_node_config({
            "node_id": "n1",
            "node_type": "calculate",
            "name": "N1",
            "config": {"operation_type": "arithmetic", "operation": "add"},
        })


def test_node_config_from_dict_and_properties():
    """from_dict should preserve NodeType and ReasoningNode properties should proxy config."""
    cfg = NodeConfig.from_dict({"node_id": "n1", "node_type": NodeType.CALCULATE, "name": "N1"})
    node = ReasoningNode(config=cfg)
    assert node.node_type == NodeType.CALCULATE
    assert node.to_dict()["node_id"] == "n1"

    cfg2 = NodeConfig.from_dict({"node_id": "n2", "node_type": "DATA_INPUT", "name": "N2"})
    assert cfg2.node_type == NodeType.DATA_INPUT


def test_normalize_nodes_supports_nodeconfig_and_reasoningnode():
    """Normalize nodes handles NodeConfig and ReasoningNode input formats."""
    config = NodeConfig(
        node_id="a",
        node_type=NodeType.DATA_INPUT,
        name="A",
        inputs=[NodeInput(source_node_id="b")],
    )
    node = ReasoningNode(config=config)

    engine = ReasoningEngine()
    normalized = engine._normalize_nodes([config, node])
    assert normalized[0]["node_id"] == "a"
    assert normalized[0]["inputs"] == ["b"]
    assert normalized[1]["node_id"] == "a"
    assert normalized[1]["inputs"] == ["b"]


def test_condition_handler_if_path():
    """Condition handler returns correct path result."""
    engine = ReasoningEngine()
    node_config = {
        "node_id": "cond",
        "node_type": NodeType.CONDITION.value,
        "name": "Cond",
        "config": {
            "condition_type": "if",
            "condition": "value > 5",
            "true_path": "t",
            "false_path": "f",
        },
    }

    result = engine._execute_node(node_config, inputs={"value": 7}, global_input=None)
    assert result.status == NodeStatus.COMPLETED
    assert result.output["next_node"] == "t"


def test_chain_with_database_input(db_session, storage: LocalStorage):
    """
    Tests a chain that reads data directly from a database table.
    """
    # 1. Setup: Create some dummy tags in the database
    from app.models import Tag
    tags_to_create = ["XRD", "SEM", "TEM"]
    db_session.add_all([Tag(name=name) for name in tags_to_create])
    db_session.commit()

    # 2. Define the reasoning chain
    nodes = [
        {
            "node_id": "db_input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Load Tags from DB",
            "config": {
                "source_type": "database",
                "table_name": "tags",
                "select_columns": ["name"],
                "order_by": "name",
            },
        },
        {
            "node_id": "output_node",
            "node_type": NodeType.OUTPUT.value,
            "name": "Final Result",
            "inputs": ["db_input"],
        },
    ]

    # 3. Execute the chain
    engine = ReasoningEngine(db_session=db_session, storage=storage)
    result = engine.execute_chain(nodes=nodes)

    # 4. Assert the results
    assert result["status"] == "completed", f"Execution failed with errors: {result['errors']}"
    assert not result["errors"]

    # Check the output of the database input node
    db_input_result = result["results"]["db_input"]
    assert db_input_result["status"] == "completed"
    
    # The output should be a list of dictionaries
    output_data = db_input_result["output"]
    assert isinstance(output_data, list)
    assert len(output_data) == 3
    
    # Extract the names and check if they match the created tags, in order
    output_names = [item['name'] for item in output_data]
    assert output_names == sorted(tags_to_create)

    # Check the final output from the output node
    output_node_result = result["results"]["output_node"]
    assert output_node_result["status"] == "completed"
    assert output_node_result["output"]["db_input"] == output_data


def test_data_input_environment_missing():
    """Missing env var returns failed status."""
    nodes = [
        {
            "node_id": "env",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Env",
            "config": {"source_type": "environment", "env_var": "LF_MISSING"},
        }
    ]
    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["env"]["status"] == "failed"


def test_data_input_constant_invalid_list():
    """Invalid JSON list should fail."""
    nodes = [
        {
            "node_id": "list",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "List",
            "config": {"source_type": "constant", "value": "[", "data_type": "list"},
        }
    ]
    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["list"]["status"] == "failed"


def test_calculate_divide_by_zero():
    """Divide by zero returns failed result."""
    nodes = [
        {
            "node_id": "a",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "A",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        {
            "node_id": "b",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "B",
            "config": {"source_type": "constant", "value": 0, "data_type": "integer"},
        },
        {
            "node_id": "div",
            "node_type": NodeType.CALCULATE.value,
            "name": "Div",
            "inputs": ["a", "b"],
            "config": {"operation_type": "arithmetic", "operation": "divide", "operands": ["a", "b"]},
        },
    ]
    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["div"]["status"] == "failed"


def test_transform_filter_invalid_operator():
    """Invalid filter operator should fail."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": [1, 2], "data_type": "list"},
        },
        {
            "node_id": "filter",
            "node_type": NodeType.TRANSFORM.value,
            "name": "Filter",
            "inputs": ["input"],
            "config": {"transform_type": "filter", "condition": "value", "operator": "bad", "threshold": 1},
        },
    ]
    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["filter"]["status"] == "failed"


def test_output_unknown_type():
    """Unknown output type should fail."""
    nodes = [
        {
            "node_id": "input",
            "node_type": NodeType.DATA_INPUT.value,
            "name": "Input",
            "config": {"source_type": "constant", "value": 1, "data_type": "integer"},
        },
        {
            "node_id": "out",
            "node_type": NodeType.OUTPUT.value,
            "name": "Out",
            "inputs": ["input"],
            "config": {"output_type": "unknown"},
        },
    ]
    engine = ReasoningEngine(db_session=None, storage=None)
    result = engine.execute_chain(nodes=nodes)
    assert result["results"]["out"]["status"] == "failed"


def test_get_handler_unknown_type():
    """get_handler should raise for unknown node type."""
    with pytest.raises(NodeHandlerError):
        get_handler("nope")


def test_get_handler_known_type():
    """get_handler returns a callable for valid types."""
    handler = get_handler("data_input")
    assert callable(handler)

