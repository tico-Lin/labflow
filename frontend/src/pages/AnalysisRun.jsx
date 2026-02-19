import React, { useEffect, useMemo, useState } from "react";
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
  message
} from "antd";
import { useSearchParams } from "react-router-dom";
import TopNav from "../components/TopNav.jsx";
import { api } from "../api/client.js";

const { Title, Text } = Typography;

const formatDefaultValue = (param) => {
  if (param.default === undefined || param.default === null) {
    if (param.type === "boolean") {
      return false;
    }
    return "";
  }
  if (param.type === "array" || param.type === "object") {
    try {
      return JSON.stringify(param.default, null, 2);
    } catch (error) {
      return "";
    }
  }
  return param.default;
};

const formatDefaultHint = (param) => {
  if (param.default === undefined || param.default === null) {
    return "No default";
  }
  if (param.type === "array" || param.type === "object") {
    try {
      return `Default: ${JSON.stringify(param.default)}`;
    } catch (error) {
      return "Default: [unreadable]";
    }
  }
  return `Default: ${String(param.default)}`;
};

const validateParam = (param, value) => {
  const isEmpty = value === "" || value === undefined || value === null;
  if (param.required && isEmpty) {
    return "Required field";
  }
  if (isEmpty) {
    return null;
  }
  if (param.type === "number" && Number.isNaN(Number(value))) {
    return "Must be a number";
  }
  if ((param.type === "array" || param.type === "object") && typeof value === "string") {
    try {
      JSON.parse(value);
    } catch (error) {
      return "Must be valid JSON";
    }
  }
  return null;
};

export default function AnalysisRun() {
  const [searchParams] = useSearchParams();
  const [tools, setTools] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedToolId, setSelectedToolId] = useState("");
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [paramValues, setParamValues] = useState({});
  const [storeOutput, setStoreOutput] = useState(true);
  const [result, setResult] = useState(null);
  const [loadingTools, setLoadingTools] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [running, setRunning] = useState(false);

  const selectedTool = useMemo(
    () => tools.find((tool) => tool.id === selectedToolId),
    [tools, selectedToolId]
  );

  const fetchTools = async () => {
    try {
      setLoadingTools(true);
      const data = await api.listAnalysisTools();
      const nextTools = Array.isArray(data) ? data : [];
      setTools(nextTools);
      const requestedTool = searchParams.get("tool");
      if (requestedTool && nextTools.some((tool) => tool.id === requestedTool)) {
        setSelectedToolId(requestedTool);
      } else if (!selectedToolId && nextTools.length > 0) {
        setSelectedToolId(nextTools[0].id);
      }
    } catch (error) {
      message.error(error.message || "Failed to load tools.");
    } finally {
      setLoadingTools(false);
    }
  };

  const fetchFiles = async (query) => {
    try {
      setLoadingFiles(true);
      const data = await api.listFiles({ limit: 50, offset: 0, q: query });
      setFiles(Array.isArray(data?.items) ? data.items : []);
    } catch (error) {
      message.error(error.message || "Failed to load files.");
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    fetchTools();
    fetchFiles();
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
    setParamValues((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const resolveParameters = () => {
    if (!selectedTool) {
      return {};
    }
    const output = {};
    for (const param of selectedTool.parameters || []) {
      const rawValue = paramValues[param.name];
      const hasValue = rawValue !== "" && rawValue !== undefined && rawValue !== null;
      if (!hasValue) {
        if (param.required) {
          throw new Error(`${param.name} is required`);
        }
        continue;
      }
      if (param.type === "array" || param.type === "object") {
        if (typeof rawValue === "string") {
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
      if (param.type === "number") {
        output[param.name] = Number(rawValue);
        continue;
      }
      if (param.type === "boolean") {
        output[param.name] = Boolean(rawValue);
        continue;
      }
      output[param.name] = rawValue;
    }
    return output;
  };

  const handleRun = async () => {
    if (!selectedToolId) {
      message.warning("Select a tool first.");
      return;
    }
    if (!selectedFileId) {
      message.warning("Select a file to analyze.");
      return;
    }
    try {
      setRunning(true);
      const parameters = resolveParameters();
      const response = await api.runAnalysis({
        tool_id: selectedToolId,
        file_id: selectedFileId,
        parameters,
        store_output: storeOutput
      });
      setResult(response);
      message.success("Analysis completed.");
    } catch (error) {
      message.error(error.message || "Run failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">Run Analysis</Title>
        <Text type="secondary" className="fade-in delay-1">
          Select a tool, attach a file, and review structured outputs.
        </Text>
      </div>
      <div className="run-shell">
        <div className="panel pad run-panel fade-in delay-2">
          <Form layout="vertical">
            <Form.Item label="Tool" required>
              <Select
                loading={loadingTools}
                value={selectedToolId || undefined}
                onChange={setSelectedToolId}
                placeholder="Select a tool"
                options={tools.map((tool) => ({
                  label: `${tool.name} (${tool.id})`,
                  value: tool.id
                }))}
              />
            </Form.Item>
            <Form.Item label="File" required>
              <Select
                showSearch
                filterOption={false}
                loading={loadingFiles}
                value={selectedFileId || undefined}
                placeholder="Search files"
                onSearch={fetchFiles}
                onFocus={() => fetchFiles()}
                onChange={setSelectedFileId}
                options={files.map((file) => ({
                  label: `${file.filename} (ID ${file.id})`,
                  value: file.id
                }))}
                notFoundContent={loadingFiles ? "Loading..." : "No files"}
              />
            </Form.Item>
            <Divider />
            <Title level={5} style={{ marginTop: 0 }}>
              Parameters
            </Title>
            {(selectedTool?.parameters || []).length === 0 ? (
              <div className="panel pad">
                <Empty description="No parameters required." />
              </div>
            ) : (
              (selectedTool?.parameters || []).map((param) => {
                const label = `${param.name}${param.required ? " *" : ""}`;
                const description = param.description || "";
                const value = paramValues[param.name];
                const error = validateParam(param, value);
                const helper = [
                  description,
                  `Type: ${param.type}`,
                  formatDefaultHint(param)
                ].filter(Boolean).join(" · ");
                if (param.type === "number") {
                  return (
                    <Form.Item
                      key={param.name}
                      label={label}
                      extra={helper}
                      validateStatus={error ? "error" : undefined}
                      help={error}
                    >
                      <InputNumber
                        style={{ width: "100%" }}
                        value={value === "" ? undefined : value}
                        onChange={(nextValue) => updateParamValue(param.name, nextValue)}
                        placeholder={param.default !== undefined ? String(param.default) : ""}
                      />
                    </Form.Item>
                  );
                }
                if (param.type === "boolean") {
                  return (
                    <Form.Item
                      key={param.name}
                      label={label}
                      extra={helper}
                      validateStatus={error ? "error" : undefined}
                      help={error}
                    >
                      <Switch
                        checked={Boolean(value)}
                        onChange={(checked) => updateParamValue(param.name, checked)}
                      />
                    </Form.Item>
                  );
                }
                if (param.type === "array" || param.type === "object") {
                  return (
                    <Form.Item
                      key={param.name}
                      label={label}
                      extra={`${helper} (JSON)`}
                      validateStatus={error ? "error" : undefined}
                      help={error}
                    >
                      <Input.TextArea
                        value={value}
                        onChange={(event) => updateParamValue(param.name, event.target.value)}
                        autoSize={{ minRows: 2 }}
                        placeholder={param.type === "array" ? "[]" : "{}"}
                      />
                    </Form.Item>
                  );
                }
                return (
                  <Form.Item
                    key={param.name}
                    label={label}
                    extra={helper}
                    validateStatus={error ? "error" : undefined}
                    help={error}
                  >
                    <Input
                      value={value}
                      onChange={(event) => updateParamValue(param.name, event.target.value)}
                      placeholder={param.default !== undefined ? String(param.default) : ""}
                    />
                  </Form.Item>
                );
              })
            )}
            <Divider />
            <Form.Item label="Store output">
              <Switch checked={storeOutput} onChange={setStoreOutput} />
            </Form.Item>
            <Button type="primary" onClick={handleRun} loading={running} block>
              Run analysis
            </Button>
          </Form>
        </div>
        <div className="panel pad run-output fade-in delay-2">
          <Title level={4}>Run output</Title>
          <div className="code-block">
            {result ? JSON.stringify(result, null, 2) : "Run a tool to see output."}
          </div>
        </div>
      </div>
    </div>
  );
}
