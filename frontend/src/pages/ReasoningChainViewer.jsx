import React, { useCallback, useEffect, useState } from "react";
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
  Spin
} from "antd";
import { useNavigate, useParams } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  MiniMap
} from "reactflow";
import "reactflow/dist/style.css";
import TopNav from "../components/TopNav.jsx";
import { api } from "../api/client.js";

const { Title, Text, Paragraph } = Typography;

// 節點類型配色方案
const NODE_TYPE_COLORS = {
  data_input: "#52c41a",
  transform: "#1890ff",
  calculate: "#722ed1",
  condition: "#fa8c16",
  output: "#eb2f96"
};

// 執行狀態配色
const STATUS_COLORS = {
  success: "success",
  completed: "success",
  failed: "error",
  error: "error",
  running: "processing",
  pending: "default"
};

export default function ReasoningChainViewer() {
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
      setChain(chainData);

      // 轉換節點和邊
      if (Array.isArray(chainData.nodes)) {
        const mappedNodes = chainData.nodes.map((node, index) => ({
          id: node.node_id,
          type: "default",
          data: {
            label: (
              <div style={{ textAlign: "center" }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {node.name || node.node_id}
                </div>
                <Tag color={NODE_TYPE_COLORS[node.node_type] || "default"} style={{ fontSize: 10 }}>
                  {node.node_type}
                </Tag>
              </div>
            ),
            nodeType: node.node_type || "data_input",
            config: node.config || {}
          },
          position: node.position || { x: 120 * index, y: 80 * index },
          style: {
            background: "#142a33",
            border: `2px solid ${NODE_TYPE_COLORS[node.node_type] || "#555"}`,
            borderRadius: 8,
            padding: 10,
            minWidth: 120
          }
        }));

        const mappedEdges = [];
        chainData.nodes.forEach((node) => {
          (node.inputs || []).forEach((inputId) => {
            mappedEdges.push({
              id: `${inputId}-${node.node_id}`,
              source: inputId,
              target: node.node_id,
              animated: true,
              style: { stroke: "#9abdb3" }
            });
          });
        });

        setNodes(mappedNodes);
        setEdges(mappedEdges);
      }

      // 獲取執行歷史
      await fetchExecutions();
    } catch (error) {
      message.error(error.message || "載入推理鏈失敗");
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
      console.error("載入執行歷史失敗:", error);
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
      message.success("推理鏈執行已啟動");

      // 輪詢執行狀態
      const result = await pollExecution(execution.execution_id);
      setSelectedExecution(result);
      await fetchExecutions();
      message.success("執行完成");
    } catch (error) {
      message.error(error.message || "執行失敗");
    } finally {
      setExecutionLoading(false);
    }
  };

  // 輪詢執行結果
  const pollExecution = async (executionId) => {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      const result = await api.getExecution(executionId);
      if (result.status !== "running" && result.status !== "pending") {
        return result;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    return api.getExecution(executionId);
  };

  // 查看執行詳情
  const handleViewExecution = async (executionId) => {
    try {
      const execution = await api.getExecution(executionId);
      setSelectedExecution(execution);
    } catch (error) {
      message.error(error.message || "載入執行詳情失敗");
    }
  };

  if (loading) {
    return (
      <div className="app-shell">
        <TopNav />
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "50vh" }}>
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
          <Title level={2}>推理鏈不存在</Title>
          <Button onClick={() => navigate("/")}>返回列表</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopNav />
      <div className="hero">
        <Title level={2} className="fade-in">{chain.name}</Title>
        <Paragraph type="secondary" className="fade-in delay-1">
          {chain.description || "無描述"}
        </Paragraph>
        <Space className="fade-in delay-1">
          <Button type="primary" onClick={handleExecuteChain} loading={executionLoading}>
            執行推理鏈
          </Button>
          <Button onClick={() => navigate("/")}>返回列表</Button>
          {chain.is_template && <Tag color="blue">模板</Tag>}
        </Space>
      </div>

      <div className="viewer-shell">
        {/* 左側：推理鏈視覺化 */}
        <div className="panel pad fade-in delay-2">
          <Title level={4}>推理鏈結構</Title>
          <div className="flow-viewer">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
            >
              <Background color="#9abdb3" gap={16} />
              <MiniMap
                nodeColor={(node) => NODE_TYPE_COLORS[node.data?.nodeType] || "#555"}
                style={{ background: "#0b1f24" }}
              />
              <Controls />
            </ReactFlow>
          </div>

          {/* 節點詳情 */}
          {nodes.length > 0 && (
            <Card
              title="節點列表"
              size="small"
              style={{ marginTop: 16, background: "rgba(20, 42, 51, 0.95)" }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                {chain.nodes?.map((node) => (
                  <Card
                    key={node.node_id}
                    size="small"
                    style={{ background: "rgba(15, 35, 43, 0.9)" }}
                  >
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="節點 ID">{node.node_id}</Descriptions.Item>
                      <Descriptions.Item label="節點名稱">{node.name || "-"}</Descriptions.Item>
                      <Descriptions.Item label="類型">
                        <Tag color={NODE_TYPE_COLORS[node.node_type]}>{node.node_type}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="輸入節點">
                        {node.inputs?.length > 0 ? node.inputs.join(", ") : "無"}
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
                key: "history",
                label: "執行歷史",
                children: (
                  <div style={{ maxHeight: "calc(100vh - 300px)", overflow: "auto" }}>
                    {executions.length === 0 ? (
                      <Text type="secondary">尚無執行記錄</Text>
                    ) : (
                      <Timeline>
                        {executions.map((exec) => (
                          <Timeline.Item
                            key={exec.execution_id}
                            color={exec.status === "completed" ? "green" : exec.status === "failed" ? "red" : "blue"}
                          >
                            <Space direction="vertical" size="small">
                              <Space>
                                <Text strong>執行 ID: {exec.execution_id}</Text>
                                <Tag color={STATUS_COLORS[exec.status]}>{exec.status}</Tag>
                              </Space>
                              <Text type="secondary">
                                開始時間: {exec.started_at ? new Date(exec.started_at).toLocaleString() : "-"}
                              </Text>
                              {exec.execution_time_ms && (
                                <Text type="secondary">耗時: {exec.execution_time_ms.toFixed(2)} ms</Text>
                              )}
                              <Button size="small" onClick={() => handleViewExecution(exec.execution_id)}>
                                查看詳情
                              </Button>
                            </Space>
                          </Timeline.Item>
                        ))}
                      </Timeline>
                    )}
                  </div>
                )
              },
              {
                key: "result",
                label: "執行結果",
                children: (
                  <div style={{ maxHeight: "calc(100vh - 300px)", overflow: "auto" }}>
                    {selectedExecution ? (
                      <Space direction="vertical" style={{ width: "100%" }}>
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
                                : "-"}
                            </Descriptions.Item>
                            <Descriptions.Item label="完成時間">
                              {selectedExecution.completed_at
                                ? new Date(selectedExecution.completed_at).toLocaleString()
                                : "-"}
                            </Descriptions.Item>
                            <Descriptions.Item label="執行時間">
                              {selectedExecution.execution_time_ms
                                ? `${selectedExecution.execution_time_ms.toFixed(2)} ms`
                                : "-"}
                            </Descriptions.Item>
                          </Descriptions>
                        </Card>

                        {selectedExecution.error && (
                          <Card size="small" title="錯誤資訊" style={{ borderColor: "#ff4d4f" }}>
                            <pre className="code-block">{JSON.stringify(selectedExecution.error, null, 2)}</pre>
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
                )
              },
              {
                key: "info",
                label: "鏈資訊",
                children: (
                  <Card size="small">
                    <Descriptions size="small" column={1}>
                      <Descriptions.Item label="鏈 ID">{chain.id}</Descriptions.Item>
                      <Descriptions.Item label="名稱">{chain.name}</Descriptions.Item>
                      <Descriptions.Item label="描述">{chain.description || "無"}</Descriptions.Item>
                      <Descriptions.Item label="是否模板">
                        {chain.is_template ? "是" : "否"}
                      </Descriptions.Item>
                      <Descriptions.Item label="建立時間">
                        {chain.created_at ? new Date(chain.created_at).toLocaleString() : "-"}
                      </Descriptions.Item>
                      <Descriptions.Item label="更新時間">
                        {chain.updated_at ? new Date(chain.updated_at).toLocaleString() : "-"}
                      </Descriptions.Item>
                      <Descriptions.Item label="節點數量">{chain.nodes?.length || 0}</Descriptions.Item>
                    </Descriptions>
                  </Card>
                )
              }
            ]}
          />
        </div>
      </div>
    </div>
  );
}
