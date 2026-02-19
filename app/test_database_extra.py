"""
Extra tests for database helpers.
"""

from app import database


def test_get_db_closes_session(monkeypatch):
    closed = {"value": False}

    class FakeSession:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(database, "SessionLocal", lambda: FakeSession())

    gen = database.get_db()
    session = next(gen)
    assert isinstance(session, FakeSession)
    gen.close()

    assert closed["value"] is True
