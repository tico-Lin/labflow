import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import 'antd/dist/reset.css';
import 'reactflow/dist/style.css';
import './styles.css';
import App from './App.jsx';
import { I18nProvider } from './i18n.jsx';

const bootBanner = document.getElementById('boot-banner');
if (bootBanner) {
  bootBanner.remove();
}

const showFatal = message => {
  const existing = document.getElementById('boot-error');
  const el = existing || document.createElement('div');
  el.id = 'boot-error';
  el.textContent = message;
  el.style.cssText =
    'position:fixed;top:12px;left:12px;right:12px;z-index:9999;' +
    'padding:12px 16px;border:1px solid rgba(255,140,0,0.5);' +
    'border-radius:8px;background:rgba(20,20,20,0.9);' +
    'color:#ffd4a3;font-family:Space Grotesk,system-ui,sans-serif;font-size:13px;';
  if (!existing) {
    document.body.prepend(el);
  }
};

window.addEventListener('error', event => {
  showFatal(`JS error: ${event.message}`);
});

window.addEventListener('unhandledrejection', event => {
  const reason = event.reason && event.reason.message ? event.reason.message : String(event.reason);
  showFatal(`Promise error: ${reason}`);
});

const rootEl = document.getElementById('root');
if (rootEl) {
  rootEl.textContent = 'React booting...';
}

// 在 React 渲染之前立即应用主题，避免闪烁
(() => {
  const DEFAULT_THEME = 'dark';
  const savedTheme = (() => {
    try {
      const saved = localStorage.getItem('labflow_theme');
      return saved === 'dark' || saved === 'light' ? saved : DEFAULT_THEME;
    } catch {
      return DEFAULT_THEME;
    }
  })();

  const root = document.documentElement;
  if (savedTheme === 'light') {
    root.setAttribute('data-theme', 'light');
  } else {
    root.removeAttribute('data-theme');
  }
})();

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <I18nProvider>
        <App />
      </I18nProvider>
    </BrowserRouter>
  </React.StrictMode>
);
