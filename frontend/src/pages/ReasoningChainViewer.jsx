import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Space,
  Tag,
  Tabs,
  Timeline,
  Typography,
  message,
  Spin,
} from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import ReactFlow, { Background, Controls, MiniMap, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text, Paragraph } = Typography;

// 純 SVG 文本層 - 完全繞過 ReactFlow 節點系統
const SVGTextLayer = ({ nodes, transform }) => {
  console.log('[SVGTextLayer] Rendering with nodes:', nodes, 'transform:', transform);

  if (!nodes || nodes.length === 0) {
    console.warn('[SVGTextLayer] No nodes to render');
    return null;
  }

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 100,
      }}
    >
      {nodes.map((node) => {
        // 正確的坐標變換：畫布坐標 = 節點坐標 × 縮放 + 視口偏移
        const zoom = transform[2];
        const x = node.position.x * zoom + transform[0];
        const y = node.position.y * zoom + transform[1];

        // 節點大小：寬 140px, 高 70px
        const nodeWidth = 140;
        const nodeHeight = 70;
        const centerX = x + (nodeWidth / 2) * zoom;
        const centerY = y + (nodeHeight / 2) * zoom;

        console.log(`[SVGTextLayer] Rendering node ${node.id}:`, {
          name: node.data?.name,
          nodeType: node.data?.nodeType,
          pos: `(${centerX.toFixed(1)}, ${centerY.toFixed(1)})`,
          zoom,
        });

        return (
          <g key={node.id}>
            {/* 節點名稱 - 放在節點中心上方 */}
            <text
              x={centerX}
              y={centerY - 10 * zoom}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{
                fill: '#e9f5f2',
                fontSize: `${14 * zoom}px`,
                fontWeight: 'bold',
                textShadow: `0 2px 4px rgba(0,0,0,0.8)`,
                fontFamily: 'system-ui, -apple-system, sans-serif',
                pointerEvents: 'none',
                userSelect: 'none',
              }}
            >
              {node.data?.name || node.id}
            </text>
            {/* 節點類型標籤 - 放在節點下方 */}
            <rect
              x={centerX - 35 * zoom}
              y={centerY + 15 * zoom}
              width={70 * zoom}
              height={16 * zoom}
              rx={3 * zoom}
              fill="rgba(255, 152, 0, 0.95)"
              pointerEvents="none"
            />
            <text
              x={centerX}
              y={centerY + 23 * zoom}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{
                fill: '#ffffff',
                fontSize: `${11 * zoom}px`,
                fontWeight: '600',
                fontFamily: 'system-ui, -apple-system, sans-serif',
                pointerEvents: 'none',
                userSelect: 'none',
              }}
            >
              {node.data?.nodeType || 'unknown'}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// 內部查看器組件 - 使用 useReactFlow 訪問視口
const ChainViewerContent = ({ nodes, edges, chainData }) => {
  const reactFlowInstance = useReactFlow();
  const [viewport, setViewport] = useState(reactFlowInstance.getViewport());

  // 監聽視口變化
  useEffect(() => {
    const updateViewport = () => {
      setViewport(reactFlowInstance.getViewport());
    };

    // 監聽移動事件
    const unsubscribe = reactFlowInstance.onMove?.(updateViewport);

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [reactFlowInstance]);

  return (
    <>
      <Background color="#9abdb3" gap={16} />
      <MiniMap
        nodeColor={node => NODE_TYPE_COLORS[node.data?.nodeType] || '#555'}
        style={{ background: '#0b1f24' }}
      />
      <Controls />
      <SVGTextLayer nodes={nodes} transform={[viewport.x, viewport.y, viewport.zoom]} />
    </>
  );
};
const NODE_TYPE_COLORS = {
  data_input: '#52c41a',
  transform: '#1890ff',
  calculate: '#722ed1',
  condition: '#fa8c16',
  output: '#eb2f96',
};

// 執行狀態配色
const STATUS_COLORS = {
  success: 'success',
  completed: 'success',
  failed: 'error',
  error: 'error',
  running: 'processing',
  pending: 'default',
};

export default function ReasoningChainViewer() {
  const { t } = useTranslation();
  const { chainId } = useParams();
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executionLoading, setExecutionLoading] = useState(false);

  // 載入推理鏈資訊
  const fetchChain = async () => {
    try {
      setLoading(true);
      const chainData = await api.getChain(chainId);
      console.log('[ReasoningChainViewer] Chain data loaded:', chainData);
      setChain(chainData);

      // 轉換節點和邊
      if (Array.isArray(chainData.nodes)) {
        console.log('[ReasoningChainViewer] Processing nodes:', chainData.nodes);
        const mappedNodes = chainData.nodes.map((node, index) => {
          const mapped = {
            id: node.node_id,
            type: 'default',
            position: node.position || { x: 120 * index, y: 80 * index },
            data: {
              name: node.name || node.node_id,
              nodeType: node.node_type || 'data_input',
              label: '', // 空標籤，我們用獨立層渲染
            },
            style: {
              background: 'rgba(15, 43, 51, 0.95)',
              border: `2px solid ${NODE_TYPE_COLORS[node.node_type] || '#555'}`,
              borderRadius: 12,
              padding: 0,
              minWidth: 140,
              minHeight: 70,
              opacity: 0.9,
            },
          };
          console.log(`[ReasoningChainViewer] Mapped node ${node.node_id}:`, mapped);
          return mapped;
        });

        const mappedEdges = [];
        chainData.nodes.forEach(node => {
          (node.inputs || []).forEach(inputId => {
            mappedEdges.push({
              id: `${inputId}-${node.node_id}`,
              source: inputId,
              target: node.node_id,
              animated: true,
              style: { stroke: '#9abdb3' },
            });
          });
        });

        setNodes(mappedNodes);
        setEdges(mappedEdges);
      }

      // 獲取執行歷史
      await fetchExecutions();
    } catch (error) {
      message.error(error.message || t('reasoning.execute_failed'));
    } finally {
      setLoading(false);
    }
  };

  // 載入執行歷史
  const fetchExecutions = async () => {
    try {
      // 調用後端 API 獲取執行歷史
      const history = await api.getChainHistory(chainId, 30);

      // 如果返回統計數據，則需要單獨獲取執行列表
      if (history && history.total_executions > 0) {
        // 嘗試獲取執行列表（如果 API 支持）
        const execList = await api.listChainExecutions(chainId, 20);
        setExecutions(Array.isArray(execList) ? execList : []);
      } else {
        setExecutions([]);
      }
    } catch (error) {
      console.error('載入執行歷史失敗:', error);
      setExecutions([]);
    }
  };

  useEffect(() => {
    if (chainId) {
      fetchChain();
    }
  }, [chainId]);

  // 執行推理鏈
  const handleExecuteChain = async () => {
    try {
      setExecutionLoading(true);
      const execution = await api.executeChain(chainId, { input_data: {} });
      message.success(t('reasoning.execute_success'));

      // 輪詢執行狀態
      const result = await pollExecution(execution.execution_id);
      setSelectedExecution(result);
      await fetchExecutions();
      message.success(t('messages.execution_completed'));
    } catch (error) {
      message.error(error.message || t('reasoning.execute_failed'));
    } finally {
      setExecutionLoading(false);
    }
  };

  // 輪詢執行結果
  const pollExecution = async executionId => {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      const result = await api.getExecution(executionId);
      if (result.status !== 'running' && result.status !== 'pending') {
        return result;
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    return api.getExecution(executionId);
  };

  // 查看執行詳情
  const handleViewExecution = async executionId => {
    try {
      const execution = await api.getExecution(executionId);
      setSelectedExecution(execution);
    } catch (error) {
      message.error(error.message || t('error.unknown_error'));
    }
  };

  if (loading) {
    return (
      <div className="app-shell">
        <TopNav />
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '50vh',
          }}
        >
          <Spin size="large" />
        </div>
      </div>
    );
  }

  if (!chain) {
    return (
      <div className="app-shell">
        <TopNav />
        <div className="hero">
          <Title level={2}>{t('error.not_found')}</Title>
          <Button onClick={() => navigate('/')}>{t('common.back')}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {chain.name}
        </Title>
        <Paragraph type="secondary" className="fade-in delay-1">
          {chain.description || t('template.no_description')}
        </Paragraph>
        <Space className="fade-in delay-1">
          <Button type="primary" onClick={handleExecuteChain} loading={executionLoading}>
            {t('reasoning.execute_chain')}
          </Button>
          <Button onClick={() => navigate('/')}>{t('common.back')}</Button>
          {chain.is_template && <Tag color="blue">{t('template.tag_template')}</Tag>}
        </Space>
      </div>

      <div className="viewer-shell">
        {/* 調試面板 */}
        <div style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          background: 'rgba(0,0,0,0.8)',
          color: '#e9f5f2',
          padding: '10px 15px',
          borderRadius: '8px',
          fontSize: '12px',
          maxWidth: '300px',
          maxHeight: '200px',
          overflow: 'auto',
          fontFamily: 'monospace',
          zIndex: 1000,
        }}>
          <div><strong>Debug Info</strong></div>
          <div>Nodes: {nodes.length}</div>
          <div>Chain ID: {chainId}</div>
          {nodes.length > 0 && (
            <div>
              <div>First Node: {nodes[0]?.id}</div>
              <div>First Node Name: {nodes[0]?.data?.name}</div>
            </div>
          )}
        </div>

        {/* 左側：推理鏈視覺化 */}
        <div className="panel pad fade-in delay-2">
          <Title level={4}>{t('reasoning.title')}</Title>
          <div className="flow-viewer">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
            >
              <ChainViewerContent nodes={nodes} edges={edges} chainData={chain} />
            </ReactFlow>
          </div>

          {/* 節點詳情 */}
          {nodes.length > 0 && (
            <Card
              title={t('template.node_list')}
              size="small"
              style={{ marginTop: 16, background: 'rgba(20, 42, 51, 0.95)' }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {chain.nodes?.map(node => (
                  <Card
                    key={node.node_id}
                    size="small"
                    style={{ background: 'rgba(15, 35, 43, 0.9)' }}
                  >
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="節點 ID">{node.node_id}</Descriptions.Item>
                      <Descriptions.Item label="節點名稱">{node.name || '-'}</Descriptions.Item>
                      <Descriptions.Item label="類型">
                        <Tag color={NODE_TYPE_COLORS[node.node_type]}>{node.node_type}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="輸入節點">
                        {node.inputs?.length > 0 ? node.inputs.join(', ') : t('common.no')}
                      </Descriptions.Item>
                      <Descriptions.Item label="配置">
                        <pre className="code-block-inline">
                          {JSON.stringify(node.config, null, 2)}
                        </pre>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                ))}
              </Space>
            </Card>
          )}
        </div>

        {/* 右側：執行歷史和結果 */}
        <div className="panel pad fade-in delay-2">
          <Tabs
            defaultActiveKey="history"
            items={[
              {
                key: 'history',
                label: t('reasoning.execution_history'),
                children: (
                  <div style={{ maxHeight: 'calc(100vh - 300px)', overflow: 'auto' }}>
                    {executions.length === 0 ? (
                      <Text type="secondary">尚無執行記錄</Text>
                    ) : (
                      <Timeline
                        items={executions.map(exec => ({
                          key: exec.execution_id,
                          color:
                            exec.status === 'completed'
                              ? 'green'
                              : exec.status === 'failed'
                                ? 'red'
                                : 'blue',
                          children: (
                            <Space direction="vertical" size="small">
                              <Space>
                                <Text strong>執行 ID: {exec.execution_id}</Text>
                                <Tag color={STATUS_COLORS[exec.status]}>{exec.status}</Tag>
                              </Space>
                              <Text type="secondary">
                                開始時間:{' '}
                                {exec.started_at ? new Date(exec.started_at).toLocaleString() : '-'}
                              </Text>
                              {exec.execution_time_ms && (
                                <Text type="secondary">
                                  耗時: {exec.execution_time_ms.toFixed(2)} ms
                                </Text>
                              )}
                              <Button
                                size="small"
                                onClick={() => handleViewExecution(exec.execution_id)}
                              >
                                查看詳情
                              </Button>
                            </Space>
                          ),
                        }))}
                      />
                    )}
                  </div>
                ),
              },
              {
                key: 'result',
                label: '執行結果',
                children: (
                  <div style={{ maxHeight: 'calc(100vh - 300px)', overflow: 'auto' }}>
                    {selectedExecution ? (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Card size="small" title="執行資訊">
                          <Descriptions size="small" column={1}>
                            <Descriptions.Item label="執行 ID">
                              {selectedExecution.execution_id}
                            </Descriptions.Item>
                            <Descriptions.Item label="狀態">
                              <Tag color={STATUS_COLORS[selectedExecution.status]}>
                                {selectedExecution.status}
                              </Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="開始時間">
                              {selectedExecution.started_at
                                ? new Date(selectedExecution.started_at).toLocaleString()
                                : '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="完成時間">
                              {selectedExecution.completed_at
                                ? new Date(selectedExecution.completed_at).toLocaleString()
                                : '-'}
                            </Descriptions.Item>
                            <Descriptions.Item label="執行時間">
                              {selectedExecution.execution_time_ms
                                ? `${selectedExecution.execution_time_ms.toFixed(2)} ms`
                                : '-'}
                            </Descriptions.Item>
                          </Descriptions>
                        </Card>

                        {selectedExecution.error && (
                          <Card size="small" title="錯誤資訊" style={{ borderColor: '#ff4d4f' }}>
                            <pre className="code-block">
                              {JSON.stringify(selectedExecution.error, null, 2)}
                            </pre>
                          </Card>
                        )}

                        <Card size="small" title="輸入資料">
                          <pre className="code-block">
                            {JSON.stringify(selectedExecution.input_data || {}, null, 2)}
                          </pre>
                        </Card>

                        <Card size="small" title="執行結果">
                          <pre className="code-block">
                            {JSON.stringify(selectedExecution.results || {}, null, 2)}
                          </pre>
                        </Card>
                      </Space>
                    ) : (
                      <Text type="secondary">請選擇一個執行記錄查看詳情</Text>
                    )}
                  </div>
                ),
              },
              {
                key: 'info',
                label: '鏈資訊',
                children: (
                  <Card size="small">
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="鏈 ID">{chain.id}</Descriptions.Item>
                      <Descriptions.Item label="名稱">{chain.name}</Descriptions.Item>
                      <Descriptions.Item label="描述">
                        {chain.description || t('common.no')}
                      </Descriptions.Item>
                      <Descriptions.Item label="是否模板">
                        {chain.is_template ? t('common.yes') : t('common.no')}
                      </Descriptions.Item>
                      <Descriptions.Item label="建立時間">
                        {chain.created_at ? new Date(chain.created_at).toLocaleString() : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="更新時間">
                        {chain.updated_at ? new Date(chain.updated_at).toLocaleString() : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="節點數量">
                        {chain.nodes?.length || 0}
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
