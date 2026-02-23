import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Divider,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Typography,
  message,
} from 'antd';
import { PlayCircleOutlined, PlusOutlined } from '@ant-design/icons';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const getTriggerOptions = (t) => [
  { value: 'on_schedule', label: t('automation.trigger_on_schedule') },
  { value: 'on_event', label: t('automation.trigger_on_event') },
  { value: 'on_file_upload', label: t('automation.trigger_on_file_upload') },
  { value: 'on_classification', label: t('automation.trigger_on_classification') },
  { value: 'manual', label: t('automation.trigger_manual') },
];

export default function AutomationCenter() {
  const { t } = useTranslation();
  const [automations, setAutomations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formState, setFormState] = useState({
    id: null,
    name: '',
    description: '',
    trigger_type: 'manual',
    trigger_config: '{}',
    actions: '[]',
    enabled: true,
  });
  const [executions, setExecutions] = useState([]);
  const [executionsOpen, setExecutionsOpen] = useState(false);
  const [executionsLoading, setExecutionsLoading] = useState(false);

  const refreshAutomations = async () => {
    try {
      setLoading(true);
      const data = await api.listAutomations({ limit: 50, skip: 0 });
      setAutomations(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error(error.message || t('automation.load_failed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAutomations();
  }, []);

  const resetForm = () => {
    setFormState({
      id: null,
      name: '',
      description: '',
      trigger_type: 'manual',
      trigger_config: '{}',
      actions: '[]',
      enabled: true,
    });
  };

  const handleSubmit = async () => {
    if (!formState.name.trim()) {
      message.warning(t('automation.enter_name'));
      return;
    }
    let triggerConfig;
    let actions;
    try {
      triggerConfig = JSON.parse(formState.trigger_config || '{}');
      actions = JSON.parse(formState.actions || '[]');
    } catch (error) {
      message.error(t('automation.invalid_json'));
      return;
    }

    try {
      if (formState.id) {
        await api.updateAutomation(formState.id, {
          name: formState.name.trim(),
          description: formState.description.trim(),
          trigger_config: triggerConfig,
          actions,
          enabled: formState.enabled,
        });
        message.success(t('automation.automation_updated'));
      } else {
        await api.createAutomation({
          name: formState.name.trim(),
          description: formState.description.trim(),
          trigger_type: formState.trigger_type,
          trigger_config: triggerConfig,
          actions,
        });
        message.success(t('automation.automation_created'));
      }
      resetForm();
      refreshAutomations();
    } catch (error) {
      message.error(error.message || t('automation.save_failed'));
    }
  };

  const handleEdit = async automation => {
    try {
      const detail = await api.getAutomation(automation.id);
      setFormState({
        id: detail.id,
        name: detail.name || '',
        description: detail.description || '',
        trigger_type: detail.trigger_type || 'manual',
        trigger_config: JSON.stringify(detail.trigger_config || {}, null, 2),
        actions: JSON.stringify(detail.actions || [], null, 2),
        enabled: detail.enabled !== false,
      });
    } catch (error) {
      message.error(error.message || t('automation.load_detail_failed'));
    }
  };

  const handleDelete = async id => {
    try {
      await api.deleteAutomation(id);
      message.success(t('automation.automation_deleted'));
      refreshAutomations();
    } catch (error) {
      message.error(error.message || t('automation.delete_failed'));
    }
  };

  const handleExecute = async id => {
    try {
      await api.executeAutomation(id, null);
      message.success(t('automation.execute_success'));
    } catch (error) {
      message.error(error.message || t('automation.execute_failed'));
    }
  };

  const handleLoadExecutions = async id => {
    try {
      setExecutionsLoading(true);
      const data = await api.listAutomationExecutions(id, { limit: 20, skip: 0 });
      setExecutions(Array.isArray(data) ? data : []);
      setExecutionsOpen(true);
    } catch (error) {
      message.error(error.message || t('automation.load_executions_failed'));
    } finally {
      setExecutionsLoading(false);
    }
  };

  const columns = [
    { title: t('automation.name_column'), dataIndex: 'name' },
    { title: t('automation.trigger_column'), dataIndex: 'trigger_type', width: 140 },
    {
      title: t('automation.enabled_column'),
      dataIndex: 'enabled',
      render: value => (value ? t('automation.enabled_yes') : t('automation.enabled_no')),
      width: 90,
    },
    {
      title: t('automation.created_column'),
      dataIndex: 'created_at',
      render: value => (value ? new Date(value).toLocaleString() : '-'),
      width: 180,
    },
    {
      title: t('automation.actions_column'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => handleEdit(record)}>
            {t('automation.edit_button')}
          </Button>
          <Button
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(record.id)}
          >
            {t('automation.execute_button')}
          </Button>
          <Button size="small" onClick={() => handleLoadExecutions(record.id)}>
            {t('automation.executions_button')}
          </Button>
          <Button size="small" danger onClick={() => handleDelete(record.id)}>
            {t('automation.delete_button')}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {t('pages.automation_center')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('pages.create_execute_monitor')}
        </Text>
      </div>
      <div style={{ padding: '0 24px 32px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Card className="panel">
            <Title level={4}>{t('pages.automation_builder')}</Title>
            <Paragraph type="secondary">{t('pages.provide_trigger_config')}</Paragraph>
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <Input
                placeholder={t('automation.automation_name')}
                value={formState.name}
                onChange={event => setFormState(prev => ({ ...prev, name: event.target.value }))}
              />
              <Input
                placeholder={t('common.description')}
                value={formState.description}
                onChange={event =>
                  setFormState(prev => ({ ...prev, description: event.target.value }))
                }
              />
              <Space align="center">
                <Text>{t('automation.trigger_type')}</Text>
                <Select
                  style={{ minWidth: 180 }}
                  options={getTriggerOptions(t)}
                  value={formState.trigger_type}
                  onChange={value => setFormState(prev => ({ ...prev, trigger_type: value }))}
                />
                <Text>{t('automation.enabled')}</Text>
                <Switch
                  checked={formState.enabled}
                  onChange={value => setFormState(prev => ({ ...prev, enabled: value }))}
                />
              </Space>
              <TextArea
                rows={5}
                value={formState.trigger_config}
                onChange={event =>
                  setFormState(prev => ({ ...prev, trigger_config: event.target.value }))
                }
                placeholder='{"schedule": "0 0 * * *"}'
              />
              <TextArea
                rows={6}
                value={formState.actions}
                onChange={event => setFormState(prev => ({ ...prev, actions: event.target.value }))}
                placeholder='[{"type": "execute_chain", "chain_id": "..."}]'
              />
              <Space>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleSubmit}>
                  {formState.id ? t('automation.update_automation') : t('automation.create_automation')}
                </Button>
                <Button onClick={resetForm}>{t('automation.clear_button')}</Button>
              </Space>
            </Space>
          </Card>
          <Card className="panel">
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Title level={4} style={{ margin: 0 }}>
                {t('automation.automations_title')}
              </Title>
              <Button icon={<PlayCircleOutlined />} onClick={refreshAutomations}>
                {t('automation.refresh_button')}
              </Button>
            </Space>
            <Divider />
            <Table
              rowKey="id"
              dataSource={automations}
              loading={loading}
              columns={columns}
              pagination={{ pageSize: 8 }}
            />
          </Card>
        </Space>
      </div>
      <Modal
        title={t('automation.executions_modal_title')}
        open={executionsOpen}
        onCancel={() => setExecutionsOpen(false)}
        footer={null}
        width={720}
      >
        <Table
          rowKey="id"
          dataSource={executions}
          loading={executionsLoading}
          columns={[
            { title: t('automation.execution_id'), dataIndex: 'id' },
            { title: t('automation.execution_status'), dataIndex: 'status' },
            {
              title: t('automation.execution_started'),
              dataIndex: 'started_at',
              render: value => (value ? new Date(value).toLocaleString() : '-'),
            },
            {
              title: t('automation.execution_completed'),
              dataIndex: 'completed_at',
              render: value => (value ? new Date(value).toLocaleString() : '-'),
            },
          ]}
          pagination={{ pageSize: 6 }}
        />
      </Modal>
    </div>
  );
}
