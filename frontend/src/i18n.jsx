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
import fallbackZh from './locales/zh.json';
import fallbackEn from './locales/en.json';

// 翻譯上下文
const I18nContext = createContext(null);

// 支持的語言列表
export const SUPPORTED_LOCALES = {
  zh: '中文',
  en: 'English',
};

// 默認語言
const DEFAULT_LOCALE = 'zh';

const LOCAL_TRANSLATIONS = {
  zh: fallbackZh,
  en: fallbackEn,
};

const getNestedValue = (source, key) => {
  if (!source) {
    return undefined;
  }
  const keys = key.split('.');
  let value = source;
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      return undefined;
    }
  }
  return value;
};

const mergeTranslations = (base, override) => {
  if (!override || typeof override !== 'object') {
    return base || {};
  }
  const result = Array.isArray(base) ? [...base] : { ...(base || {}) };
  Object.keys(override).forEach(key => {
    const baseValue = base ? base[key] : undefined;
    const overrideValue = override[key];
    if (overrideValue && typeof overrideValue === 'object' && !Array.isArray(overrideValue)) {
      result[key] = mergeTranslations(
        baseValue && typeof baseValue === 'object' ? baseValue : {},
        overrideValue
      );
    } else {
      result[key] = overrideValue;
    }
  });
  return result;
};

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

  // 加載翻譯數據（包含重試機制）
  const loadTranslations = useCallback(async targetLocale => {
    const maxRetries = 3;
    let retryCount = 0;
    let currentLocale = targetLocale;

    const tryLoad = async () => {
      try {
        setLoading(true);
        setError(null);
        setTranslations(
          LOCAL_TRANSLATIONS[currentLocale] || LOCAL_TRANSLATIONS[DEFAULT_LOCALE] || {}
        );

        const response = await fetch(`${API_BASE_URL}/i18n/translations/${currentLocale}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          throw new Error(`Failed to load translations for ${currentLocale}: ${response.status}`);
        }

        const data = await response.json();
        const merged = mergeTranslations(
          LOCAL_TRANSLATIONS[currentLocale] || LOCAL_TRANSLATIONS[DEFAULT_LOCALE] || {},
          data.translations || {}
        );
        setTranslations(merged);
        setLoading(false);
        return true;
      } catch (err) {
        retryCount += 1;
        console.error(`Error loading translations (attempt ${retryCount}):`, err);

        if (retryCount < maxRetries) {
          // 等待後重試
          await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
          return tryLoad();
        } else {
          // 重試失敗，使用备用翻译或空对象
          const fallback =
            LOCAL_TRANSLATIONS[currentLocale] || LOCAL_TRANSLATIONS[DEFAULT_LOCALE] || {};
          setError(err.message);
          setLoading(false);

          // 嘗試從 fallback locale 加載
          if (currentLocale !== DEFAULT_LOCALE) {
            console.warn(`Falling back to ${DEFAULT_LOCALE} locale`);
            currentLocale = DEFAULT_LOCALE;
            retryCount = 0;
            return tryLoad();
          }

          // 如果加載失敗，使用空對象作為後備
          setTranslations(fallback);
          return false;
        }
      }
    };

    return tryLoad();
  }, []);

  // 切換語言
  const setLocale = useCallback(
    newLocale => {
      if (SUPPORTED_LOCALES[newLocale]) {
        setLocaleState(newLocale);
        saveLocale(newLocale);
        setTranslations(LOCAL_TRANSLATIONS[newLocale] || LOCAL_TRANSLATIONS[DEFAULT_LOCALE] || {});
        loadTranslations(newLocale);
      }
    },
    [loadTranslations]
  );

  // 初始加載翻譯
  useEffect(() => {
    setTranslations(LOCAL_TRANSLATIONS[locale] || LOCAL_TRANSLATIONS[DEFAULT_LOCALE] || {});
    loadTranslations(locale);
  }, [locale, loadTranslations]);

  // 应用启动时同步语言到 Electron
  useEffect(() => {
    if (window.labflow && window.labflow.setLanguage) {
      try {
        window.labflow.setLanguage(locale).then(() => {
          console.log(`[i18n] Synced language to Electron: ${locale}`);
        }).catch((error) => {
          console.warn('[i18n] Could not sync language to Electron:', error);
        });
      } catch (error) {
        console.warn('[i18n] Could not sync language to Electron:', error);
      }
    }
  }, [locale]);

  // 翻譯函數
  const translate = useCallback(
    (key, params = {}) => {
      // 根據點分隔的鍵查找嵌套翻譯
      let value = getNestedValue(translations, key);
      if (value === undefined) {
        value = getNestedValue(LOCAL_TRANSLATIONS[locale], key);
      }
      if (value === undefined) {
        value = getNestedValue(LOCAL_TRANSLATIONS[DEFAULT_LOCALE], key);
      }
      if (value === undefined) {
        return key;
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

  const handleLanguageChange = async newLocale => {
    setLocale(newLocale);

    // 如果在 Electron 環境中，保存語言偏好
    if (window.labflow && window.labflow.setLanguage) {
      try {
        await window.labflow.setLanguage(newLocale);
      } catch (error) {
        console.warn('Failed to save language preference to Electron:', error);
      }
    }
  };

  return (
    <select
      value={locale}
      onChange={e => handleLanguageChange(e.target.value)}
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
