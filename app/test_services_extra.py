"""
Additional coverage for script_service and reasoning_service.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import models
from app.services.script_service import ScriptService, InvalidScriptError, ScriptServiceError
from app.services.reasoning_service import ReasoningService, ChainNotFoundError, InvalidChainError, ReasoningServiceError


def _create_user(test_db):
    user = models.User(
        username="svc_user",
        email="svc_user@example.com",
        hashed_password="hash",
        role=models.RoleEnum.VIEWER,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _basic_nodes():
    return [
        {"node_id": "n1", "node_type": "data_input", "config": {"source": "constant", "value": 1}},
        {"node_id": "n2", "node_type": "output", "inputs": ["n1"], "config": {"format": "raw"}},
    ]


@pytest.mark.unit
def test_script_service_versions_and_filters(test_db):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script1 = service.create_script(
        name="calc",
        content="print('ok')",
        parameters={"a": 1},
        category="math",
        created_by_id=user.id,
        version="1.0.0",
    )
    script2 = service.create_script(
        name="calc",
        content="print('ok2')",
        parameters={"a": 2},
        category="math",
        created_by_id=user.id,
        version="1.1.0",
    )
    service.create_script(
        name="other",
        content="print('x')",
        parameters={},
        category="misc",
        created_by_id=user.id,
        version="0.1.0",
    )

    latest = service.get_script_by_name("calc")
    assert latest.id == script2.id

    versions = service.list_script_versions("calc")
    assert len(versions) == 2
    assert versions[0].id == script2.id

    math_scripts = service.list_scripts(category="math")
    assert all(s.category == "math" for s in math_scripts)

    assert service.get_script(script1.id) is not None


def test_script_service_update_invalid_content(test_db):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="bad",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )

    with pytest.raises(InvalidScriptError):
        service.update_script(script.id, content=" ")


def test_script_service_update_fields(test_db):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="update",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )

    updated = service.update_script(
        script.id,
        name="updated",
        parameters={"x": 1},
        category="tools",
        version="2.0.0",
    )
    assert updated.name == "updated"
    assert updated.category == "tools"
    assert updated.version == "2.0.0"


def test_script_service_execute_failure(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="fail",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )

    def raise_exec(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_execute_script_content", raise_exec)
    execution = service.execute_script(script.id, {"x": 1})
    assert execution.status == "failed"
    assert execution.error


def test_script_service_cache_and_error_paths(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="cache",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )

    monkeypatch.setattr(service.cache, "get", lambda key: script)
    cached = service.get_script(script.id)
    assert cached.id == script.id

    def raise_db(*args, **kwargs):
        raise SQLAlchemyError("db fail")

    monkeypatch.setattr(test_db, "execute", raise_db)
    assert service.get_script_by_name("cache") is None
    assert service.list_scripts() == []
    assert service.list_script_versions("cache") == []


def test_script_service_execute_and_cache_execution(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="exec_ok",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )
    execution = service.execute_script(script.id, {"x": 1})
    assert execution.status == "completed"

    monkeypatch.setattr(service.cache, "get", lambda key: execution)
    cached_exec = service.get_execution(execution.id)
    assert cached_exec.id == execution.id


def test_script_service_execute_db_error(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="exec_fail",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )

    def fail_commit():
        raise SQLAlchemyError("db fail")

    monkeypatch.setattr(test_db, "commit", fail_commit)
    with pytest.raises(ScriptServiceError):
        service.execute_script(script.id, {"x": 1})


def test_script_service_delete_missing(test_db):
    service = ScriptService(test_db)
    assert service.delete_script(uuid4()) is False


def test_script_service_list_executions_filters(test_db):
    user = _create_user(test_db)
    service = ScriptService(test_db)

    script = service.create_script(
        name="exec",
        content="print('ok')",
        parameters={},
        category="misc",
        created_by_id=user.id,
    )
    execution = service.execute_script(script.id, {"x": 1})

    all_exec = service.list_executions(script_id=script.id)
    assert len(all_exec) >= 1

    completed = service.list_executions(script_id=script.id, status="completed")
    assert any(e.id == execution.id for e in completed)


def test_script_service_large_content_validation(test_db):
    service = ScriptService(test_db)
    with pytest.raises(InvalidScriptError):
        service._validate_script_content("x" * (1024 * 1024 + 1))


@pytest.mark.unit
def test_reasoning_service_template_only_and_errors(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ReasoningService(test_db)

    chain1 = service.create_chain(
        name="chain1",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
        is_template=True,
    )
    service.create_chain(
        name="chain2",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
        is_template=False,
    )

    templates = service.list_chains(template_only=True)
    assert any(c.id == chain1.id for c in templates)
    assert all(c.is_template for c in templates)

    with pytest.raises(ChainNotFoundError):
        service.update_chain(uuid4(), name="missing")

    with pytest.raises(ChainNotFoundError):
        service.execute_chain(uuid4(), {}, user_id=user.id)

    def raise_engine(*args, **kwargs):
        raise RuntimeError("engine boom")

    monkeypatch.setattr(service.engine, "execute_chain", raise_engine)
    execution = service.execute_chain(chain1.id, {}, user_id=user.id)
    assert execution.status == "failed"
    assert execution.error_log


def test_reasoning_service_cache_and_db_errors(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ReasoningService(test_db)

    chain = service.create_chain(
        name="cached",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
    )

    monkeypatch.setattr(service.cache, "get", lambda key: chain)
    cached_chain = service.get_chain(chain.id)
    assert cached_chain.id == chain.id

    def raise_db(*args, **kwargs):
        raise SQLAlchemyError("db fail")

    monkeypatch.setattr(test_db, "execute", raise_db)
    assert service.list_chains() == []
    assert service.list_executions() == []


def test_reasoning_service_create_chain_db_error(test_db, monkeypatch):
    service = ReasoningService(test_db)

    def fail_commit():
        raise SQLAlchemyError("db fail")

    monkeypatch.setattr(test_db, "commit", fail_commit)
    with pytest.raises(ReasoningServiceError):
        service.create_chain(
            name="bad",
            description="",
            nodes=_basic_nodes(),
            created_by_id=1,
        )


def test_reasoning_service_helpers_and_db_errors(test_db, monkeypatch):
    service = ReasoningService(test_db)

    with pytest.raises(InvalidChainError):
        service._normalize_nodes(123)

    assert service._normalize_json_value("{\"x\": 1}") == {"x": 1}
    assert service._normalize_json_value("not json") == "not json"

    assert service._normalize_json_value([1, 2]) == [1, 2]

    assert service._normalize_nodes('[{"node_id": "n1", "node_type": "data_input", "config": {"source": "constant", "value": 1}}]')

    bad = service._stringify_errors({"x", "y"})
    assert isinstance(bad, str)

    assert service._stringify_errors("oops") == "oops"

    def raise_db(*args, **kwargs):
        raise SQLAlchemyError("db fail")

    monkeypatch.setattr(test_db, "execute", raise_db)
    assert service.get_execution(uuid4()) is None
    assert service.get_execution_history(uuid4()) == {}


def test_reasoning_service_execute_with_errors(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ReasoningService(test_db)

    chain = service.create_chain(
        name="errors",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
    )

    def fake_execute(*args, **kwargs):
        return {"status": "completed", "results": {"x": 1}, "errors": {"e": "x"}}

    monkeypatch.setattr(service.engine, "execute_chain", fake_execute)
    execution = service.execute_chain(chain.id, {}, user_id=user.id)
    assert execution.status == "completed"
    assert execution.error_log


def test_reasoning_service_delete_chain_success(test_db):
    user = _create_user(test_db)
    service = ReasoningService(test_db)

    chain = service.create_chain(
        name="delete",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
    )
    assert service.delete_chain(chain.id) is True


def test_reasoning_service_list_executions_success(test_db):
    user = _create_user(test_db)
    service = ReasoningService(test_db)

    chain = service.create_chain(
        name="execs",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
    )

    execution = service.execute_chain(chain.id, {}, user_id=user.id)
    executions = service.list_executions(chain_id=chain.id, status=execution.status)
    assert any(e.id == execution.id for e in executions)


def test_reasoning_service_get_execution_cached(test_db, monkeypatch):
    user = _create_user(test_db)
    service = ReasoningService(test_db)

    chain = service.create_chain(
        name="exec_cache",
        description="",
        nodes=_basic_nodes(),
        created_by_id=user.id,
    )

    execution = service.execute_chain(chain.id, {}, user_id=user.id)
    monkeypatch.setattr(service.cache, "get", lambda key: execution)
    cached = service.get_execution(execution.id)
    assert cached.id == execution.id
