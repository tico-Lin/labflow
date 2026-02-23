import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Empty,
  Modal,
  Row,
  Space,
  Tag,
  Typography,
  message,
  Spin,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text, Paragraph } = Typography;

// 節點類型配色方案
const NODE_TYPE_COLORS = {
  data_input: '#52c41a',
  transform: '#1890ff',
  calculate: '#722ed1',
  condition: '#fa8c16',
  output: '#eb2f96',
};

export default function TemplateLibrary() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);

  // 載入模板列表
  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const templateList = await api.listTemplates();
      setTemplates(templateList);
    } catch (error) {
      message.error(error.message || t('template.load_failed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  // 從模板創建新鏈
  const handleCreateFromTemplate = async templateId => {
    try {
      const newChain = await api.createChainFromTemplate(templateId);
      message.success(t('template.created_from'));
      navigate(`/flow/${newChain.id}`);
    } catch (error) {
      message.error(error.message || t('template.delete_failed'));
    }
  };

  // 刪除模板
  const handleDeleteTemplate = async templateId => {
    try {
      await api.deleteChain(templateId);
      message.success(t('template.delete_success'));
      fetchTemplates();
    } catch (error) {
      message.error(error.message || t('template.delete_failed'));
    }
  };

  // 預覽模板
  const handlePreviewTemplate = async template => {
    try {
      const fullTemplate = await api.getChain(template.id);
      setSelectedTemplate(fullTemplate);
      setPreviewVisible(true);
    } catch (error) {
      message.error(error.message || t('template.load_details_failed'));
    }
  };

  // 渲染預覽的流程圖
  const renderPreviewFlow = () => {
    if (!selectedTemplate || !selectedTemplate.nodes) {
      return <Empty description={t('template.no_nodes')} />;
    }

    const nodes = selectedTemplate.nodes.map((node, index) => ({
      id: node.node_id,
      type: 'default',
      data: {
        label: (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{node.name || node.node_id}</div>
            <Tag color={NODE_TYPE_COLORS[node.node_type] || 'default'} style={{ fontSize: 10 }}>
              {node.node_type}
            </Tag>
          </div>
        ),
      },
      position: node.position || { x: 120 * index, y: 80 * index },
      style: {
        background: '#f9f9f9',
        border: `2px solid ${NODE_TYPE_COLORS[node.node_type] || '#555'}`,
        borderRadius: 8,
        padding: 10,
        minWidth: 120,
      },
    }));

    const edges = [];
    selectedTemplate.nodes.forEach(node => {
      (node.inputs || []).forEach(inputId => {
        edges.push({
          id: `${inputId}-${node.node_id}`,
          source: inputId,
          target: node.node_id,
          animated: true,
          style: { stroke: '#1890ff' },
        });
      });
    });

    return (
      <div style={{ height: 400 }}>
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    );
  };

  // 統計節點類型
  const countNodeTypes = template => {
    if (!template.nodes || !Array.isArray(template.nodes)) {
      return {};
    }
    return template.nodes.reduce((acc, node) => {
      const type = node.node_type || 'unknown';
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {});
  };

  if (loading) {
    return (
      <div className="app-shell">
        <TopNav />
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" spinning={true}>
            <div style={{ padding: '50px' }}>{t('template.loading')}</div>
          </Spin>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {t('template.library_title')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('template.library_subtitle')}
        </Text>
      </div>

      <div className="panel pad fade-in delay-2" style={{ maxWidth: 1400, margin: '24px auto' }}>
        <Space style={{ marginBottom: 24, width: '100%', justifyContent: 'space-between' }}>
          <Text strong>{t('template.found_count', { count: templates.length })}</Text>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/flow/new?template=true')}
          >
            {t('template.create_new')}
          </Button>
        </Space>

        {templates.length === 0 ? (
          <Empty description={t('template.no_templates')} image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button type="primary" onClick={() => navigate('/flow/new?template=true')}>
              {t('template.create_first')}
            </Button>
          </Empty>
        ) : (
          <Row gutter={[16, 16]}>
            {templates.map(template => {
              const nodeTypes = countNodeTypes(template);
              const nodeCount = Object.values(nodeTypes).reduce((sum, count) => sum + count, 0);

              return (
                <Col xs={24} sm={12} lg={8} xl={6} key={template.id}>
                  <Card
                    hoverable
                    actions={[
                      <Button
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => handlePreviewTemplate(template)}
                      >
                        {t('template.preview')}
                      </Button>,
                      <Button
                        type="link"
                        icon={<CopyOutlined />}
                        onClick={() => handleCreateFromTemplate(template.id)}
                      >
                        {t('template.use')}
                      </Button>,
                      <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/flow/${template.id}`)}
                      >
                        {t('common.edit')}
                      </Button>,
                      <Popconfirm
                        title={t('template.delete_confirm')}
                        onConfirm={() => handleDeleteTemplate(template.id)}
                        okText={t('common.confirm')}
                        cancelText={t('common.cancel')}
                      >
                        <Button type="link" danger icon={<DeleteOutlined />}>
                          {t('common.delete')}
                        </Button>
                      </Popconfirm>,
                    ]}
                  >
                    <Card.Meta
                      title={
                        <div>
                          <Tag color="blue" style={{ marginBottom: 8 }}>
                            模板
                          </Tag>
                          <div>{template.name}</div>
                        </div>
                      }
                      description={
                        <div>
                          <Paragraph
                            ellipsis={{ rows: 2 }}
                            style={{ marginBottom: 12, minHeight: 44 }}
                          >
                            {template.description || t('template.no_description')}
                          </Paragraph>
                          <Space size="small" wrap>
                            <Tag>{t('template.node_count', { count: nodeCount })}</Tag>
                            {Object.entries(nodeTypes).map(([type, count]) => (
                              <Tag key={type} color={NODE_TYPE_COLORS[type]}>
                                {t('template.node_type_count', { type, count })}
                              </Tag>
                            ))}
                          </Space>
                        </div>
                      }
                    />
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </div>

      {/* 模板預覽 Modal */}
      <Modal
        title={
          <Space>
            <Tag color="blue">{t('template.tag_template')}</Tag>
            <span>{selectedTemplate?.name}</span>
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            {t('common.close')}
          </Button>,
          <Button
            key="edit"
            icon={<EditOutlined />}
            onClick={() => {
              setPreviewVisible(false);
              navigate(`/flow/${selectedTemplate.id}`);
            }}
          >
            {t('common.edit')}
          </Button>,
          <Button
            key="use"
            type="primary"
            icon={<CopyOutlined />}
            onClick={() => {
              setPreviewVisible(false);
              handleCreateFromTemplate(selectedTemplate.id);
            }}
          >
            {t('template.use_this')}
          </Button>,
        ]}
      >
        {selectedTemplate && (
          <div>
            <Paragraph>{selectedTemplate.description || t('template.no_description')}</Paragraph>
            <Title level={5}>{t('template.workflow_diagram')}</Title>
            {renderPreviewFlow()}
            <Title level={5} style={{ marginTop: 24 }}>
              {t('template.node_list')}
            </Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              {selectedTemplate.nodes?.map((node, index) => (
                <Card key={node.node_id} size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Text strong>#{index + 1}</Text>
                      <Text strong>{node.name || node.node_id}</Text>
                      <Tag color={NODE_TYPE_COLORS[node.node_type]}>{node.node_type}</Tag>
                    </Space>
                    {node.inputs && node.inputs.length > 0 && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('template.inputs_label')} {node.inputs.join(', ')}
                      </Text>
                    )}
                  </Space>
                </Card>
              ))}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
}
