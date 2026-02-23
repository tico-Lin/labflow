import React, { useEffect, useState } from 'react';
import { Button, Table, Typography, message, Space, Card, Row, Col, Statistic, Tag } from 'antd';
import {
  BookOutlined,
  PlusOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text } = Typography;

export default function Home() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [chains, setChains] = useState([]);

  const fetchChains = async () => {
    try {
      setLoading(true);
      const data = await api.listChains();
      // 過濾掉模板，只顯示普通推理鏈
      const nonTemplateChains = data.filter(chain => !chain.is_template);
      setChains(nonTemplateChains);
    } catch (error) {
      message.error(error.message || 'Failed to load chains.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChains();
  }, []);

  const handleDelete = async id => {
    try {
      await api.deleteChain(id);
      message.success(t('home.chain_removed'));
      fetchChains();
    } catch (error) {
      message.error(error.message || t('home.delete_failed'));
    }
  };

  const columns = [
    {
      title: t('home.name_column'),
      dataIndex: 'name',
    },
    {
      title: t('home.description_column'),
      dataIndex: 'description',
    },
    {
      title: t('home.created_column'),
      dataIndex: 'created_at',
      render: value => (value ? new Date(value).toLocaleString() : '-'),
    },
    {
      title: t('home.actions_column'),
      key: 'actions',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button size="small" type="primary" onClick={() => navigate(`/view/${record.id}`)}>
            {t('home.view_button')}
          </Button>
          <Button size="small" onClick={() => navigate(`/flow/${record.id}`)}>
            {t('home.edit_button')}
          </Button>
          <Button size="small" danger onClick={() => handleDelete(record.id)}>
            {t('home.delete_button')}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={1} className="fade-in">
          {t('pages.reasoning_chain_library')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('pages.manage_templates')}
        </Text>
      </div>
      <div style={{ padding: '0 24px 32px' }}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }} className="fade-in delay-2">
          <Col xs={24} sm={12} md={6}>
            <Card hoverable onClick={() => navigate('/flow/new')}>
              <Statistic
                title={t('home.create_new_chain')}
                prefix={<PlusOutlined />}
                valueStyle={{ color: '#1890ff' }}
                value={t('home.start_value')}
              />
              <Text type="secondary">{t('home.start_desc')}</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card hoverable onClick={() => navigate('/templates')}>
              <Statistic
                title={t('home.template_library')}
                prefix={<BookOutlined />}
                valueStyle={{ color: '#52c41a' }}
                value={t('home.browse_value')}
              />
              <Text type="secondary">{t('home.browse_desc')}</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card hoverable onClick={() => navigate('/intelligence')}>
              <Statistic
                title={t('home.intelligent_analysis')}
                prefix={<ThunderboltOutlined />}
                valueStyle={{ color: '#faad14' }}
                value={t('home.ai_value')}
              />
              <Text type="secondary">{t('home.ai_desc')}</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic title={t('home.my_chains_stat')} prefix={<AppstoreOutlined />} value={chains.length} />
              <Text type="secondary">{t('home.chains_count_desc')}</Text>
            </Card>
          </Col>
        </Row>
        <div className="panel pad fade-in delay-3">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Text strong>{t('home.my_chains_title')}</Text>
            <Space>
              <Button icon={<BookOutlined />} onClick={() => navigate('/templates')}>
                {t('home.browse_templates_button')}
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/flow/new')}>
                {t('home.create_new_button')}
              </Button>
            </Space>
          </div>
          <Table
            rowKey="id"
            columns={columns}
            dataSource={chains}
            loading={loading}
            pagination={{ pageSize: 6 }}
          />
        </div>
      </div>
    </div>
  );
}
