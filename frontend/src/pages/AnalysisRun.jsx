import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Divider,
  Empty,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Typography,
  message,
  Upload,
  Alert,
} from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import TopNav from '../components/TopNav.jsx';
import { api, auth } from '../api/client.js';
import { offlineStorage } from '../utils/offlineStorage.js';

const { Title, Text } = Typography;

const formatDefaultValue = param => {
  if (param.default === undefined || param.default === null) {
    if (param.type === 'boolean') {
      return false;
    }
    return '';
  }
  if (param.type === 'array' || param.type === 'object') {
    try {
      return JSON.stringify(param.default, null, 2);
    } catch (error) {
      return '';
    }
  }
  return param.default;
};

const formatDefaultHint = (t, param) => {
  if (param.default === undefined || param.default === null) {
    return t('analysis.no_default');
  }
  if (param.type === 'array' || param.type === 'object') {
    try {
      return `${t('analysis.default_prefix')}${JSON.stringify(param.default)}`;
    } catch (error) {
      return t('analysis.default_prefix') + '[unreadable]';
    }
  }
  return `${t('analysis.default_prefix')}${String(param.default)}`;
};

const validateParam = (t, param, value) => {
  const isEmpty = value === '' || value === undefined || value === null;
  if (param.required && isEmpty) {
    return t('analysis.required_field');
  }
  if (isEmpty) {
    return null;
  }
  if (param.type === 'number' && Number.isNaN(Number(value))) {
    return t('analysis.must_be_number');
  }
  if ((param.type === 'array' || param.type === 'object') && typeof value === 'string') {
    try {
      JSON.parse(value);
    } catch (error) {
      return t('analysis.must_be_json');
    }
  }
  return null;
};

export default function AnalysisRun() {
  const [searchParams] = useSearchParams();
  const [tools, setTools] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedToolId, setSelectedToolId] = useState('');
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [paramValues, setParamValues] = useState({});
  const [storeOutput, setStoreOutput] = useState(true);
  const [result, setResult] = useState(null);
  const [loadingTools, setLoadingTools] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [running, setRunning] = useState(false);
  const [offlineMode, setOfflineMode] = useState(auth.getOffline());
  const [localFiles, setLocalFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const selectedTool = useMemo(
    () => tools.find(tool => tool.id === selectedToolId),
    [tools, selectedToolId]
  );

  const fetchTools = async () => {
    try {
      setLoadingTools(true);
      const data = await api.listAnalysisTools();
      const nextTools = Array.isArray(data) ? data : [];
      setTools(nextTools);
      const requestedTool = searchParams.get('tool');
      if (requestedTool && nextTools.some(tool => tool.id === requestedTool)) {
        setSelectedToolId(requestedTool);
      } else if (!selectedToolId && nextTools.length > 0) {
        setSelectedToolId(nextTools[0].id);
      }
    } catch (error) {
      message.error(error.message || t('analysis.load_tools_failed'));
    } finally {
      setLoadingTools(false);
    }
  };

  const fetchFiles = async query => {
    try {
      setLoadingFiles(true);
      const data = await api.listFiles({ limit: 50, offset: 0, q: query });
      setFiles(Array.isArray(data?.items) ? data.items : []);
    } catch (error) {
      message.error(error.message || t('analysis.load_files_failed'));
    } finally {
      setLoadingFiles(false);
    }
  };

  // 加載本地文件列表
  const loadLocalFiles = async () => {
    try {
      const allFiles = await offlineStorage.getAllFiles();
      setLocalFiles(allFiles);
    } catch (error) {
      console.error('Failed to load local files:', error);
    }
  };

  // 處理文件上傳
  const handleLocalFileUpload = async file => {
    try {
      setUploading(true);
      const uploadedFile = await offlineStorage.storeFile(file);
      message.success(`File "${file.name}" uploaded successfully`);
      await loadLocalFiles();
      return false; // 防止默認上傳行為
    } catch (error) {
      message.error(error.message || t('analysis.delete_file_failed'));
      return false;
    } finally {
      setUploading(false);
    }
  };

  // 刪除本地文件
  const deleteLocalFile = async fileId => {
    try {
      await offlineStorage.deleteFile(fileId);
      message.success(t('analysis.file_deleted'));
      await loadLocalFiles();
    } catch (error) {
      message.error(error.message || t('analysis.delete_file_failed'));
    }
  };

  useEffect(() => {
    fetchTools();
    fetchFiles();
    loadLocalFiles();
  }, []);

  useEffect(() => {
    setOfflineMode(auth.getOffline());
  }, []);

  useEffect(() => {
    if (!selectedTool) {
      setParamValues({});
      return;
    }
    const defaults = (selectedTool.parameters || []).reduce((acc, param) => {
      acc[param.name] = formatDefaultValue(param);
      return acc;
    }, {});
    setParamValues(defaults);
  }, [selectedTool]);

  const updateParamValue = (name, value) => {
    setParamValues(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const resolveParameters = () => {
    if (!selectedTool) {
      return {};
    }
    const output = {};
    for (const param of selectedTool.parameters || []) {
      const rawValue = paramValues[param.name];
      const hasValue = rawValue !== '' && rawValue !== undefined && rawValue !== null;
      if (!hasValue) {
        if (param.required) {
          throw new Error(`${param.name} is required`);
        }
        continue;
      }
      if (param.type === 'array' || param.type === 'object') {
        if (typeof rawValue === 'string') {
          try {
            const parsed = JSON.parse(rawValue);
            output[param.name] = parsed;
          } catch (error) {
            throw new Error(`${param.name} must be valid JSON`);
          }
        } else {
          output[param.name] = rawValue;
        }
        continue;
      }
      if (param.type === 'number') {
        output[param.name] = Number(rawValue);
        continue;
      }
      if (param.type === 'boolean') {
        output[param.name] = Boolean(rawValue);
        continue;
      }
      output[param.name] = rawValue;
    }
    return output;
  };

  const handleRun = async () => {
    if (!selectedToolId) {
      message.warning(t('analysis.select_tool_first'));
      return;
    }
    if (!selectedFileId) {
      message.warning(t('analysis.select_file_to_analyze'));
      return;
    }
    try {
      setRunning(true);
      const parameters = resolveParameters();
      const response = await api.runAnalysis({
        tool_id: selectedToolId,
        file_id: selectedFileId,
        parameters,
        store_output: storeOutput,
      });
      setResult(response);
      message.success(t('analysis.analysis_completed'));
    } catch (error) {
      message.error(error.message || t('analysis.run_failed'));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {t('analysis.page_title')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('analysis.page_subtitle')}
        </Text>
      </div>
      <div className="run-shell">
        <div className="panel pad run-panel fade-in delay-2">
          <Form layout="vertical">
            <Form.Item label={t('analysis.tool_label')} required>
              <Select
                loading={loadingTools}
                value={selectedToolId || undefined}
                onChange={setSelectedToolId}
                placeholder={t('analysis.tool_placeholder')}
                options={tools.map(tool => ({
                  label: `${tool.name} (${tool.id})`,
                  value: tool.id,
                }))}
              />
            </Form.Item>
            <Form.Item label={t('analysis.file_label')} required>
              <Select
                showSearch
                filterOption={false}
                loading={loadingFiles}
                value={selectedFileId || undefined}
                placeholder={t('analysis.file_placeholder')}
                onSearch={fetchFiles}
                onFocus={() => fetchFiles()}
                onChange={setSelectedFileId}
                options={files.map(file => ({
                  label: `${file.filename} (ID ${file.id})`,
                  value: file.id,
                }))}
                notFoundContent={loadingFiles ? t('analysis.loading') : t('analysis.no_files')}
              />
            </Form.Item>
            {offlineMode && (
              <>
                <Divider />
                <Alert
                  message={t('analysis.offline_mode_title')}
                  description={t('analysis.offline_mode_desc')}
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Form.Item label={t('analysis.upload_local_file')}>
                  <Upload
                    beforeUpload={handleLocalFileUpload}
                    maxCount={1}
                    accept="*"
                    disabled={uploading}
                  >
                    <Button icon={<UploadOutlined />} loading={uploading}>
                      {uploading ? t('analysis.uploading') : t('analysis.select_file_upload')}
                    </Button>
                  </Upload>
                </Form.Item>
                {localFiles.length > 0 && (
                  <Form.Item label={t('analysis.or_select_local')}>
                    <Select
                      value={selectedFileId || undefined}
                      onChange={setSelectedFileId}
                      placeholder={t('analysis.select_local_file')}
                      options={localFiles.map(file => ({
                        label: `${file.filename} (${(file.size / 1024).toFixed(2)} KB)`,
                        value: file.id,
                      }))}
                    />
                    {selectedFileId && localFiles.some(f => f.id === selectedFileId) && (
                      <Button
                        danger
                        size="small"
                        style={{ marginTop: 8 }}
                        onClick={() => {
                          deleteLocalFile(selectedFileId);
                          setSelectedFileId(null);
                        }}
                      >
                        {t('analysis.delete_selected_file')}
                      </Button>
                    )}
                  </Form.Item>
                )}
              </>
            )}
            <Divider />
            <Title level={5} style={{ marginTop: 0 }}>
              {t('analysis.parameters_title')}
            </Title>
            {(selectedTool?.parameters || []).length === 0 ? (
              <div className="panel pad">
                <Empty description={t('analysis.no_parameters')} />
              </div>
            ) : (
              (selectedTool?.parameters || []).map(param => {
                const label = `${param.name}${param.required ? ' *' : ''}`;
                const description = param.description || '';
                const value = paramValues[param.name];
                const error = validateParam(t, param, value);
                const helper = [description, `${t('analysis.type_prefix')}${param.type}`, formatDefaultHint(t, param)]
                  .filter(Boolean)
                  .join(' · ');
                if (param.type === 'number') {
                  return (
                    <Form.Item
                      key={param.name}
                      label={label}
                      extra={helper}
                      validateStatus={error ? 'error' : undefined}
                      help={error}
                    >
                      <InputNumber
                        style={{ width: '100%' }}
                        value={value === '' ? undefined : value}
                        onChange={nextValue => updateParamValue(param.name, nextValue)}
                        placeholder={param.default !== undefined ? String(param.default) : ''}
                      />
                    </Form.Item>
                  );
                }
                if (param.type === 'boolean') {
                  return (
                    <Form.Item
                      key={param.name}
                      label={label}
                      extra={helper}
                      validateStatus={error ? 'error' : undefined}
                      help={error}
                    >
                      <Switch
                        checked={Boolean(value)}
                        onChange={checked => updateParamValue(param.name, checked)}
                      />
                    </Form.Item>
                  );
                }
                if (param.type === 'array' || param.type === 'object') {
                  return (
                    <Form.Item
                      key={param.name}
                      label={label}
                      extra={`${helper} (JSON)`}
                      validateStatus={error ? 'error' : undefined}
                      help={error}
                    >
                      <Input.TextArea
                        value={value}
                        onChange={event => updateParamValue(param.name, event.target.value)}
                        autoSize={{ minRows: 2 }}
                        placeholder={param.type === 'array' ? '[]' : '{}'}
                      />
                    </Form.Item>
                  );
                }
                return (
                  <Form.Item
                    key={param.name}
                    label={label}
                    extra={helper}
                    validateStatus={error ? 'error' : undefined}
                    help={error}
                  >
                    <Input
                      value={value}
                      onChange={event => updateParamValue(param.name, event.target.value)}
                      placeholder={param.default !== undefined ? String(param.default) : ''}
                    />
                  </Form.Item>
                );
              })
            )}
            <Divider />
            <Form.Item label={t('analysis.store_output_label')}>
              <Switch checked={storeOutput} onChange={setStoreOutput} />
            </Form.Item>
            <Button type="primary" onClick={handleRun} loading={running} block>
              {t('analysis.run_button')}
            </Button>
          </Form>
        </div>
        <div className="panel pad run-output fade-in delay-2">
          <Title level={4}>{t('analysis.output_title')}</Title>
          <div className="code-block">
            {result ? JSON.stringify(result, null, 2) : t('analysis.output_placeholder')}
          </div>
        </div>
      </div>
    </div>
  );
}
