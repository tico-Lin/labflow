import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Home from './pages/Home.jsx';
import FlowEditor from './pages/FlowEditor.jsx';
import ReasoningChainViewer from './pages/ReasoningChainViewer.jsx';
import TemplateLibrary from './pages/TemplateLibrary.jsx';
import AnalysisTools from './pages/AnalysisTools.jsx';
import AnalysisRun from './pages/AnalysisRun.jsx';
import IntelligentAnalysis from './pages/IntelligentAnalysis.jsx';
import DataManagement from './pages/DataManagement.jsx';
import AutomationCenter from './pages/AutomationCenter.jsx';
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
  // Auto-enable offline mode in development for testing
  useEffect(() => {
    const isDev = import.meta.env.DEV;
    const offlineAllowed =
      String(import.meta.env.VITE_OFFLINE_MODE || 'true')
        .toLowerCase()
        .trim() === 'true';

    // In development, auto-enable offline mode if not already logged in
    if (isDev && offlineAllowed && !auth.getToken() && !auth.getOffline()) {
      auth.clearToken();
      auth.setOffline(true);
    }
  }, []);
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
        path="/data"
        element={
          <AuthGuard>
            <DataManagement />
          </AuthGuard>
        }
      />
      <Route
        path="/automation"
        element={
          <AuthGuard>
            <AutomationCenter />
          </AuthGuard>
        }
      />
      <Route
        path="/intelligence"
        element={
          <AuthGuard>
            <IntelligentAnalysis />
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
