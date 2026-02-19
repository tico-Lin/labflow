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
      message.error(error.message || '載入模板失敗');
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
      message.success('已從模板創建新推理鏈');
      navigate(`/flow/${newChain.id}`);
    } catch (error) {
      message.error(error.message || '創建失敗');
    }
  };

  // 刪除模板
  const handleDeleteTemplate = async templateId => {
    try {
      await api.deleteChain(templateId);
      message.success('模板已刪除');
      fetchTemplates();
    } catch (error) {
      message.error(error.message || '刪除失敗');
    }
  };

  // 預覽模板
  const handlePreviewTemplate = async template => {
    try {
      const fullTemplate = await api.getChain(template.id);
      setSelectedTemplate(fullTemplate);
      setPreviewVisible(true);
    } catch (error) {
      message.error(error.message || '載入模板詳情失敗');
    }
  };

  // 渲染預覽的流程圖
  const renderPreviewFlow = () => {
    if (!selectedTemplate || !selectedTemplate.nodes) {
      return <Empty description="沒有節點數據" />;
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
          <Spin size="large" tip="載入模板中..." />
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          推理鏈模板庫
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          重用預設的推理鏈模板快速構建分析工作流
        </Text>
      </div>

      <div className="panel pad fade-in delay-2" style={{ maxWidth: 1400, margin: '24px auto' }}>
        <Space style={{ marginBottom: 24, width: '100%', justifyContent: 'space-between' }}>
          <Text strong>找到 {templates.length} 個模板</Text>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/flow/new?template=true')}
          >
            創建新模板
          </Button>
        </Space>

        {templates.length === 0 ? (
          <Empty description="還沒有任何模板" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button type="primary" onClick={() => navigate('/flow/new?template=true')}>
              創建第一個模板
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
                        預覽
                      </Button>,
                      <Button
                        type="link"
                        icon={<CopyOutlined />}
                        onClick={() => handleCreateFromTemplate(template.id)}
                      >
                        使用
                      </Button>,
                      <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/flow/${template.id}`)}
                      >
                        編輯
                      </Button>,
                      <Popconfirm
                        title="確定刪除這個模板嗎？"
                        onConfirm={() => handleDeleteTemplate(template.id)}
                        okText="確定"
                        cancelText="取消"
                      >
                        <Button type="link" danger icon={<DeleteOutlined />}>
                          刪除
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
                            {template.description || '無描述'}
                          </Paragraph>
                          <Space size="small" wrap>
                            <Tag>{nodeCount} 個節點</Tag>
                            {Object.entries(nodeTypes).map(([type, count]) => (
                              <Tag key={type} color={NODE_TYPE_COLORS[type]}>
                                {type}: {count}
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
            <Tag color="blue">模板</Tag>
            <span>{selectedTemplate?.name}</span>
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            關閉
          </Button>,
          <Button
            key="edit"
            icon={<EditOutlined />}
            onClick={() => {
              setPreviewVisible(false);
              navigate(`/flow/${selectedTemplate.id}`);
            }}
          >
            編輯
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
            使用此模板
          </Button>,
        ]}
      >
        {selectedTemplate && (
          <div>
            <Paragraph>{selectedTemplate.description || '無描述'}</Paragraph>
            <Title level={5}>工作流程圖</Title>
            {renderPreviewFlow()}
            <Title level={5} style={{ marginTop: 24 }}>
              節點列表
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
                        輸入: {node.inputs.join(', ')}
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
