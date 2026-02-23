import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Divider, Input, Space, Typography, message, Checkbox, Tag } from 'antd';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from 'reactflow';
import TopNav from '../components/TopNav.jsx';
import NodeInspector from '../components/NodeInspector.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text } = Typography;

// 節點類型顏色
const NODE_TYPE_COLORS = {
  data_input: '#4ade80',
  data_output: '#60a5fa',
  output: '#ec4899',
  transform: '#f59e0b',
  calculate: '#8b5cf6',
  condition: '#14b8a6',
};

// 純 SVG 文本層 - 完全繞過 ReactFlow 節點系統
const SVGTextLayer = ({ nodes, transform }) => {
  if (!nodes || nodes.length === 0) {
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
              fill={NODE_TYPE_COLORS[node.data?.nodeType] || '#666'}
              opacity="0.95"
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

// FlowEditor 內容組件 - 使用 useReactFlow 訪問視口
const FlowEditorContent = ({ nodes }) => {
  const reactFlowInstance = useReactFlow();
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const animationFrameRef = React.useRef(null);
  const lastViewportRef = React.useRef({ x: 0, y: 0, zoom: 1 });

  // 監聽視口變化 - 使用 requestAnimationFrame 確保流暢更新
  React.useEffect(() => {
    const updateViewport = () => {
      const vp = reactFlowInstance.getViewport();

      // 只在視口真的改變時才更新（避免不必要的重新渲染）
      const last = lastViewportRef.current;
      if (vp.x !== last.x || vp.y !== last.y || vp.zoom !== last.zoom) {
        setViewport(vp);
        lastViewportRef.current = vp;
      }

      // 持續監聽下一幀
      animationFrameRef.current = requestAnimationFrame(updateViewport);
    };

    // 開始動畫循環
    animationFrameRef.current = requestAnimationFrame(updateViewport);

    return () => {
      // 清理動畫幀
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [reactFlowInstance]);

  return (
    <>
      <Background color="#9abdb3" gap={16} />
      <MiniMap nodeColor={node => NODE_TYPE_COLORS[node.data?.nodeType] || '#555'} style={{ background: '#0b1f24' }} />
      <Controls />
      <SVGTextLayer nodes={nodes} transform={[viewport.x, viewport.y, viewport.zoom]} />
    </>
  );
};

const initialNodes = [
  {
    id: 'input',
    type: 'default',
    data: {
      label: '',
      name: 'Input',
      nodeType: 'data_input',
      config: { source_type: 'global', key_path: 'file_id' },
    },
    position: { x: 0, y: 0 },
    style: {
      background: 'rgba(15, 43, 51, 0.95)',
      border: `2px solid ${NODE_TYPE_COLORS.data_input}`,
      borderRadius: 12,
      padding: 0,
      minWidth: 140,
      minHeight: 70,
      opacity: 0.9,
    },
  },
  {
    id: 'output',
    type: 'default',
    data: { label: '', name: 'Output', nodeType: 'output', config: { output_type: 'return' } },
    position: { x: 240, y: 120 },
    style: {
      background: 'rgba(15, 43, 51, 0.95)',
      border: `2px solid ${NODE_TYPE_COLORS.output}`,
      borderRadius: 12,
      padding: 0,
      minWidth: 140,
      minHeight: 70,
      opacity: 0.9,
    },
  },
];

export default function FlowEditor() {
  const { t } = useTranslation();
  const { chainId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [name, setName] = useState(t('reasoning.chain_name') || 'Untitled chain');
  const [description, setDescription] = useState('');
  const [isTemplate, setIsTemplate] = useState(searchParams.get('template') === 'true');
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const selectedNode = useMemo(
    () => nodes.find(node => node.id === selectedNodeId),
    [nodes, selectedNodeId]
  );

  const fetchChain = async () => {
    if (chainId === 'new') {
      return;
    }
    try {
      const chain = await api.getChain(chainId);
      setName(chain.name || 'Untitled chain');
      setDescription(chain.description || '');
      setIsTemplate(chain.is_template || false);
      if (Array.isArray(chain.nodes)) {
        const mappedNodes = chain.nodes.map((node, index) => ({
          id: node.node_id,
          type: 'default',
          data: {
            label: '',
            name: node.name || node.node_id,
            nodeType: node.node_type || 'data_input',
            config: node.config || {},
          },
          position: node.position || { x: 120 * index, y: 80 * index },
          style: {
            background: 'rgba(15, 43, 51, 0.95)',
            border: `2px solid ${NODE_TYPE_COLORS[node.node_type] || '#555'}`,
            borderRadius: 12,
            padding: 0,
            minWidth: 140,
            minHeight: 70,
            opacity: 0.9,
          },
        }));
        const mappedEdges = [];
        chain.nodes.forEach(node => {
          (node.inputs || []).forEach(inputId => {
            mappedEdges.push({
              id: `${inputId}-${node.node_id}`,
              source: inputId,
              target: node.node_id,
            });
          });
        });
        setNodes(mappedNodes);
        setEdges(mappedEdges);
      }
    } catch (error) {
      message.error(error.message || t('messages.chain_load_failed'));
    }
  };

  useEffect(() => {
    fetchChain();
  }, [chainId]);

  const onConnect = useCallback(params => setEdges(eds => addEdge(params, eds)), [setEdges]);

  const handleAddNode = nodeType => {
    const newNode = {
      id: `node-${nodes.length + 1}`,
      type: 'default',
      data: {
        label: '',
        name: `${nodeType.replace('_', ' ')}`,
        nodeType,
        config: {},
      },
      position: { x: 120 + nodes.length * 30, y: 120 + nodes.length * 20 },
      style: {
        background: 'rgba(15, 43, 51, 0.95)',
        border: `2px solid ${NODE_TYPE_COLORS[nodeType] || '#555'}`,
        borderRadius: 12,
        padding: 0,
        minWidth: 140,
        minHeight: 70,
        opacity: 0.9,
      },
    };
    setNodes(nds => nds.concat(newNode));
  };

  const handleNodeChange = updatedNode => {
    setNodes(nds => nds.map(node => (node.id === updatedNode.id ? updatedNode : node)));
  };

  const buildChainPayload = () => {
    const inputMap = edges.reduce((acc, edge) => {
      acc[edge.target] = acc[edge.target] || [];
      acc[edge.target].push(edge.source);
      return acc;
    }, {});

    const chainNodes = nodes.map(node => ({
      node_id: node.id,
      node_type: node.data?.nodeType || 'data_input',
      name: node.data?.label || node.id,
      inputs: inputMap[node.id] || [],
      config: node.data?.config || {},
      position: node.position,
    }));

    return {
      name,
      description,
      nodes: chainNodes,
      is_template: isTemplate,
    };
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = buildChainPayload();
      if (chainId === 'new') {
        const created = await api.createChain(payload);
        message.success(t('messages.chain_created_success'));
        navigate(`/flow/${created.id}`);
      } else {
        await api.updateChain(chainId, payload);
        message.success(t('messages.chain_updated_success'));
      }
    } catch (error) {
      message.error(error.message || t('messages.save_failed'));
    } finally {
      setSaving(false);
    }
  };

  const pollExecution = async executionId => {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const result = await api.getExecution(executionId);
      if (result.status !== 'running' && result.status !== 'pending') {
        return result;
      }
      await new Promise(resolve => setTimeout(resolve, 800));
    }
    return api.getExecution(executionId);
  };

  const handleRun = async () => {
    try {
      setRunning(true);
      if (chainId === 'new') {
        message.warning(t('messages.save_the_chain_first'));
        return;
      }
      const execution = await api.executeChain(chainId, { input_data: {} });
      const result = await pollExecution(execution.execution_id);
      setExecutionResult(result);
      message.success(t('messages.execution_completed_success'));
    } catch (error) {
      message.error(error.message || t('messages.execution_failed_msg'));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {t('floweditor.title')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('floweditor.subtitle')}
        </Text>
      </div>
      <div className="flow-shell">
        <div className="panel pad fade-in delay-2">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Input
              placeholder={t('reasoning.chain_name') || 'Chain name'}
              value={name}
              onChange={event => setName(event.target.value)}
            />
            <Input.TextArea
              placeholder={t('reasoning.chain_description') || 'Chain description'}
              value={description}
              autoSize={{ minRows: 2 }}
              onChange={event => setDescription(event.target.value)}
            />
            <Checkbox checked={isTemplate} onChange={e => setIsTemplate(e.target.checked)}>
              {isTemplate && (
                <Tag color="blue" style={{ marginLeft: 8 }}>
                  {t('reasoning.is_template') || 'Template'}
                </Tag>
              )}
              {t('reasoning.is_template') || 'Save as Template'}
            </Checkbox>
            <div className="flow-toolbar">
              <Button onClick={() => handleAddNode('data_input')}>{t('reasoning.node.add_input') || 'Add input'}</Button>
              <Button onClick={() => handleAddNode('transform')}>{t('reasoning.node.add_transform') || 'Add transform'}</Button>
              <Button onClick={() => handleAddNode('calculate')}>{t('reasoning.node.add_calculate') || 'Add calculate'}</Button>
              <Button onClick={() => handleAddNode('condition')}>{t('reasoning.node.add_condition') || 'Add condition'}</Button>
              <Button onClick={() => handleAddNode('output')}>{t('reasoning.node.add_output') || 'Add output'}</Button>
            </div>
            <Space>
              <Button type="primary" onClick={handleSave} loading={saving}>
                {t('common.save') || 'Save'}
              </Button>
              <Button onClick={handleRun} loading={running}>
                {t('reasoning.execute_chain') || 'Run'}
              </Button>
              <Button onClick={() => navigate('/')}>{t('common.back') || 'Back'}</Button>
            </Space>
          </div>
          <Divider />
          <div className="flow-editor">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
              fitView
            >
              <FlowEditorContent nodes={nodes} />
            </ReactFlow>
          </div>
        </div>
        <div className="panel pad flow-sidebar fade-in delay-2">
          <Title level={4}>{t('reasoning.node.basic_info') || 'Node inspector'}</Title>
          <NodeInspector node={selectedNode} onChange={handleNodeChange} />
          <Divider />
          <Title level={4}>{t('reasoning.execution_history') || t('floweditor.execution_output')}</Title>
          <div className="code-block">
            {executionResult
              ? JSON.stringify(executionResult, null, 2)
              : t('messages.run_a_chain')}
          </div>
        </div>
      </div>
    </div>
  );
}
