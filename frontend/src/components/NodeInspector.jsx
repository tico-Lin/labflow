import React, { useEffect, useMemo, useState } from 'react';
import { Button, Input, Select, Typography, Form, Space, Card, Collapse } from 'antd';

const { Text } = Typography;
const { Panel } = Collapse;

const NODE_TYPES = [
  { value: 'data_input', label: 'Data Input' },
  { value: 'transform', label: 'Transform' },
  { value: 'calculate', label: 'Calculate' },
  { value: 'condition', label: 'Condition' },
  { value: 'output', label: 'Output' },
];

// 針對不同節點類型的配置選項
const DATA_INPUT_SOURCES = [
  { value: 'global', label: 'Global Input' },
  { value: 'file', label: 'File' },
  { value: 'database', label: 'Database' },
];

const TRANSFORM_OPERATIONS = [
  { value: 'smooth', label: 'Smooth' },
  { value: 'normalize', label: 'Normalize' },
  { value: 'filter', label: 'Filter' },
  { value: 'convert_units', label: 'Convert Units' },
];

const CALCULATE_OPERATIONS = [
  { value: 'peak_fit', label: 'Peak Fitting' },
  { value: 'impedance_analysis', label: 'Impedance Analysis' },
  { value: 'statistics', label: 'Statistics' },
  { value: 'custom', label: 'Custom Calculation' },
];

const CONDITION_OPERATORS = [
  { value: 'gt', label: 'Greater Than (>)' },
  { value: 'lt', label: 'Less Than (<)' },
  { value: 'eq', label: 'Equal (==)' },
  { value: 'gte', label: 'Greater or Equal (>=)' },
  { value: 'lte', label: 'Less or Equal (<=)' },
];

const OUTPUT_TYPES = [
  { value: 'return', label: 'Return Value' },
  { value: 'plot', label: 'Plot/Chart' },
  { value: 'save_file', label: 'Save File' },
  { value: 'conclusion', label: 'Conclusion' },
];

// 為不同節點類型渲染特定的配置表單
function NodeConfigForm({ nodeType, config, onChange }) {
  const updateConfig = (key, value) => {
    onChange({ ...config, [key]: value });
  };

  switch (nodeType) {
    case 'data_input':
      return (
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Source Type</Text>
            <Select
              value={config.source_type || 'global'}
              onChange={value => updateConfig('source_type', value)}
              options={DATA_INPUT_SOURCES}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <Text type="secondary">Key Path</Text>
            <Input
              value={config.key_path || ''}
              onChange={e => updateConfig('key_path', e.target.value)}
              placeholder="e.g., file_id, data.measurements"
            />
          </div>
        </Space>
      );

    case 'transform':
      return (
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Operation</Text>
            <Select
              value={config.operation || 'smooth'}
              onChange={value => updateConfig('operation', value)}
              options={TRANSFORM_OPERATIONS}
              style={{ width: '100%' }}
            />
          </div>
          {config.operation === 'smooth' && (
            <div>
              <Text type="secondary">Window Size</Text>
              <Input
                type="number"
                value={config.window_size || 5}
                onChange={e => updateConfig('window_size', parseInt(e.target.value))}
              />
            </div>
          )}
          {config.operation === 'convert_units' && (
            <>
              <div>
                <Text type="secondary">From Unit</Text>
                <Input
                  value={config.from_unit || ''}
                  onChange={e => updateConfig('from_unit', e.target.value)}
                  placeholder="e.g., nm, mm"
                />
              </div>
              <div>
                <Text type="secondary">To Unit</Text>
                <Input
                  value={config.to_unit || ''}
                  onChange={e => updateConfig('to_unit', e.target.value)}
                  placeholder="e.g., μm, cm"
                />
              </div>
            </>
          )}
        </Space>
      );

    case 'calculate':
      return (
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Operation</Text>
            <Select
              value={config.operation || 'statistics'}
              onChange={value => updateConfig('operation', value)}
              options={CALCULATE_OPERATIONS}
              style={{ width: '100%' }}
            />
          </div>
          {config.operation === 'custom' && (
            <div>
              <Text type="secondary">Expression</Text>
              <Input.TextArea
                value={config.expression || ''}
                onChange={e => updateConfig('expression', e.target.value)}
                placeholder="e.g., result = sum(x) / len(x)"
                autoSize={{ minRows: 3 }}
              />
            </div>
          )}
          {config.operation === 'peak_fit' && (
            <div>
              <Text type="secondary">Model</Text>
              <Select
                value={config.model || 'gaussian'}
                onChange={value => updateConfig('model', value)}
                options={[
                  { value: 'gaussian', label: 'Gaussian' },
                  { value: 'lorentzian', label: 'Lorentzian' },
                  { value: 'voigt', label: 'Voigt' },
                ]}
                style={{ width: '100%' }}
              />
            </div>
          )}
        </Space>
      );

    case 'condition':
      return (
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Left Operand</Text>
            <Input
              value={config.left || ''}
              onChange={e => updateConfig('left', e.target.value)}
              placeholder="e.g., value, result.mean"
            />
          </div>
          <div>
            <Text type="secondary">Operator</Text>
            <Select
              value={config.operator || 'gt'}
              onChange={value => updateConfig('operator', value)}
              options={CONDITION_OPERATORS}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <Text type="secondary">Right Operand</Text>
            <Input
              value={config.right || ''}
              onChange={e => updateConfig('right', e.target.value)}
              placeholder="e.g., 0.5, threshold"
            />
          </div>
        </Space>
      );

    case 'output':
      return (
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Output Type</Text>
            <Select
              value={config.output_type || 'return'}
              onChange={value => updateConfig('output_type', value)}
              options={OUTPUT_TYPES}
              style={{ width: '100%' }}
            />
          </div>
          {config.output_type === 'plot' && (
            <>
              <div>
                <Text type="secondary">Chart Type</Text>
                <Select
                  value={config.chart_type || 'line'}
                  onChange={value => updateConfig('chart_type', value)}
                  options={[
                    { value: 'line', label: 'Line Chart' },
                    { value: 'scatter', label: 'Scatter Plot' },
                    { value: 'bar', label: 'Bar Chart' },
                  ]}
                  style={{ width: '100%' }}
                />
              </div>
              <div>
                <Text type="secondary">Title</Text>
                <Input
                  value={config.title || ''}
                  onChange={e => updateConfig('title', e.target.value)}
                  placeholder="Chart title"
                />
              </div>
            </>
          )}
          {config.output_type === 'save_file' && (
            <div>
              <Text type="secondary">File Name</Text>
              <Input
                value={config.filename || ''}
                onChange={e => updateConfig('filename', e.target.value)}
                placeholder="e.g., result.csv"
              />
            </div>
          )}
        </Space>
      );

    default:
      return <Text type="secondary">No specific config for this node type.</Text>;
  }
}

export default function NodeInspector({ node, onChange }) {
  const [rawConfig, setRawConfig] = useState(() =>
    JSON.stringify(node?.data?.config || {}, null, 2)
  );
  const [useAdvancedMode, setUseAdvancedMode] = useState(false);

  useEffect(() => {
    setRawConfig(JSON.stringify(node?.data?.config || {}, null, 2));
  }, [node]);

  const syncConfig = value => {
    setRawConfig(value);
    try {
      const parsed = value ? JSON.parse(value) : {};
      onChange({
        ...node,
        data: {
          ...node.data,
          config: parsed,
        },
      });
    } catch (error) {
      // keep invalid JSON until user fixes it
    }
  };

  const handleConfigChange = newConfig => {
    setRawConfig(JSON.stringify(newConfig, null, 2));
    onChange({
      ...node,
      data: {
        ...node.data,
        config: newConfig,
      },
    });
  };

  const nodeType = useMemo(() => node?.data?.nodeType || 'data_input', [node]);

  if (!node) {
    return <Text type="secondary">Select a node to edit its settings.</Text>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Card size="small" title="Basic Info">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">Node ID</Text>
            <Input value={node.id} disabled />
          </div>
          <div>
            <Text type="secondary">Node Label</Text>
            <Input
              value={node.data?.label}
              onChange={event =>
                onChange({
                  ...node,
                  data: { ...node.data, label: event.target.value },
                })
              }
            />
          </div>
          <div>
            <Text type="secondary">Node Type</Text>
            <Select
              options={NODE_TYPES}
              value={nodeType}
              onChange={value =>
                onChange({
                  ...node,
                  data: { ...node.data, nodeType: value },
                })
              }
              style={{ width: '100%' }}
            />
          </div>
        </Space>
      </Card>

      <Card size="small" title="Configuration">
        <Collapse
          defaultActiveKey={['form']}
          items={[
            {
              key: 'form',
              label: 'Visual Editor',
              children: (
                <NodeConfigForm
                  nodeType={nodeType}
                  config={node.data?.config || {}}
                  onChange={handleConfigChange}
                />
              ),
            },
            {
              key: 'json',
              label: 'JSON Editor (Advanced)',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Input.TextArea
                    autoSize={{ minRows: 6 }}
                    value={rawConfig}
                    onChange={event => syncConfig(event.target.value)}
                  />
                  <Button onClick={() => syncConfig(rawConfig)} type="default" size="small">
                    Apply JSON config
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
