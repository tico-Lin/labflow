"""
Tests for app.i18n utilities.
"""

import json
from pathlib import Path

from app import i18n
from app.i18n import I18nManager, Translator


def _write_locale(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")


def test_i18n_manager_loads_locales(tmp_path: Path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()

    _write_locale(
        locales_dir / "zh.json",
        {"common": {"welcome": "hello", "name": "hi {user}"}},
    )
    _write_locale(
        locales_dir / "en.json",
        {"common": {"welcome": "welcome"}},
    )

    manager = I18nManager(locales_dir=str(locales_dir))
    assert sorted(manager.get_available_locales()) == ["en", "zh"]

    translator = manager.get_translator("en")
    assert translator("common.welcome") == "welcome"


def test_translator_fallbacks_and_formatting(tmp_path: Path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()

    _write_locale(
        locales_dir / "zh.json",
        {"common": {"welcome": "hello", "name": "hi {user}"}},
    )

    manager = I18nManager(locales_dir=str(locales_dir))
    translator = manager.get_translator("missing")

    assert translator("common.welcome") == "hello"
    assert translator("common.unknown") == "common.unknown"
    assert translator("common.name", user="lab") == "hi lab"
    assert translator("common.name") == "hi {user}"


def test_add_translation_deep_merge(tmp_path: Path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()

    _write_locale(
        locales_dir / "zh.json",
        {"common": {"nested": {"a": "1"}}},
    )

    manager = I18nManager(locales_dir=str(locales_dir))
    manager.add_translation("zh", {"common": {"nested": {"b": "2"}}})

    translator = manager.get_translator("zh")
    assert translator("common.nested.a") == "1"
    assert translator("common.nested.b") == "2"


def test_translator_callable():
    translator = Translator("en", {"common": {"welcome": "hello"}})
    assert translator("common.welcome") == "hello"


def test_i18n_manager_missing_dir(tmp_path: Path):
    missing_dir = tmp_path / "missing"
    manager = I18nManager(locales_dir=str(missing_dir))
    assert manager.get_available_locales() == []


def test_i18n_manager_invalid_json(tmp_path: Path, capsys):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()
    (locales_dir / "bad.json").write_text("{bad json", encoding="utf-8")

    manager = I18nManager(locales_dir=str(locales_dir))
    captured = capsys.readouterr()
    assert "Error loading translation file" in captured.out
    assert manager.get_available_locales() == []


def test_get_i18n_manager_singleton(tmp_path: Path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()
    _write_locale(locales_dir / "zh.json", {"common": {"welcome": "hello"}})

    i18n._i18n_manager = None
    manager = i18n.get_i18n_manager()
    manager.locales_dir = locales_dir
    manager.translations = {"zh": {"common": {"welcome": "hello"}}}

    assert i18n.get_i18n_manager() is manager
    assert i18n.get_translator("zh")("common.welcome") == "hello"
    assert i18n.get_available_locales() == ["zh"]


def test_add_translation_new_locale(tmp_path: Path):
    locales_dir = tmp_path / "locales"
    locales_dir.mkdir()

    manager = I18nManager(locales_dir=str(locales_dir))
    manager.add_translation("fr", {"common": {"welcome": "salut"}})

    translator = manager.get_translator("fr")
    assert translator("common.welcome") == "salut"
