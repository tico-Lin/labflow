"""
Tests for logging_config utilities.
"""

import json
import logging

from app import logging_config


def test_structured_formatter_and_text_formatter():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.custom_fields = {"key": "value"}

    structured = logging_config.StructuredFormatter().format(record)
    parsed = json.loads(structured)
    assert parsed["message"] == "hello"
    assert parsed["key"] == "value"

    text = logging_config.TextFormatter().format(record)
    assert "hello" in text


def test_configure_logging_and_log_with_context(monkeypatch):
    logging_config.configure_logging(level="INFO", log_format="json", log_file=None)
    logger = logging_config.get_logger("test_logger")
    logging_config.log_with_context(logger, "info", "context", user_id=1)


def test_configure_logging_text_format(monkeypatch):
    logging_config.configure_logging(level="INFO", log_format="text", log_file=None)


def test_log_stats_and_handler():
    logging_config.LogStats.reset()
    handler = logging_config.StatsHandler()
    record = logging.LogRecord(
        name="stats",
        level=logging.WARNING,
        pathname=__file__,
        lineno=20,
        msg="warn",
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    stats = logging_config.LogStats.get_stats()
    assert stats["WARNING"] == 1

    logging_config.LogStats.record("UNKNOWN")


def test_ensure_log_directory_failure(monkeypatch):
    monkeypatch.setattr(logging_config, "LOG_FILE", "logs/test.log")
    monkeypatch.setattr(logging_config.os.path, "exists", lambda path: False)
    monkeypatch.setattr(logging_config.os, "makedirs", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    logging_config._ensure_log_directory()


def test_configure_logging_file_handler_failure(monkeypatch):
    def fail_handler(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(logging_config.logging.handlers, "RotatingFileHandler", fail_handler)
    logging_config.configure_logging(level="INFO", log_format="json", log_file="logs/test.log")


def test_setup_module_loggers():
    logging_config.setup_module_loggers()
