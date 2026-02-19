/**
 * LabFlow 前端國際化 (i18n) 模塊
 *
 * 提供：
 * - I18nProvider: React 上下文提供者
 * - useTranslation: 獲取翻譯函數的 Hook
 * - useLanguage: 獲取和設置當前語言的 Hook
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from './api/client';

// 翻譯上下文
const I18nContext = createContext(null);

// 支持的語言列表
export const SUPPORTED_LOCALES = {
  zh: '中文',
  en: 'English',
};

// 默認語言
const DEFAULT_LOCALE = 'zh';

// 從 localStorage 獲取保存的語言設置
const getSavedLocale = () => {
  try {
    const saved = localStorage.getItem('labflow_locale');
    if (saved && SUPPORTED_LOCALES[saved]) {
      return saved;
    }
  } catch (e) {
    console.warn('Failed to read locale from localStorage:', e);
  }
  return DEFAULT_LOCALE;
};

// 保存語言設置到 localStorage
const saveLocale = locale => {
  try {
    localStorage.setItem('labflow_locale', locale);
  } catch (e) {
    console.warn('Failed to save locale to localStorage:', e);
  }
};

/**
 * I18n Provider 組件
 *
 * 使用方式：
 * <I18nProvider>
 *   <App />
 * </I18nProvider>
 */
export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(getSavedLocale());
  const [translations, setTranslations] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 加載翻譯數據
  const loadTranslations = useCallback(async targetLocale => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/i18n/translations/${targetLocale}`);

      if (!response.ok) {
        throw new Error(`Failed to load translations for ${targetLocale}`);
      }

      const data = await response.json();
      setTranslations(data.translations);
      setLoading(false);
    } catch (err) {
      console.error('Error loading translations:', err);
      setError(err.message);
      setLoading(false);

      // 如果加載失敗，使用空對象作為後備
      setTranslations({});
    }
  }, []);

  // 切換語言
  const setLocale = useCallback(
    newLocale => {
      if (SUPPORTED_LOCALES[newLocale]) {
        setLocaleState(newLocale);
        saveLocale(newLocale);
        loadTranslations(newLocale);
      }
    },
    [loadTranslations]
  );

  // 初始加載翻譯
  useEffect(() => {
    loadTranslations(locale);
  }, []);

  // 翻譯函數
  const translate = useCallback(
    (key, params = {}) => {
      // 根據點分隔的鍵查找嵌套翻譯
      const keys = key.split('.');
      let value = translations;

      for (const k of keys) {
        if (value && typeof value === 'object' && k in value) {
          value = value[k];
        } else {
          // 未找到翻譯，返回鍵本身
          return key;
        }
      }

      // 如果是字符串，進行參數替換
      if (typeof value === 'string') {
        return value.replace(/\{(\w+)\}/g, (match, paramKey) => {
          return params[paramKey] !== undefined ? params[paramKey] : match;
        });
      }

      return key;
    },
    [translations]
  );

  const value = {
    locale,
    setLocale,
    translations,
    translate,
    loading,
    error,
    t: translate, // 簡寫別名
  };

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

/**
 * 使用翻譯的 Hook
 *
 * 使用方式：
 * const { t } = useTranslation();
 * <h1>{t('common.welcome')}</h1>
 */
export function useTranslation() {
  const context = useContext(I18nContext);

  if (!context) {
    throw new Error('useTranslation must be used within I18nProvider');
  }

  return {
    t: context.translate,
    translate: context.translate,
    loading: context.loading,
    error: context.error,
  };
}

/**
 * 使用語言設置的 Hook
 *
 * 使用方式：
 * const { locale, setLocale, locales } = useLanguage();
 */
export function useLanguage() {
  const context = useContext(I18nContext);

  if (!context) {
    throw new Error('useLanguage must be used within I18nProvider');
  }

  return {
    locale: context.locale,
    setLocale: context.setLocale,
    locales: SUPPORTED_LOCALES,
    loading: context.loading,
    error: context.error,
  };
}

/**
 * Trans 組件 - 用於在 JSX 中進行翻譯
 *
 * 使用方式：
 * <Trans i18nKey="common.welcome" />
 * <Trans i18nKey="common.selected_count" count={5} />
 */
export function Trans({ i18nKey, ...params }) {
  const { t } = useTranslation();
  return <>{t(i18nKey, params)}</>;
}

/**
 * 語言切換器組件
 *
 * 使用方式：
 * <LanguageSwitcher />
 */
export function LanguageSwitcher({ className = '' }) {
  const { locale, setLocale, locales } = useLanguage();

  return (
    <select
      value={locale}
      onChange={e => setLocale(e.target.value)}
      className={`language-switcher ${className}`}
      aria-label="Select Language"
    >
      {Object.entries(locales).map(([code, name]) => (
        <option key={code} value={code}>
          {name}
        </option>
      ))}
    </select>
  );
}

export default I18nProvider;
