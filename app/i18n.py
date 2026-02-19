"""
LabFlow 國際化 (i18n) 模塊

提供多語言支持，包括：
- 中文（簡體和繁體）
- 英文
- 可擴展的其他語言接口

使用方式：
    from app.i18n import get_translator

    t = get_translator("zh")
    print(t("common.welcome"))  # 返回中文翻譯

    t = get_translator("en")
    print(t("common.welcome"))  # 返回英文翻譯
"""

import os
import json
from typing import Dict, Any, Optional, Callable
from pathlib import Path


class Translator:
    """翻譯器類，負責加載和管理特定語言的翻譯"""

    def __init__(self, locale: str, translations: Dict[str, Any]):
        self.locale = locale
        self.translations = translations

    def translate(self, key: str, **kwargs) -> str:
        """
        根據鍵獲取翻譯文本

        Args:
            key: 翻譯鍵，支持點分隔的嵌套結構 (例如: "common.welcome")
            **kwargs: 用於格式化翻譯文本的參數

        Returns:
            翻譯後的文本，如果未找到則返回原始鍵
        """
        keys = key.split(".")
        value = self.translations

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return key  # 未找到翻譯，返回原始鍵

        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value

        return key

    def __call__(self, key: str, **kwargs) -> str:
        """使 Translator 實例可調用"""
        return self.translate(key, **kwargs)


class I18nManager:
    """國際化管理器，負責加載和管理所有語言的翻譯"""

    def __init__(self, locales_dir: Optional[str] = None):
        """
        初始化 i18n 管理器

        Args:
            locales_dir: 翻譯文件所在目錄，默認為 app/locales
        """
        if locales_dir is None:
            locales_dir = os.path.join(
                os.path.dirname(__file__),
                "locales"
            )

        self.locales_dir = Path(locales_dir)
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.default_locale = "zh"
        self._load_all_translations()

    def _load_all_translations(self):
        """加載所有可用的翻譯文件"""
        if not self.locales_dir.exists():
            return

        for locale_file in self.locales_dir.glob("*.json"):
            locale = locale_file.stem
            try:
                with open(locale_file, "r", encoding="utf-8") as f:
                    self.translations[locale] = json.load(f)
            except Exception as e:
                print(f"Error loading translation file {locale_file}: {e}")

    def get_translator(self, locale: Optional[str] = None) -> Translator:
        """
        獲取指定語言的翻譯器

        Args:
            locale: 語言代碼，例如 "zh", "en"。如果為 None，使用默認語言

        Returns:
            Translator 實例
        """
        if locale is None:
            locale = self.default_locale

        translations = self.translations.get(
            locale,
            self.translations.get(self.default_locale, {})
        )

        return Translator(locale, translations)

    def get_available_locales(self) -> list[str]:
        """獲取所有可用的語言代碼"""
        return list(self.translations.keys())

    def add_translation(self, locale: str, translations: Dict[str, Any]):
        """
        動態添加或更新翻譯

        Args:
            locale: 語言代碼
            translations: 翻譯字典
        """
        if locale in self.translations:
            # 深度合併翻譯
            self._deep_merge(self.translations[locale], translations)
        else:
            self.translations[locale] = translations

    def _deep_merge(self, target: dict, source: dict):
        """深度合併兩個字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value


# 全局 i18n 管理器實例
_i18n_manager = None


def get_i18n_manager() -> I18nManager:
    """獲取全局 i18n 管理器實例（單例模式）"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def get_translator(locale: Optional[str] = None) -> Translator:
    """
    獲取指定語言的翻譯器（便捷函數）

    Args:
        locale: 語言代碼，例如 "zh", "en"

    Returns:
        Translator 實例
    """
    return get_i18n_manager().get_translator(locale)


def get_available_locales() -> list[str]:
    """獲取所有可用的語言代碼（便捷函數）"""
    return get_i18n_manager().get_available_locales()
