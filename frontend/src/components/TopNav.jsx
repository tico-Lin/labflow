import React, { useEffect, useState } from 'react';
import { Button, Tag, Dropdown } from 'antd';
import { SunOutlined, BgColorsOutlined } from '@ant-design/icons';
import { NavLink, useNavigate } from 'react-router-dom';
import { auth } from '../api/client.js';
import { useTranslation, LanguageSwitcher } from '../i18n.jsx';
import { useTheme } from '../hooks/useTheme.js';

export default function TopNav() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { toggleTheme, theme } = useTheme();
  const fallbackOffline =
    String(import.meta.env.VITE_OFFLINE_MODE || 'true')
      .toLowerCase()
      .trim() === 'true';
  const [offlineMode, setOfflineMode] = useState(fallbackOffline);
  const [runtimeMode, setRuntimeMode] = useState('local');
  const token = auth.getToken();
  const offlineSession = auth.getOffline();

  const themeMenuItems = [
    {
      key: 'dark',
      label: (
        <span>
          <BgColorsOutlined style={{ marginRight: '8px' }} />
          {t('common.dark_theme') || 'Dark Theme'}
        </span>
      ),
      onClick: () => {
        if (theme !== 'dark') toggleTheme();
      },
    },
    {
      key: 'light',
      label: (
        <span>
          <SunOutlined style={{ marginRight: '8px' }} />
          {t('common.light_theme') || 'Light Theme'}
        </span>
      ),
      onClick: () => {
        if (theme !== 'light') toggleTheme();
      },
    },
  ];

  useEffect(() => {
    const healthBase = import.meta.env.VITE_HEALTH_BASE || '/health';
    fetch(healthBase)
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
        {offlineMode ? <Tag color="#f39b2f">{t('auth.local_only') || 'Local Only'}</Tag> : null}
        <Tag color="#2db7f5">{runtimeMode}</Tag>
      </div>
      <div className="app-nav">
        <NavLink to="/" end>
          {t('navigation.reasoning') || 'Reasoning Chains'}
        </NavLink>
        <NavLink to="/templates">{t('navigation.templates') || 'Template Library'}</NavLink>
        <NavLink to="/intelligence">{t('navigation.intelligence') || 'Intelligence Analysis'}</NavLink>
        <NavLink to="/analysis/tools">{t('navigation.analysis') || 'Analysis'}</NavLink>
        <NavLink to="/data">{t('navigation.data') || 'Data Management'}</NavLink>
        <NavLink to="/automation">{t('navigation.automation') || 'Automation'}</NavLink>
        {offlineMode && !token && offlineSession ? (
          <Tag color="#f39b2f">{t('auth.offline_mode') || 'Offline Mode'}</Tag>
        ) : null}
        <Dropdown menu={{ items: themeMenuItems }}>
          <Button
            type="text"
            icon={theme === 'dark' ? <BgColorsOutlined /> : <SunOutlined />}
            title={theme === 'dark' ? 'Switch Theme' : 'Switch Theme'}
            style={{ color: 'inherit' }}
          />
        </Dropdown>
        <LanguageSwitcher className="language-switcher-nav" />
        {token ? (
          <Button size="small" onClick={handleLogout}>
            {t('common.logout') || 'Logout'}
          </Button>
        ) : (
          <Button size="small" onClick={handleLogin}>
            {t('common.login') || 'Login'}
          </Button>
        )}
      </div>
    </div>
  );
}
