import React, { useState } from 'react';
import { Button, Form, Input, Typography, message } from 'antd';
import { Link, useNavigate } from 'react-router-dom';
import { api, auth } from '../api/client.js';
import { useTranslation, LanguageSwitcher } from '../i18n.jsx';

const { Title, Text } = Typography;

export default function Login() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const offlineAllowed =
    String(import.meta.env.VITE_OFFLINE_MODE || 'true')
      .toLowerCase()
      .trim() === 'true';

  const handleFinish = async values => {
    try {
      setLoading(true);
      const response = await api.login(values);
      auth.setToken(response.access_token);
      auth.setOffline(false);
      message.success(t('auth.login_success'));
      navigate('/');
    } catch (error) {
      message.error(error.message || t('auth.login_failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleOffline = () => {
    auth.clearToken();
    auth.setOffline(true);
    message.info(t('auth.offline_mode'));
    navigate('/');
  };

  return (
    <div className="auth-shell">
      <div className="panel pad auth-card fade-in">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 16,
          }}
        >
          <Title level={2} style={{ margin: 0 }}>
            {t('auth.login_title')}
          </Title>
          <LanguageSwitcher />
        </div>
        <Text type="secondary">{t('common.welcome')}</Text>
        <Form layout="vertical" onFinish={handleFinish} style={{ marginTop: 24 }}>
          <Form.Item
            name="username"
            label={t('auth.username')}
            rules={[{ required: true, message: t('auth.username_required') }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label={t('auth.password')}
            rules={[{ required: true, message: t('auth.password_required') }]}
          >
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            {t('common.login')}
          </Button>
          {offlineAllowed ? (
            <Button type="default" onClick={handleOffline} block style={{ marginTop: 12 }}>
              {t('auth.offline_mode')}
            </Button>
          ) : null}
        </Form>
        {offlineAllowed ? (
          <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
            {t('auth.local_only')}
          </Text>
        ) : null}
        <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
          {t('common.register')}? <Link to="/register">{t('auth.register_title')}</Link>
        </Text>
      </div>
    </div>
  );
}
