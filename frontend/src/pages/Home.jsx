import React, { useEffect, useState } from 'react';
import { Button, Table, Typography, message, Space, Card, Row, Col, Statistic, Tag } from 'antd';
import { BookOutlined, PlusOutlined, AppstoreOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';

const { Title, Text } = Typography;

export default function Home() {
  const navigate = useNavigate();
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
      message.success('Chain removed.');
      fetchChains();
    } catch (error) {
      message.error(error.message || 'Delete failed.');
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
    },
    {
      title: 'Description',
      dataIndex: 'description',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      render: value => (value ? new Date(value).toLocaleString() : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button size="small" type="primary" onClick={() => navigate(`/view/${record.id}`)}>
            View
          </Button>
          <Button size="small" onClick={() => navigate(`/flow/${record.id}`)}>
            Edit
          </Button>
          <Button size="small" danger onClick={() => handleDelete(record.id)}>
            Delete
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
          Reasoning Chain Library
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          Manage templates, connect data sources, and run automated workflows.
        </Text>
      </div>
      <div style={{ padding: '0 24px 32px' }}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }} className="fade-in delay-2">
          <Col xs={24} sm={12} md={8}>
            <Card hoverable onClick={() => navigate('/flow/new')}>
              <Statistic
                title="創建新推理鏈"
                prefix={<PlusOutlined />}
                valueStyle={{ color: '#1890ff' }}
                value="開始"
              />
              <Text type="secondary">從零開始構建自定義工作流</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card hoverable onClick={() => navigate('/templates')}>
              <Statistic
                title="模板庫"
                prefix={<BookOutlined />}
                valueStyle={{ color: '#52c41a' }}
                value="瀏覽"
              />
              <Text type="secondary">從預設模板快速開始</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card>
              <Statistic title="我的推理鏈" prefix={<AppstoreOutlined />} value={chains.length} />
              <Text type="secondary">已創建的工作流數量</Text>
            </Card>
          </Col>
        </Row>
        <div className="panel pad fade-in delay-3">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <Text strong>我的推理鏈</Text>
            <Space>
              <Button icon={<BookOutlined />} onClick={() => navigate('/templates')}>
                瀏覽模板
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/flow/new')}>
                創建新鏈
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
