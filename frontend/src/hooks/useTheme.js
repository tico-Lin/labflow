/**
 * 主题管理 Hook
 * 支持深色和浅色主题切换
 */

import { useState, useEffect, useCallback } from 'react';

const THEMES = {
  dark: 'dark',
  light: 'light',
};

const DEFAULT_THEME = 'dark';

// 从 localStorage 获取保存的主题
const getSavedTheme = () => {
  try {
    const saved = localStorage.getItem('labflow_theme');
    if (saved && Object.values(THEMES).includes(saved)) {
      return saved;
    }
  } catch (e) {
    console.warn('Failed to read theme from localStorage:', e);
  }
  return DEFAULT_THEME;
};

// 保存主题到 localStorage
const saveTheme = theme => {
  try {
    localStorage.setItem('labflow_theme', theme);
  } catch (e) {
    console.warn('Failed to save theme to localStorage:', e);
  }
};

// 应用主题到 DOM
const applyTheme = theme => {
  const root = document.documentElement;
  if (theme === THEMES.light) {
    root.setAttribute('data-theme', 'light');
  } else {
    root.removeAttribute('data-theme');
  }
};

export function useTheme() {
  const savedTheme = getSavedTheme();
  const [theme, setThemeState] = useState(savedTheme);

  // 当主题状态变化时，应用主题
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // 切换主题
  const setTheme = useCallback(newTheme => {
    if (Object.values(THEMES).includes(newTheme)) {
      setThemeState(newTheme);
      saveTheme(newTheme);
      applyTheme(newTheme);
    }
  }, []);

  // 切换主题（如果当前是深色则切换到浅色，反之亦然）
  const toggleTheme = useCallback(() => {
    const newTheme = theme === THEMES.dark ? THEMES.light : THEMES.dark;
    setTheme(newTheme);
  }, [theme, setTheme]);

  return {
    theme,
    setTheme,
    toggleTheme,
    themes: THEMES,
  };
}

export default useTheme;
