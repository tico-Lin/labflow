import React, { useEffect, useState } from 'react';
import { Button, Empty, Typography, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import TopNav from '../components/TopNav.jsx';
import { api } from '../api/client.js';
import { useTranslation } from '../i18n.jsx';

const { Title, Text, Paragraph } = Typography;

export default function AnalysisTools() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchTools = async () => {
    try {
      setLoading(true);
      const data = await api.listAnalysisTools();
      setTools(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error(error.message || t('analysis.load_tools_failed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTools();
  }, []);

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">
          {t('pages.analysis_tools_catalog')}
        </Title>
        <Text type="secondary" className="fade-in delay-1">
          {t('analysis.browse_adapters')}
        </Text>
      </div>
      <div className="tools-shell fade-in delay-2">
        {loading ? (
          <div className="panel pad">{t('common.loading')}</div>
        ) : tools.length === 0 ? (
          <div className="panel pad">
            <Empty description={t('analysis.no_tools')} />
          </div>
        ) : (
          tools.map(tool => {
            const requiredParams = (tool.parameters || [])
              .filter(param => param.required)
              .map(param => param.name);
            return (
              <div className="tool-card" key={tool.id}>
                <div>
                  <Title level={4} style={{ margin: 0 }}>
                    {tool.name}
                  </Title>
                  <Text type="secondary">
                    {tool.id} · v{tool.version}
                  </Text>
                </div>
                <Paragraph style={{ margin: 0 }}>{tool.description}</Paragraph>
                <div className="tool-meta">
                  {(tool.input_types || []).map(input => (
                    <span className="pill" key={`${tool.id}-input-${input}`}>
                      {t('analysis.input_label')}: {input}
                    </span>
                  ))}
                  {(tool.outputs || []).map(output => (
                    <span className="pill" key={`${tool.id}-output-${output}`}>
                      {t('analysis.output_label')}: {output}
                    </span>
                  ))}
                </div>
                <div>
                  <Text type="secondary">{t('analysis.parameters_label')}: {(tool.parameters || []).length}</Text>
                  {requiredParams.length > 0 ? (
                    <Paragraph style={{ margin: '4px 0 0' }}>
                      {t('analysis.required_label')}: {requiredParams.join(', ')}
                    </Paragraph>
                  ) : null}
                </div>
                <div className="tool-footer">
                  <Text type="secondary">{t('analysis.ready_to_run')}</Text>
                  <Button
                    type="primary"
                    onClick={() => navigate(`/analysis/run?tool=${encodeURIComponent(tool.id)}`)}
                  >
                    {t('analysis.run_tool')}
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
