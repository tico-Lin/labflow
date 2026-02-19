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
} from 'reactflow';
import TopNav from '../components/TopNav.jsx';
import NodeInspector from '../components/NodeInspector.jsx';
import { api } from '../api/client.js';

const { Title, Text } = Typography;

const initialNodes = [
  {
    id: 'input',
    type: 'default',
    data: {
      label: 'Input',
      nodeType: 'data_input',
      config: { source_type: 'global', key_path: 'file_id' },
    },
    position: { x: 0, y: 0 },
  },
  {
    id: 'output',
    type: 'default',
    data: { label: 'Output', nodeType: 'output', config: { output_type: 'return' } },
    position: { x: 240, y: 120 },
  },
];

export default function FlowEditor() {
  const { chainId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [name, setName] = useState('Untitled chain');
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
            label: node.name || node.node_id,
            nodeType: node.node_type || 'data_input',
            config: node.config || {},
          },
          position: node.position || { x: 120 * index, y: 80 * index },
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
      message.error(error.message || 'Failed to load chain.');
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
        label: `${nodeType.replace('_', ' ')}`,
        nodeType,
        config: {},
      },
      position: { x: 120 + nodes.length * 30, y: 120 + nodes.length * 20 },
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
        message.success('Chain created.');
        navigate(`/flow/${created.id}`);
      } else {
        await api.updateChain(chainId, payload);
        message.success('Chain updated.');
      }
    } catch (error) {
      message.error(error.message || 'Save failed.');
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
        message.warning('Save the chain before running.');
        return;
      }
      const execution = await api.executeChain(chainId, { input_data: {} });
      const result = await pollExecution(execution.execution_id);
      setExecutionResult(result);
      message.success('Execution completed.');
    } catch (error) {
      message.error(error.message || 'Execution failed.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          Reasoning Flow Editor
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          Assemble and test nodes with live execution output.
        </Text>
      </div>
      <div className="flow-shell">
        <div className="panel pad fade-in delay-2">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Input
              placeholder="Chain name"
              value={name}
              onChange={event => setName(event.target.value)}
            />
            <Input.TextArea
              placeholder="Chain description"
              value={description}
              autoSize={{ minRows: 2 }}
              onChange={event => setDescription(event.target.value)}
            />
            <Checkbox checked={isTemplate} onChange={e => setIsTemplate(e.target.checked)}>
              {isTemplate && (
                <Tag color="blue" style={{ marginLeft: 8 }}>
                  模板
                </Tag>
              )}
              保存為可重用模板
            </Checkbox>
            <div className="flow-toolbar">
              <Button onClick={() => handleAddNode('data_input')}>Add input</Button>
              <Button onClick={() => handleAddNode('transform')}>Add transform</Button>
              <Button onClick={() => handleAddNode('calculate')}>Add calculate</Button>
              <Button onClick={() => handleAddNode('condition')}>Add condition</Button>
              <Button onClick={() => handleAddNode('output')}>Add output</Button>
            </div>
            <Space>
              <Button type="primary" onClick={handleSave} loading={saving}>
                Save
              </Button>
              <Button onClick={handleRun} loading={running}>
                Run
              </Button>
              <Button onClick={() => navigate('/')}>Back</Button>
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
              <Background />
              <MiniMap />
              <Controls />
            </ReactFlow>
          </div>
        </div>
        <div className="panel pad flow-sidebar fade-in delay-2">
          <Title level={4}>Node inspector</Title>
          <NodeInspector node={selectedNode} onChange={handleNodeChange} />
          <Divider />
          <Title level={4}>Execution output</Title>
          <div className="code-block">
            {executionResult
              ? JSON.stringify(executionResult, null, 2)
              : 'Run a chain to see output.'}
          </div>
        </div>
      </div>
    </div>
  );
}
