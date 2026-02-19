"""
Targeted tests for low-coverage utility modules.
"""

import json
import os
import fnmatch
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import cache as cache_module
from app.integrations.utils import write_temp_file
from app.models import File, Tag, User, RoleEnum
from app.query_optimization import (
    PaginationParams,
    paginate,
    get_files_with_pagination,
    get_file_by_id,
    bulk_get_files,
    QueryStats,
)
import app.init_db as init_db
import app.services.analysis_service as analysis_service
from app.integrations.base import ToolAdapter, ToolSpec, ToolParameter, ToolResult
from app.services.script_service import ScriptService, InvalidScriptError
from app.services.reasoning_service import ReasoningService, InvalidChainError
from app.models import ReasoningChain, ReasoningExecution
from app.storage import LocalStorage


class FakeRedis:
    def __init__(self):
        self.store = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    def keys(self, pattern):
        return [key for key in self.store.keys() if fnmatch.fnmatch(key, pattern)]


class FakeAdapter(ToolAdapter):
    spec = ToolSpec(
        id="auto",
        name="Fake Adapter",
        version="1.0",
        description="Test adapter",
        input_types=["bin"],
        parameters=[ToolParameter("value", "string", False, None, "value")],
        outputs=["ok"],
    )

    def run(self, context):
        return ToolResult(
            status="completed",
            output={"ok": True},
            annotations=[{"source": "auto"}],
            conclusion="done",
        )


@pytest.mark.unit
def test_cache_manager_round_trip(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache_module, "_redis_client", fake)
    monkeypatch.setattr(cache_module, "REDIS_AVAILABLE", True)

    key = "unit:test"
    value = {"a": 1}
    assert cache_module.CacheManager.set(key, value, ttl=10) is True
    assert cache_module.CacheManager.get(key) == value
    assert cache_module.CacheManager.delete(key) is True
    assert cache_module.CacheManager.get(key) is None


@pytest.mark.unit
def test_cache_manager_delete_pattern(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache_module, "_redis_client", fake)
    monkeypatch.setattr(cache_module, "REDIS_AVAILABLE", True)

    cache_module.CacheManager.set("prefix:1", {"v": 1}, ttl=10)
    cache_module.CacheManager.set("prefix:2", {"v": 2}, ttl=10)
    cache_module.CacheManager.set("other:1", {"v": 3}, ttl=10)

    deleted = cache_module.CacheManager.delete_pattern("prefix:*")
    assert deleted == 2
    assert cache_module.CacheManager.get("other:1") == {"v": 3}


@pytest.mark.unit
def test_cache_result_decorator(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache_module, "_redis_client", fake)
    monkeypatch.setattr(cache_module, "REDIS_AVAILABLE", True)

    calls = {"count": 0}

    @cache_module.cache_result(ttl=5, key_prefix="calc")
    def add(a, b):
        calls["count"] += 1
        return a + b

    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert calls["count"] == 1


@pytest.mark.unit
def test_cache_manager_unavailable(monkeypatch):
    monkeypatch.setattr(cache_module, "REDIS_AVAILABLE", False)
    assert cache_module.CacheManager.get("missing") is None
    assert cache_module.CacheManager.set("missing", 1) is False
    assert cache_module.CacheManager.delete("missing") is False
    assert cache_module.CacheManager.delete_pattern("*") == 0


@pytest.mark.unit
def test_write_temp_file_suffix():
    data = b"unit-test"
    path = write_temp_file(data, filename="sample.txt")
    try:
        assert os.path.exists(path)
        assert path.endswith(".txt")
        with open(path, "rb") as handle:
            assert handle.read() == data
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.unit
def test_pagination_helpers(test_db):
    params = PaginationParams(page=2, page_size=5)
    assert params.get_offset() == 5
    assert params.get_limit() == 5

    file_a = File(filename="a.txt", storage_key="/tmp/a", file_hash="a" * 64)
    file_b = File(filename="b.txt", storage_key="/tmp/b", file_hash="b" * 64)
    test_db.add_all([file_b, file_a])
    test_db.commit()

    query = test_db.query(File)
    data, total = paginate(query, page=1, page_size=10, sort_by="filename", order="asc")
    assert total == 2
    assert [item.filename for item in data] == ["a.txt", "b.txt"]


@pytest.mark.unit
def test_query_optimization_helpers(test_db):
    file_a = File(filename="a.txt", storage_key="/tmp/a", file_hash="a" * 64)
    file_b = File(filename="b.txt", storage_key="/tmp/b", file_hash="b" * 64)
    tag = Tag(name="XRD")
    file_a.tags.append(tag)
    test_db.add_all([file_a, file_b])
    test_db.commit()

    result = get_files_with_pagination(test_db, page=1, page_size=1, sort_by="filename", order="asc")
    assert result.total == 2
    assert result.total_pages == 2
    assert len(result.data) == 1

    fetched = get_file_by_id(test_db, file_a.id)
    assert fetched is not None
    assert fetched.filename == "a.txt"

    batch = bulk_get_files(test_db, [file_a.id, file_b.id])
    assert {item.filename for item in batch} == {"a.txt", "b.txt"}


@pytest.mark.unit
def test_query_stats_defaults():
    QueryStats.reset()
    stats = QueryStats.get_stats()
    assert stats["query_count"] == 0
    assert stats["total_time"] == 0.0
    assert stats["avg_time"] == 0


@pytest.mark.unit
def test_init_db_helpers(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(init_db, "engine", engine)
    monkeypatch.setattr(init_db, "SessionLocal", SessionLocal)
    monkeypatch.setattr(init_db, "hash_password", lambda pwd: f"hashed-{pwd}")

    assert init_db.check_tables_exist() is False
    assert init_db.create_all_tables() is True
    assert init_db.check_tables_exist() is True
    assert init_db.verify_database() is True

    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    assert init_db.create_default_admin() is True

    session = SessionLocal()
    try:
        admin = session.query(User).filter(User.email == "admin@labflow.local").first()
        assert admin is not None
        assert admin.role == RoleEnum.ADMIN
        assert admin.hashed_password == "hashed-admin123"
    finally:
        session.close()

    assert init_db.create_default_tags() is True
    session = SessionLocal()
    try:
        assert session.query(Tag).count() > 0
    finally:
        session.close()
        engine.dispose()


@pytest.mark.unit
def test_analysis_service_list_and_run_tool(test_db, monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = analysis_service.LocalStorage(base_dir=tmpdir)
        file_path = os.path.join(tmpdir, "sample.bin")
        with open(file_path, "wb") as handle:
            handle.write(b"sample")

        file_record = File(
            filename="sample.bin",
            storage_key=file_path,
            file_hash="a" * 64,
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)

        fake = FakeAdapter()
        monkeypatch.setattr(analysis_service, "get_adapter", lambda tool_id: fake)
        monkeypatch.setattr(analysis_service, "list_specs", lambda: [fake.spec])

        service = analysis_service.AnalysisService(test_db, storage=storage)
        tools = service.list_tools()
        assert tools[0]["id"] == "auto"

        result = service.run_tool("auto", file_record.id, parameters={"value": "x"})
        assert result["status"] == "completed"
        assert result["stored"]["conclusion_id"] is not None
        assert result["stored"]["annotation_ids"]


@pytest.mark.unit
def test_script_service_crud_and_execute(test_db):
    user = User(
        username="script_user",
        email="script_user@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    service = ScriptService(test_db)

    script = service.create_script(
        name="test_script",
        content="print('hi')",
        parameters={"x": 1},
        category="analysis",
        created_by_id=user.id,
    )
    assert script.name == "test_script"

    fetched = service.get_script(script.id)
    assert fetched is not None
    assert fetched.id == script.id

    by_name = service.get_script_by_name("test_script")
    assert by_name is not None

    scripts = service.list_scripts(category="analysis")
    assert scripts

    updated = service.update_script(
        script.id,
        name="updated_script",
        content="print('updated')",
        parameters={"y": 2},
        version="1.0.1",
    )
    assert updated.name == "updated_script"
    assert updated.version == "1.0.1"

    execution = service.execute_script(script.id, {"input": "value"}, timeout=1)
    assert execution.status in {"completed", "failed"}

    execution_fetched = service.get_execution(execution.id)
    assert execution_fetched is not None

    exec_list = service.list_executions(script_id=script.id)
    assert exec_list

    assert service.delete_script(script.id) is True


@pytest.mark.unit
def test_script_service_invalid_content(test_db):
    service = ScriptService(test_db)
    with pytest.raises(InvalidScriptError):
        service.create_script(
            name="bad_script",
            content="   ",
            parameters={},
            category="analysis",
            created_by_id=1,
        )

    with pytest.raises(InvalidScriptError):
        service.create_script(
            name="big_script",
            content="x" * (1024 * 1024 + 1),
            parameters={},
            category="analysis",
            created_by_id=1,
        )


@pytest.mark.unit
def test_reasoning_service_chain_crud(test_db):
    user = User(
        username="reasoning_user",
        email="reasoning_user@example.com",
        hashed_password="hashed",
        role=RoleEnum.EDITOR,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReasoningService(test_db, storage=LocalStorage(base_dir=tmpdir))

        nodes = [
            {"node_id": "n1", "node_type": "data_input", "config": {"source": "constant", "value": 1}},
            {"node_id": "n2", "node_type": "output", "inputs": ["n1"], "config": {"format": "raw"}},
        ]

        chain = service.create_chain(
            name="Test Chain",
            description="unit test chain",
            nodes=nodes,
            created_by_id=user.id,
        )
        assert chain.name == "Test Chain"

        fetched = service.get_chain(chain.id)
        assert fetched is not None

        listed = service.list_chains()
        assert listed

        updated = service.update_chain(chain.id, name="Updated Chain")
        assert updated is not None
        assert updated.name == "Updated Chain"

        assert service.delete_chain(chain.id) is True


@pytest.mark.unit
def test_reasoning_service_invalid_chain(test_db):
    service = ReasoningService(test_db, storage=LocalStorage(base_dir="data/managed"))
    with pytest.raises(InvalidChainError):
        service.create_chain(
            name="",
            description="invalid",
            nodes=[],
            created_by_id=1,
        )


@pytest.mark.unit
def test_script_service_cache_invalidation(test_db, monkeypatch):
    service = ScriptService(test_db)
    calls = []

    def record(pattern):
        calls.append(pattern)
        return 0

    monkeypatch.setattr(service.cache, "delete_pattern", record)
    service._invalidate_script_cache()
    service._invalidate_execution_cache("script-1")

    assert "script:*" in calls
    assert "scripts:*" in calls
    assert "script_execution:*" in calls
    assert "script_executions:script-1:*" in calls


@pytest.mark.unit
def test_reasoning_service_execute_chain_paths(test_db):
    user = User(
        username="exec_user",
        email="exec_user@example.com",
        hashed_password="hashed",
        role=RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReasoningService(test_db, storage=LocalStorage(base_dir=tmpdir))
        nodes = [
            {"node_id": "n1", "node_type": "data_input", "config": {"source": "constant", "value": 1}},
            {"node_id": "n2", "node_type": "output", "inputs": ["n1"], "config": {"format": "raw"}},
        ]

        chain = service.create_chain(
            name="Exec Chain",
            description="exec path",
            nodes=nodes,
            created_by_id=user.id,
        )

        def ok_execute_chain(nodes, input_data, timeout):
            return {"status": "completed", "results": {"n1": {"value": 1}}, "errors": []}

        service.engine.execute_chain = ok_execute_chain
        execution = service.execute_chain(chain.id, {"input": "value"}, user.id, timeout=1)
        assert execution.status == "completed"
        assert execution.results

        def boom_execute_chain(nodes, input_data, timeout):
            raise RuntimeError("boom")

        service.engine.execute_chain = boom_execute_chain
        failed = service.execute_chain(chain.id, {"input": "value"}, user.id, timeout=1)
        assert failed.status == "failed"
        assert failed.error_log


@pytest.mark.unit
def test_reasoning_service_history_stats(test_db):
    chain = ReasoningChain(
        name="History Chain",
        description="history",
        nodes=[{"node_id": "n1", "node_type": "data_input", "config": {"source": "constant", "value": 1}}],
        created_by_id=None,
    )
    test_db.add(chain)
    test_db.commit()
    test_db.refresh(chain)

    now = datetime.now(timezone.utc)
    executions = [
        ReasoningExecution(
            chain_id=chain.id,
            status="completed",
            user_id=None,
            input_data={"a": 1},
            results={"ok": True},
            started_at=now,
            completed_at=now,
            execution_time_ms=100,
        ),
        ReasoningExecution(
            chain_id=chain.id,
            status="failed",
            user_id=None,
            input_data={"a": 2},
            results={"ok": False},
            error_log="error",
            started_at=now,
            completed_at=now,
            execution_time_ms=200,
        ),
    ]
    test_db.add_all(executions)
    test_db.commit()

    service = ReasoningService(test_db, storage=LocalStorage(base_dir="data/managed"))
    stats = service.get_execution_history(chain.id, days=7)
    assert stats["total_executions"] == 2
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["avg_execution_time_ms"] == 150
