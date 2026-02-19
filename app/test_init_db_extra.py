"""
Extra coverage for init_db helpers.
"""

import pytest

from app import models
import app.init_db as init_db


@pytest.mark.unit
def test_create_all_tables_failure(monkeypatch):
    def fail_create_all(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(init_db.Base.metadata, "create_all", fail_create_all)
    assert init_db.create_all_tables() is False


@pytest.mark.unit
def test_check_tables_exist_true(monkeypatch):
    class FakeInspector:
        def get_table_names(self):
            return ["users", "files"]

    monkeypatch.setattr(init_db, "inspect", lambda engine: FakeInspector())
    assert init_db.check_tables_exist() is True


@pytest.mark.unit
def test_create_default_admin_existing(test_db, monkeypatch):
    user = models.User(
        username="admin",
        email="admin@labflow.local",
        hashed_password="hash",
        role=models.RoleEnum.ADMIN,
        is_active=1,
    )
    test_db.add(user)
    test_db.commit()

    monkeypatch.setattr(init_db, "hash_password", lambda password: "hash")
    monkeypatch.setattr(init_db, "SessionLocal", lambda: test_db)
    monkeypatch.setattr(test_db, "close", lambda: None)

    assert init_db.create_default_admin() is True


@pytest.mark.unit
def test_create_default_admin_error(monkeypatch):
    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class FakeSession:
        def __init__(self):
            self.rollback_called = False

        def query(self, *args, **kwargs):
            return FakeQuery()

        def add(self, *args, **kwargs):
            pass

        def commit(self):
            raise RuntimeError("commit fail")

        def rollback(self):
            self.rollback_called = True

        def close(self):
            pass

    session = FakeSession()
    monkeypatch.setattr(init_db, "hash_password", lambda password: "hash")
    monkeypatch.setattr(init_db, "SessionLocal", lambda: session)

    assert init_db.create_default_admin() is False
    assert session.rollback_called is True


@pytest.mark.unit
def test_create_default_tags_existing(test_db, monkeypatch):
    tag = models.Tag(name="existing")
    test_db.add(tag)
    test_db.commit()

    monkeypatch.setattr(init_db, "SessionLocal", lambda: test_db)
    monkeypatch.setattr(test_db, "close", lambda: None)

    assert init_db.create_default_tags() is True


@pytest.mark.unit
def test_create_default_tags_error(monkeypatch):
    class FakeQuery:
        def count(self):
            return 0

    class FakeSession:
        def __init__(self):
            self.rollback_called = False

        def query(self, *args, **kwargs):
            return FakeQuery()

        def add(self, *args, **kwargs):
            pass

        def commit(self):
            raise RuntimeError("commit fail")

        def rollback(self):
            self.rollback_called = True

        def close(self):
            pass

    session = FakeSession()
    monkeypatch.setattr(init_db, "SessionLocal", lambda: session)

    assert init_db.create_default_tags() is False
    assert session.rollback_called is True


@pytest.mark.unit
def test_create_default_tags_invalid_name(monkeypatch):
    class FakeQuery:
        def count(self):
            return 0

    class FakeSession:
        def __init__(self):
            self.added = []

        def query(self, *args, **kwargs):
            return FakeQuery()

        def add(self, item):
            self.added.append(item)

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    class FakeTag:
        def __init__(self, name):
            if name == "XRD":
                raise ValueError("bad")
            self.name = name

    session = FakeSession()
    monkeypatch.setattr(init_db, "SessionLocal", lambda: session)
    monkeypatch.setattr(models, "Tag", FakeTag)

    assert init_db.create_default_tags() is True
    assert session.added


@pytest.mark.unit
def test_verify_database_failure(monkeypatch):
    class FakeConn:
        def __enter__(self):
            raise RuntimeError("no connect")

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(init_db, "engine", FakeEngine())
    assert init_db.verify_database() is False


@pytest.mark.unit
def test_main_exits_on_failed_verify(monkeypatch):
    monkeypatch.setattr(init_db, "verify_database", lambda: False)
    with pytest.raises(SystemExit):
        init_db.main()


@pytest.mark.unit
def test_main_success_flow(monkeypatch):
    calls = {"admin": 0, "tags": 0}

    monkeypatch.setattr(init_db, "verify_database", lambda: True)
    monkeypatch.setattr(init_db, "check_tables_exist", lambda: False)
    monkeypatch.setattr(init_db, "create_all_tables", lambda: True)

    def mark_admin():
        calls["admin"] += 1
        return True

    def mark_tags():
        calls["tags"] += 1
        return True

    monkeypatch.setattr(init_db, "create_default_admin", mark_admin)
    monkeypatch.setattr(init_db, "create_default_tags", mark_tags)

    init_db.main()
    assert calls["admin"] == 1
    assert calls["tags"] == 1
