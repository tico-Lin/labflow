import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import {
  CloudUploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FileSearchOutlined,
  PlusOutlined,
  SyncOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import TopNav from '../components/TopNav.jsx';
import { api, API_BASE_URL } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

export default function DataManagement() {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [autoClassify, setAutoClassify] = useState(true);
  const [autoTag, setAutoTag] = useState(true);
  const [batchFiles, setBatchFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [tags, setTags] = useState([]);
  const [tagsLoading, setTagsLoading] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [batchTagNames, setBatchTagNames] = useState('');
  const [tagFileId, setTagFileId] = useState(null);
  const [tagId, setTagId] = useState(null);
  const [conclusionFileId, setConclusionFileId] = useState(null);
  const [conclusions, setConclusions] = useState([]);
  const [conclusionContent, setConclusionContent] = useState('');
  const [editingConclusion, setEditingConclusion] = useState(null);
  const [annotationFileId, setAnnotationFileId] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [annotationJson, setAnnotationJson] = useState('');
  const [annotationSource, setAnnotationSource] = useState('manual');
  const [maintenanceResult, setMaintenanceResult] = useState(null);

  const fileOptions = useMemo(
    () => files.map(file => ({ label: `${file.filename} (#${file.id})`, value: file.id })),
    [files]
  );

  const tagOptions = useMemo(
    () => tags.map(tag => ({ label: `${tag.name} (#${tag.id})`, value: tag.id })),
    [tags]
  );

  const refreshFiles = async (query = '') => {
    try {
      setFilesLoading(true);
      if (query) {
        const data = await api.searchFiles({ q: query, limit: 50, offset: 0 });
        setFiles(Array.isArray(data?.items) ? data.items : []);
      } else {
        const data = await api.listFiles({ limit: 100, skip: 0 });
        setFiles(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      message.error(error.message || 'Failed to load files.');
    } finally {
      setFilesLoading(false);
    }
  };

  const refreshTags = async () => {
    try {
      setTagsLoading(true);
      const data = await api.listTags({ limit: 100, skip: 0 });
      setTags(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error(error.message || t('data_management.load_tags_failed'));
    } finally {
      setTagsLoading(false);
    }
  };

  const refreshConclusions = async fileId => {
    if (!fileId) {
      setConclusions([]);
      return;
    }
    try {
      const data = await api.listConclusions(fileId, { limit: 50, skip: 0 });
      setConclusions(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error(error.message || t('data_management.load_conclusions_failed'));
    }
  };

  const refreshAnnotations = async fileId => {
    if (!fileId) {
      setAnnotations([]);
      return;
    }
    try {
      const data = await api.listAnnotations(fileId);
      setAnnotations(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error(error.message || t('data_management.load_annotations_failed'));
    }
  };

  useEffect(() => {
    refreshFiles();
    refreshTags();
  }, []);

  const handleUpload = async file => {
    try {
      await api.uploadFile(file, { auto_classify: autoClassify, auto_tag: autoTag });
      message.success(t('data_management.file_uploaded'));
      refreshFiles(searchQuery);
    } catch (error) {
      message.error(error.message || t('data_management.upload_failed'));
    }
  };

  const handleBatchUpload = async () => {
    if (batchFiles.length === 0) {
      message.warning(t('data_management.select_files_warning'));
      return;
    }
    try {
      await api.batchUploadFiles(batchFiles);
      message.success(t('data_management.batch_upload_success'));
      setBatchFiles([]);
      refreshFiles(searchQuery);
    } catch (error) {
      message.error(error.message || t('data_management.batch_upload_failed'));
    }
  };

  const handleDeleteFiles = async ids => {
    try {
      if (ids.length === 1) {
        await api.deleteFile(ids[0]);
      } else {
        await api.batchDeleteFiles(ids);
      }
      message.success(t('data_management.delete_completed'));
      setSelectedFileIds([]);
      refreshFiles(searchQuery);
    } catch (error) {
      message.error(error.message || t('data_management.delete_failed'));
    }
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim()) {
      message.warning(t('data_management.enter_tag_name'));
      return;
    }
    try {
      await api.createTag(newTagName.trim());
      message.success(t('data_management.tag_created'));
      setNewTagName('');
      refreshTags();
    } catch (error) {
      message.error(error.message || t('data_management.create_tag_failed'));
    }
  };

  const handleBatchCreateTags = async () => {
    const names = batchTagNames
      .split(',')
      .map(name => name.trim())
      .filter(Boolean);
    if (names.length === 0) {
      message.warning(t('data_management.enter_tag_names'));
      return;
    }
    try {
      await api.batchCreateTags(names);
      message.success(t('data_management.batch_tags_created'));
      setBatchTagNames('');
      refreshTags();
    } catch (error) {
      message.error(error.message || t('data_management.batch_create_failed'));
    }
  };

  const handleAttachTag = async () => {
    if (!tagFileId || !tagId) {
      message.warning(t('data_management.select_file_and_tag'));
      return;
    }
    try {
      await api.addTagToFile(tagFileId, tagId);
      message.success(t('data_management.tag_attached'));
    } catch (error) {
      message.error(error.message || t('data_management.attach_failed'));
    }
  };

  const handleRemoveTag = async () => {
    if (!tagFileId || !tagId) {
      message.warning(t('data_management.select_file_and_tag'));
      return;
    }
    try {
      await api.removeTagFromFile(tagFileId, tagId);
      message.success(t('data_management.tag_removed'));
    } catch (error) {
      message.error(error.message || t('data_management.remove_failed'));
    }
  };

  const handleCreateConclusion = async () => {
    if (!conclusionFileId) {
      message.warning(t('data_management.select_file_first'));
      return;
    }
    if (!conclusionContent.trim()) {
      message.warning(t('data_management.enter_conclusion_content'));
      return;
    }
    try {
      await api.createConclusion(conclusionFileId, conclusionContent.trim());
      message.success(t('data_management.conclusion_created'));
      setConclusionContent('');
      refreshConclusions(conclusionFileId);
    } catch (error) {
      message.error(error.message || t('data_management.create_conclusion_failed'));
    }
  };

  const handleUpdateConclusion = async () => {
    if (!editingConclusion) {
      return;
    }
    try {
      await api.updateConclusion(editingConclusion.id, editingConclusion.content);
      message.success(t('data_management.conclusion_updated'));
      setEditingConclusion(null);
      refreshConclusions(conclusionFileId);
    } catch (error) {
      message.error(error.message || t('data_management.update_failed'));
    }
  };

  const handleDeleteConclusion = async id => {
    try {
      await api.deleteConclusion(id);
      message.success(t('data_management.conclusion_deleted'));
      refreshConclusions(conclusionFileId);
    } catch (error) {
      message.error(error.message || t('data_management.delete_failed'));
    }
  };

  const handleCreateAnnotation = async () => {
    if (!annotationFileId) {
      message.warning(t('data_management.select_file_first'));
      return;
    }
    if (!annotationJson.trim()) {
      message.warning(t('data_management.enter_annotation_json'));
      return;
    }
    try {
      const data = JSON.parse(annotationJson);
      await api.createAnnotation(annotationFileId, data, annotationSource);
      message.success(t('data_management.annotation_created'));
      setAnnotationJson('');
      refreshAnnotations(annotationFileId);
    } catch (error) {
      message.error(error.message || t('data_management.create_annotation_failed'));
    }
  };

  const handleFileStatus = async () => {
    try {
      const data = await api.getFileStatus();
      setMaintenanceResult(data);
      message.success(t('data_management.file_status_loaded'));
    } catch (error) {
      message.error(error.message || t('data_management.status_check_failed'));
    }
  };

  const handleSyncFiles = async () => {
    try {
      const data = await api.syncFiles();
      setMaintenanceResult(data);
      message.success(t('data_management.sync_completed'));
    } catch (error) {
      message.error(error.message || t('data_management.sync_failed'));
    }
  };

  const filesColumns = [
    {
      title: t('data_management.id_column'),
      dataIndex: 'id',
      width: 80,
    },
    {
      title: t('data_management.filename_column'),
      dataIndex: 'filename',
      render: value => <Text>{value}</Text>,
    },
    {
      title: t('data_management.hash_column'),
      dataIndex: 'file_hash',
      render: value => (value ? <Text code>{value.slice(0, 10)}...</Text> : '-'),
    },
    {
      title: t('data_management.created_column'),
      dataIndex: 'created_at',
      render: value => (value ? new Date(value).toLocaleString() : '-'),
    },
    {
      title: t('data_management.actions_column'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            href={`${API_BASE_URL}/files/${record.id}/download`}
            target="_blank"
          >
            {t('data_management.download_button')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteFiles([record.id])}
          >
            {t('data_management.delete_button')}
          </Button>
        </Space>
      ),
    },
  ];

  const conclusionsColumns = [
    {
      title: t('data_management.id_column'),
      dataIndex: 'id',
      width: 80,
    },
    {
      title: t('data_management.content_column'),
      dataIndex: 'content',
      render: value => <Paragraph>{value}</Paragraph>,
    },
    {
      title: t('data_management.updated_column'),
      dataIndex: 'updated_at',
      render: value => (value ? new Date(value).toLocaleString() : '-'),
    },
    {
      title: t('data_management.actions_column'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => setEditingConclusion({ ...record })}>
            {t('data_management.edit_button')}
          </Button>
          <Button size="small" danger onClick={() => handleDeleteConclusion(record.id)}>
            {t('data_management.delete_button')}
          </Button>
        </Space>
      ),
    },
  ];

  const annotationColumns = [
    {
      title: t('data_management.id_column'),
      dataIndex: 'id',
      width: 80,
    },
    {
      title: t('data_management.source_column'),
      dataIndex: 'source',
      render: value => <Tag>{value}</Tag>,
    },
    {
      title: t('data_management.data_column'),
      dataIndex: 'data',
      render: value => (
        <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(value, null, 2)}</pre>
      ),
    },
    {
      title: t('data_management.created_column'),
      dataIndex: 'created_at',
      render: value => (value ? new Date(value).toLocaleString() : '-'),
    },
  ];

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {t('pages.data_management')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('common.files_tags_conclusions_annotations')}
        </Text>
      </div>
      <div style={{ padding: '0 24px 32px' }}>
        <Tabs
          defaultActiveKey="files"
          className="fade-in delay-2"
          items={[
            {
              key: 'files',
              label: t('data_management.files_tab'),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={10}>
                    <Card className="panel" style={{ marginBottom: 16 }}>
                      <Title level={4}>{t('data_management.upload_tab')}</Title>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <Text>{t('data_management.auto_classify')}</Text>
                          <Switch checked={autoClassify} onChange={setAutoClassify} />
                          <Text>{t('data_management.auto_tag')}</Text>
                          <Switch checked={autoTag} onChange={setAutoTag} />
                        </Space>
                        <Upload
                          customRequest={({ file, onSuccess, onError }) => {
                            handleUpload(file)
                              .then(() => onSuccess?.())
                              .catch(error => onError?.(error));
                          }}
                          showUploadList={false}
                        >
                          <Button icon={<CloudUploadOutlined />}>{t('data_management.upload_file_button')}</Button>
                        </Upload>
                        <Divider />
                        <Text strong>{t('data_management.batch_upload_title')}</Text>
                        <Upload
                          multiple
                          beforeUpload={file => {
                            setBatchFiles(prev => prev.concat(file));
                            return false;
                          }}
                          fileList={batchFiles.map(file => ({ uid: file.uid, name: file.name }))}
                          onRemove={file => {
                            setBatchFiles(prev => prev.filter(item => item.uid !== file.uid));
                          }}
                        >
                          <Button icon={<PlusOutlined />}>{t('data_management.select_files')}</Button>
                        </Upload>
                        <Space>
                          <Button type="primary" onClick={handleBatchUpload}>
                            {t('data_management.run_batch_upload')}
                          </Button>
                          <Button onClick={() => setBatchFiles([])}>{t('data_management.clear_button')}</Button>
                        </Space>
                      </Space>
                    </Card>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.search_title')}</Title>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Input
                          prefix={<FileSearchOutlined />}
                          placeholder={t('data_management.search_placeholder')}
                          value={searchQuery}
                          onChange={event => setSearchQuery(event.target.value)}
                          onPressEnter={() => refreshFiles(searchQuery)}
                        />
                        <Space>
                          <Button icon={<SyncOutlined />} onClick={() => refreshFiles(searchQuery)}>
                            {t('data_management.refresh_button')}
                          </Button>
                          <Button
                            danger
                            disabled={selectedFileIds.length === 0}
                            onClick={() => handleDeleteFiles(selectedFileIds)}
                          >
                            {t('data_management.delete_selected')}
                          </Button>
                        </Space>
                      </Space>
                    </Card>
                  </Col>
                  <Col xs={24} lg={14}>
                    <Card className="panel">
                      <Title level={4}>{t('pages.files_list')}</Title>
                      <Table
                        rowKey="id"
                        columns={filesColumns}
                        dataSource={files}
                        loading={filesLoading}
                        pagination={{ pageSize: 8 }}
                        rowSelection={{
                          selectedRowKeys: selectedFileIds,
                          onChange: keys => setSelectedFileIds(keys),
                        }}
                      />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'tags',
              label: t('data_management.tags_tab'),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card className="panel" style={{ marginBottom: 16 }}>
                      <Title level={4}>{t('data_management.create_tag_title')}</Title>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Input
                          placeholder={t('data_management.tag_name_placeholder')}
                          value={newTagName}
                          onChange={event => setNewTagName(event.target.value)}
                        />
                        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateTag}>
                          {t('data_management.create_button')}
                        </Button>
                        <Divider />
                        <Text strong>{t('data_management.batch_create_title')}</Text>
                        <Input
                          placeholder={t('data_management.batch_tag_placeholder')}
                          value={batchTagNames}
                          onChange={event => setBatchTagNames(event.target.value)}
                        />
                        <Button icon={<PlusOutlined />} onClick={handleBatchCreateTags}>
                          {t('data_management.create_batch_button')}
                        </Button>
                      </Space>
                    </Card>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.attach_tag_title')}</Title>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Select
                          placeholder={t('data_management.select_file_placeholder')}
                          options={fileOptions}
                          value={tagFileId}
                          onChange={value => setTagFileId(value)}
                          showSearch
                          optionFilterProp="label"
                        />
                        <Select
                          placeholder={t('data_management.select_tag_placeholder')}
                          options={tagOptions}
                          value={tagId}
                          onChange={value => setTagId(value)}
                          showSearch
                          optionFilterProp="label"
                        />
                        <Space>
                          <Button icon={<TagsOutlined />} type="primary" onClick={handleAttachTag}>
                            {t('data_management.attach_button')}
                          </Button>
                          <Button danger onClick={handleRemoveTag}>
                            {t('data_management.remove_button')}
                          </Button>
                        </Space>
                      </Space>
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.tags_list_title')}</Title>
                      <Table
                        rowKey="id"
                        loading={tagsLoading}
                        dataSource={tags}
                        pagination={{ pageSize: 8 }}
                        columns={[
                          { title: t('data_management.id_column'), dataIndex: 'id', width: 80 },
                          { title: t('data_management.name_column'), dataIndex: 'name' },
                        ]}
                      />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'conclusions',
              label: t('data_management.conclusions_tab'),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card className="panel" style={{ marginBottom: 16 }}>
                      <Title level={4}>{t('data_management.select_file_title')}</Title>
                      <Select
                        placeholder={t('data_management.select_file_placeholder')}
                        options={fileOptions}
                        value={conclusionFileId}
                        onChange={value => {
                          setConclusionFileId(value);
                          refreshConclusions(value);
                        }}
                        showSearch
                        optionFilterProp="label"
                      />
                      <Divider />
                      <Title level={4}>{t('data_management.create_conclusion_title')}</Title>
                      <TextArea
                        rows={6}
                        value={conclusionContent}
                        onChange={event => setConclusionContent(event.target.value)}
                        placeholder={t('data_management.write_conclusion_placeholder')}
                      />
                      <Button
                        type="primary"
                        style={{ marginTop: 12 }}
                        onClick={handleCreateConclusion}
                      >
                        {t('data_management.save_conclusion_button')}
                      </Button>
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.conclusions_list_title')}</Title>
                      <Table
                        rowKey="id"
                        dataSource={conclusions}
                        pagination={{ pageSize: 6 }}
                        columns={conclusionsColumns}
                      />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'annotations',
              label: t('data_management.annotations_tab'),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.select_file_title')}</Title>
                      <Select
                        placeholder={t('data_management.select_file_placeholder')}
                        options={fileOptions}
                        value={annotationFileId}
                        onChange={value => {
                          setAnnotationFileId(value);
                          refreshAnnotations(value);
                        }}
                        showSearch
                        optionFilterProp="label"
                      />
                      <Divider />
                      <Title level={4}>{t('data_management.create_annotation_title')}</Title>
                      <TextArea
                        rows={6}
                        value={annotationJson}
                        onChange={event => setAnnotationJson(event.target.value)}
                        placeholder={t('data_management.annotation_json_placeholder')}
                      />
                      <Select
                        style={{ marginTop: 12 }}
                        value={annotationSource}
                        onChange={value => setAnnotationSource(value)}
                        options={[
                          { label: 'manual', value: 'manual' },
                          { label: 'auto', value: 'auto' },
                          { label: 'imported', value: 'imported' },
                        ]}
                      />
                      <Button
                        type="primary"
                        style={{ marginTop: 12 }}
                        onClick={handleCreateAnnotation}
                      >
                        {t('data_management.save_annotation_button')}
                      </Button>
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.annotations_list_title')}</Title>
                      <Table
                        rowKey="id"
                        dataSource={annotations}
                        pagination={{ pageSize: 6 }}
                        columns={annotationColumns}
                      />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'maintenance',
              label: t('data_management.maintenance_tab'),
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.system_tasks_title')}</Title>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Button icon={<SyncOutlined />} onClick={handleFileStatus}>
                          {t('data_management.check_file_status')}
                        </Button>
                        <Button icon={<SyncOutlined />} type="primary" onClick={handleSyncFiles}>
                          {t('data_management.sync_orphaned_files')}
                        </Button>
                        <Alert
                          type="info"
                          message={t('data_management.maintenance_info')}
                        />
                      </Space>
                    </Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card className="panel">
                      <Title level={4}>{t('data_management.latest_result_title')}</Title>
                      {maintenanceResult ? (
                        <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                          {JSON.stringify(maintenanceResult, null, 2)}
                        </pre>
                      ) : (
                        <Text type="secondary">{t('data_management.run_task_prompt')}</Text>
                      )}
                    </Card>
                  </Col>
                </Row>
              ),
            },
          ]}
        />
      </div>
      <Modal
        title={t('data_management.edit_conclusion_title')}
        open={Boolean(editingConclusion)}
        onCancel={() => setEditingConclusion(null)}
        onOk={handleUpdateConclusion}
        okText={t('data_management.save_button')}
      >
        <TextArea
          rows={6}
          value={editingConclusion?.content || ''}
          onChange={event =>
            setEditingConclusion(prev => (prev ? { ...prev, content: event.target.value } : prev))
          }
        />
      </Modal>
    </div>
  );
}
