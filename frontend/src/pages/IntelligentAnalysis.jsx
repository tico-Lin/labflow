import React, { useState, useEffect } from 'react';
import {
  Button,
  Card,
  Col,
  Row,
  Upload,
  message,
  Spin,
  Typography,
  Tabs,
  Tag,
  Progress,
  Descriptions,
  List,
  Alert,
  Space,
  Divider,
  Select,
} from 'antd';
import {
  UploadOutlined,
  FileSearchOutlined,
  TagsOutlined,
  FormOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;

export default function IntelligentAnalysis() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');
  const [file, setFile] = useState(null);
  const [fileId, setFileId] = useState(null);
  const [files, setFiles] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);

  // 載入已有檔案列表
  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const data = await api.listFiles({ limit: 100 });
        setFiles(data.files || []);
      } catch (error) {
        console.error('Failed to load files:', error);
      }
    };
    fetchFiles();
  }, []);

  // 執行完整智能分析
  const handleCompleteAnalysis = async () => {
    if (!file && !fileId) {
      message.warning(t('intelligence.select_file_first'));
      return;
    }

    try {
      setLoading(true);
      setAnalysisResult(null);

      let result;

      if (file) {
        // 方案1: 先上傳檔案，獲取file_id，然後分析
        message.info(t('intelligence.uploading_file'));

        // 這裡需要檔案上傳API（假設存在）
        // 暫時使用檔案識別API
        const identifyResult = await api.identifyFile(file);

        // 由於我們沒有file_id，我們將分步調用
        const namingResult = await api.suggestNaming(file.name);

        result = {
          success: true,
          data: {
            filename: file.name,
            identification: identifyResult.data,
            naming: namingResult.data,
            tags: { error: '需要file_id才能推薦標籤' },
            conclusion: { error: '需要file_id才能生成結論' },
          },
        };
      } else {
        // 方案2: 使用已有檔案ID
        result = await api.completeAnalysis(fileId, { language: 'zh', topKTags: 10 });
      }

      if (result.success) {
        setAnalysisResult(result.data);
        message.success(t('intelligence.analysis_complete'));
      } else {
        message.error(t('common.error'));
      }
    } catch (error) {
      message.error(error.message || t('intelligence.analysis_error'));
      console.error('Analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 單獨執行檔案識別
  const handleIdentification = async () => {
    if (!file && !fileId) {
      message.warning(t('intelligence.select_file_first'));
      return;
    }

    try {
      setLoading(true);
      const result = await api.identifyFile(file || fileId);

      if (result.success) {
        setAnalysisResult({
          ...analysisResult,
          filename: file?.name || `File ${fileId}`,
          identification: result.data,
        });
        message.success(t('intelligence.identification_complete'));
      }
    } catch (error) {
      message.error(error.message || t('intelligence.identification_failed'));
    } finally {
      setLoading(false);
    }
  };

  // 單獨執行命名建議
  const handleNamingSuggestion = async () => {
    const filename = file?.name || files.find(f => f.id === fileId)?.filename;

    if (!filename) {
      message.warning(t('intelligence.select_file_first'));
      return;
    }

    try {
      setLoading(true);
      const result = await api.suggestNaming(filename);

      if (result.success) {
        setAnalysisResult({
          ...analysisResult,
          filename,
          naming: result.data,
        });
        message.success(t('intelligence.naming_complete'));
      }
    } catch (error) {
      message.error(error.message || t('intelligence.naming_failed'));
    } finally {
      setLoading(false);
    }
  };

  // 單獨執行標籤推薦
  const handleTagRecommendation = async () => {
    if (!fileId) {
      message.warning(t('intelligence.tag_recommendation_requires_file'));
      return;
    }

    try {
      setLoading(true);
      const result = await api.recommendTags(fileId, { topK: 10 });

      if (result.success) {
        setAnalysisResult({
          ...analysisResult,
          tags: result.data,
        });
        message.success(t('intelligence.tags_complete'));
      }
    } catch (error) {
      message.error(error.message || t('intelligence.tags_failed'));
    } finally {
      setLoading(false);
    }
  };

  // 單獨執行結論生成
  const handleConclusionGeneration = async () => {
    if (!fileId) {
      message.warning(t('intelligence.conclusion_generation_requires_file'));
      return;
    }

    try {
      setLoading(true);
      const result = await api.generateConclusion(fileId, 'zh');

      if (result.success) {
        setAnalysisResult({
          ...analysisResult,
          conclusion: result.data,
        });
        message.success(t('intelligence.conclusion_complete'));
      }
    } catch (error) {
      message.error(error.message || t('intelligence.conclusion_failed'));
    } finally {
      setLoading(false);
    }
  };

  // 檔案上傳配置
  const uploadProps = {
    beforeUpload: file => {
      setFile(file);
      setFileId(null); // 清除已選擇的檔案ID
      message.success(t('intelligence.file_selected', { filename: file.name }));
      return false; // 阻止自動上傳
    },
    maxCount: 1,
    onRemove: () => {
      setFile(null);
    },
  };

  // 渲染檔案識別結果
  const renderIdentification = identification => {
    if (!identification) return null;
    if (identification.error) {
      return <Alert type="error" message={identification.error} />;
    }

    const confidence = identification.confidence || 0;
    const fileType = identification.file_type || 'unknown';

    return (
      <Card
        title={
          <>
            <FileSearchOutlined /> {t('intelligence.file_identification')}
          </>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label={t('file.file_type')}>
            <Tag color={fileType !== 'unknown' ? 'blue' : 'default'}>{fileType.toUpperCase()}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="置信度">
            <Progress percent={(confidence * 100).toFixed(0)} size="small" />
          </Descriptions.Item>
          <Descriptions.Item label={t('file.file_size')}>
            {identification.file_size ? `${(identification.file_size / 1024).toFixed(2)} KB` : '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('file.file_hash')}>
            <Text code style={{ fontSize: 11 }}>
              {identification.file_hash?.substring(0, 16) || '-'}
            </Text>
          </Descriptions.Item>
        </Descriptions>

        {/* XRD 特定特徵 */}
        {fileType === 'xrd' && identification.xrd_peak_count && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            message="XRD 特徵"
            description={
              <div>
                <Text>峰值數量: {identification.xrd_peak_count}</Text>
                {identification.xrd_2theta_min && (
                  <Text>
                    {' '}
                    | 2θ範圍: {identification.xrd_2theta_min}° - {identification.xrd_2theta_max}°
                  </Text>
                )}
              </div>
            }
          />
        )}

        {/* EIS 特定特徵 */}
        {fileType === 'eis' && identification.eis_freq_min && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            message="EIS 特徵"
            description={
              <Text>
                頻率範圍: {identification.eis_freq_min} Hz - {identification.eis_freq_max} Hz
              </Text>
            }
          />
        )}

        {/* CV 特定特徵 */}
        {fileType === 'cv' && identification.cv_voltage_min && (
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            message="CV 特徵"
            description={
              <Text>
                電壓範圍: {identification.cv_voltage_min} V - {identification.cv_voltage_max} V
              </Text>
            }
          />
        )}
      </Card>
    );
  };

  // 渲染命名建議結果
  const renderNaming = naming => {
    if (!naming) return null;
    if (naming.error) {
      return <Alert type="error" message={naming.error} />;
    }

    const confidence = naming.confidence || 0;

    return (
      <Card
        title={
          <>
            <FormOutlined /> {t('intelligence.naming_suggestion')}
          </>
        }
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            type="success"
            message="建議的標準化檔名"
            description={
              <Text strong copyable>
                {naming.standard_name}
              </Text>
            }
            icon={<CheckCircleOutlined />}
          />

          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="原始檔名">{naming.original_filename}</Descriptions.Item>
            <Descriptions.Item label="分析信心度">
              <Progress percent={(confidence * 100).toFixed(0)} size="small" />
            </Descriptions.Item>
            <Descriptions.Item label="樣品名稱">
              <Tag color="geekblue">{naming.sample_name || '-'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="組成信息">
              <Tag color="purple">{naming.composition || '-'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="儀器類型">
              <Tag color="cyan">{naming.instrument_type?.toUpperCase() || '-'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="實驗類型">
              <Tag color="green">{naming.experiment_type || '-'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="日期">{naming.date || '-'}</Descriptions.Item>
            <Descriptions.Item label="序號">{naming.sequence || '-'}</Descriptions.Item>
          </Descriptions>
        </Space>
      </Card>
    );
  };

  // 渲染標籤推薦結果
  const renderTags = tags => {
    if (!tags) return null;
    if (tags.error) {
      return <Alert type="error" message={tags.error} />;
    }

    const recommendations = tags.recommendations || [];
    const existingTags = tags.existing_tags || [];

    return (
      <Card
        title={
          <>
            <TagsOutlined /> {t('intelligence.tag_recommendation')}
          </>
        }
        style={{ marginBottom: 16 }}
      >
        {existingTags.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text strong>已有標籤：</Text>
            <div style={{ marginTop: 8 }}>
              {existingTags.map(tag => (
                <Tag key={tag} color="default">
                  {tag}
                </Tag>
              ))}
            </div>
          </div>
        )}

        <Divider />

        <Text strong>推薦標籤：</Text>
        <List
          style={{ marginTop: 8 }}
          dataSource={recommendations}
          renderItem={item => (
            <List.Item>
              <List.Item.Meta
                avatar={<BulbOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
                title={
                  <Space>
                    <Tag color="blue">{item.tag_name}</Tag>
                    <Progress
                      type="circle"
                      percent={(item.score * 100).toFixed(0)}
                      width={40}
                      format={p => `${p}%`}
                    />
                  </Space>
                }
                description={
                  <div>
                    <Text type="secondary">{item.reason || '基於檔案特性推薦'}</Text>
                    <div style={{ marginTop: 4 }}>
                      {item.sources?.map(source => (
                        <Tag key={source} color="green" style={{ fontSize: 11 }}>
                          {source}
                        </Tag>
                      ))}
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    );
  };

  // 渲染結論結果
  const renderConclusion = conclusion => {
    if (!conclusion) return null;
    if (conclusion.error) {
      return <Alert type="error" message={conclusion.error} />;
    }

    return (
      <Card
        title={
          <>
            <InfoCircleOutlined /> {t('intelligence.conclusion_generation')}
          </>
        }
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Alert
            type="info"
            message={conclusion.title}
            description={
              <div>
                <Paragraph>{conclusion.summary}</Paragraph>
                <Text type="secondary">
                  置信度: {((conclusion.confidence || 0) * 100).toFixed(0)}% | 生成時間:{' '}
                  {new Date(conclusion.generated_at).toLocaleString()}
                </Text>
              </div>
            }
          />

          {conclusion.sections?.map((section, idx) => (
            <Card key={idx} size="small" type="inner" title={section.title}>
              <Paragraph>{section.content}</Paragraph>
              {section.evidence?.length > 0 && (
                <div>
                  <Text strong>證據：</Text>
                  <ul>
                    {section.evidence.map((ev, i) => (
                      <li key={i}>
                        <Text type="secondary">{ev}</Text>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          ))}
        </Space>
      </Card>
    );
  };

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={1} className="fade-in">
          <ThunderboltOutlined /> {t('intelligence.title')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('intelligence.subtitle')}
        </Text>
      </div>

      <div style={{ padding: '0 24px 32px' }}>
        <Row gutter={16}>
          {/* 左側：檔案輸入 */}
          <Col xs={24} lg={8}>
            <Card title={t('intelligence.select_file')} style={{ marginBottom: 16 }}>
              <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={[
                  {
                    key: 'upload',
                    label: t('intelligence.upload_tab'),
                    children: (
                      <>
                        <Dragger {...uploadProps}>
                          <p className="ant-upload-drag-icon">
                            <UploadOutlined />
                          </p>
                          <p className="ant-upload-text">{t('intelligence.drag_files')}</p>
                          <p className="ant-upload-hint">{t('intelligence.supported_formats')}</p>
                        </Dragger>
                        {file && (
                          <Alert
                            style={{ marginTop: 12 }}
                            type="success"
                            message={t('intelligence.file_selected', { filename: file.name })}
                          />
                        )}
                      </>
                    ),
                  },
                  {
                    key: 'select',
                    label: t('intelligence.select_tab'),
                    children: (
                      <>
                        <Select
                          showSearch
                          placeholder={t('intelligence.select_file')}
                          style={{ width: '100%' }}
                          value={fileId}
                          onChange={value => {
                            setFileId(value);
                            setFile(null); // 清除上傳的檔案
                          }}
                          filterOption={(input, option) =>
                            option.children.toLowerCase().includes(input.toLowerCase())
                          }
                        >
                          {files.map(f => (
                            <Select.Option key={f.id} value={f.id}>
                              {f.filename}
                            </Select.Option>
                          ))}
                        </Select>
                        {fileId && (
                          <Alert
                            style={{ marginTop: 12 }}
                            type="success"
                            message={t('intelligence.file_id_selected', { id: fileId })}
                          />
                        )}
                      </>
                    ),
                  },
                ]}
              />
            </Card>

            {/* 功能按鈕 */}
            <Card title={t('intelligence.functions')}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="primary"
                  block
                  size="large"
                  icon={<ThunderboltOutlined />}
                  onClick={handleCompleteAnalysis}
                  loading={loading}
                >
                  {t('intelligence.complete_analysis')}
                </Button>

                <Divider>{t('intelligence.or_select_function')}</Divider>

                <Button
                  block
                  icon={<FileSearchOutlined />}
                  onClick={handleIdentification}
                  loading={loading}
                >
                  {t('intelligence.file_identification')}
                </Button>

                <Button
                  block
                  icon={<FormOutlined />}
                  onClick={handleNamingSuggestion}
                  loading={loading}
                >
                  {t('intelligence.naming_suggestion')}
                </Button>

                <Button
                  block
                  icon={<TagsOutlined />}
                  onClick={handleTagRecommendation}
                  loading={loading}
                  disabled={!fileId}
                >
                  {t('intelligence.tag_recommendation')}
                </Button>

                <Button
                  block
                  icon={<InfoCircleOutlined />}
                  onClick={handleConclusionGeneration}
                  loading={loading}
                  disabled={!fileId}
                >
                  {t('intelligence.conclusion_generation')}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* 右側：分析結果 */}
          <Col xs={24} lg={16}>
            <Spin spinning={loading} tip={loading ? t('intelligence.analysis_results') : undefined}>
              {analysisResult ? (
                <div>
                  <Title level={4}>📊 {t('intelligence.analysis_result_title', { filename: analysisResult.filename })}</Title>

                  {renderIdentification(analysisResult.identification)}
                  {renderNaming(analysisResult.naming)}
                  {renderTags(analysisResult.tags)}
                  {renderConclusion(analysisResult.conclusion)}
                </div>
              ) : (
                <Card>
                  <Alert
                    type="info"
                    message={t('intelligence.select_and_analyze')}
                    description={t('intelligence.select_analyze_desc')}
                    showIcon
                  />
                </Card>
              )}
            </Spin>
          </Col>
        </Row>
      </div>
    </div>
  );
}
