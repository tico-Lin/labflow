import React, { useState } from "react";
import { Button, Form, Input, Typography, message } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

const { Title, Text } = Typography;

export default function Register() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleFinish = async (values) => {
    try {
      setLoading(true);
      await api.register(values);
      message.success("Account created. Please sign in.");
      navigate("/login");
    } catch (error) {
      message.error(error.message || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="panel pad auth-card fade-in">
        <Title level={2}>Create account</Title>
        <Text type="secondary">LabFlow uses roles to manage access.</Text>
        <Form layout="vertical" onFinish={handleFinish} style={{ marginTop: 24 }}>
          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: "Username is required." }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: "Password is required." }]}
          >
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            Create account
          </Button>
        </Form>
        <Text type="secondary" style={{ display: "block", marginTop: 16 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </Text>
      </div>
    </div>
  );
}
