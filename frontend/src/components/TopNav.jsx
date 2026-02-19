import React, { useEffect, useState } from 'react';
import { Button, Tag } from 'antd';
import { NavLink, useNavigate } from 'react-router-dom';
import { auth } from '../api/client.js';
import { useTranslation, LanguageSwitcher } from '../i18n.jsx';

export default function TopNav() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const fallbackOffline =
    String(import.meta.env.VITE_OFFLINE_MODE || 'true')
      .toLowerCase()
      .trim() === 'true';
  const [offlineMode, setOfflineMode] = useState(fallbackOffline);
  const [runtimeMode, setRuntimeMode] = useState('local');
  const token = auth.getToken();
  const offlineSession = auth.getOffline();

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
    fetch(`${apiBase}/health`)
      .then(response => response.json())
      .then(data => {
        if (typeof data?.offline_mode === 'boolean') {
          setOfflineMode(data.offline_mode);
        }
        if (typeof data?.mode === 'string' && data.mode.trim()) {
          setRuntimeMode(data.mode.trim());
        }
      })
      .catch(() => {
        setOfflineMode(fallbackOffline);
      });
  }, [fallbackOffline]);

  const handleLogout = () => {
    auth.clearToken();
    auth.setOffline(false);
    navigate('/login');
  };

  const handleLogin = () => {
    navigate('/login');
  };

  return (
    <div className="app-topbar">
      <div className="app-title">
        LabFlow <span>Reasoning Studio</span>
        {offlineMode ? <Tag color="#f39b2f">{t('auth.local_only')}</Tag> : null}
        <Tag color="#2db7f5">{runtimeMode}</Tag>
      </div>
      <div className="app-nav">
        <NavLink to="/" end>
          {t('navigation.reasoning')}
        </NavLink>
        <NavLink to="/templates">{t('navigation.templates')}</NavLink>
        <NavLink to="/analysis/tools">{t('navigation.analysis')}</NavLink>
        <NavLink to="/analysis/run">{t('common.submit')}</NavLink>
        {offlineMode && !token && offlineSession ? (
          <Tag color="#f39b2f">{t('auth.offline_mode')}</Tag>
        ) : null}
        <LanguageSwitcher className="language-switcher-nav" />
        {token ? (
          <Button size="small" onClick={handleLogout}>
            {t('common.logout')}
          </Button>
        ) : (
          <Button size="small" onClick={handleLogin}>
            {t('common.login')}
          </Button>
        )}
      </div>
    </div>
  );
}
