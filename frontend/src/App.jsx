import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Home from './pages/Home.jsx';
import FlowEditor from './pages/FlowEditor.jsx';
import ReasoningChainViewer from './pages/ReasoningChainViewer.jsx';
import TemplateLibrary from './pages/TemplateLibrary.jsx';
import AnalysisTools from './pages/AnalysisTools.jsx';
import AnalysisRun from './pages/AnalysisRun.jsx';
import { auth } from './api/client.js';

const AuthGuard = ({ children }) => {
  const token = auth.getToken();
  const offlineAllowed =
    String(import.meta.env.VITE_OFFLINE_MODE || 'true')
      .toLowerCase()
      .trim() === 'true';
  const offline = offlineAllowed && auth.getOffline();
  if (!token && !offline) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <AuthGuard>
            <Home />
          </AuthGuard>
        }
      />
      <Route
        path="/analysis/tools"
        element={
          <AuthGuard>
            <AnalysisTools />
          </AuthGuard>
        }
      />
      <Route
        path="/analysis/run"
        element={
          <AuthGuard>
            <AnalysisRun />
          </AuthGuard>
        }
      />
      <Route
        path="/flow/:chainId"
        element={
          <AuthGuard>
            <FlowEditor />
          </AuthGuard>
        }
      />
      <Route
        path="/templates"
        element={
          <AuthGuard>
            <TemplateLibrary />
          </AuthGuard>
        }
      />
      <Route
        path="/view/:chainId"
        element={
          <AuthGuard>
            <ReasoningChainViewer />
          </AuthGuard>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
