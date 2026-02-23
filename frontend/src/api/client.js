const API_BASE = import.meta.env.VITE_API_BASE || '/api';

// 导出用于其他模块
export const API_BASE_URL = API_BASE;

const OFFLINE_KEY = 'labflow_offline';

const getToken = () => localStorage.getItem('labflow_token');
const getOffline = () => localStorage.getItem(OFFLINE_KEY) === 'true';
const setOffline = value => {
  if (value) {
    localStorage.setItem(OFFLINE_KEY, 'true');
  } else {
    localStorage.removeItem(OFFLINE_KEY);
  }
};

const request = async (path, options = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
};

export const api = {
  login: payload => request('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  register: payload => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  listFiles: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).reduce((acc, [key, value]) => {
        if (value === undefined || value === null || value === '') {
          return acc;
        }
        acc[key] = value;
        return acc;
      }, {})
    ).toString();
    return request(`/files${query ? `?${query}` : ''}`);
  },
  searchFiles: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).reduce((acc, [key, value]) => {
        if (value === undefined || value === null || value === '') {
          return acc;
        }
        acc[key] = value;
        return acc;
      }, {})
    ).toString();
    return request(`/files/search${query ? `?${query}` : ''}`);
  },
  uploadFile: async (file, options = {}) => {
    const { auto_classify = true, auto_tag = true } = options;
    const query = new URLSearchParams({
      auto_classify: String(auto_classify),
      auto_tag: String(auto_tag),
    }).toString();
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    const headers = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(`${API_BASE}/files/?${query}`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response.json();
  },
  batchUploadFiles: async files => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    const token = getToken();
    const headers = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(`${API_BASE}/files/batch-upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response.json();
  },
  deleteFile: id => request(`/files/${id}`, { method: 'DELETE' }),
  batchDeleteFiles: ids =>
    request('/files/batch-delete', { method: 'POST', body: JSON.stringify(ids) }),
  listTags: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).reduce((acc, [key, value]) => {
        if (value === undefined || value === null || value === '') {
          return acc;
        }
        acc[key] = value;
        return acc;
      }, {})
    ).toString();
    return request(`/tags${query ? `?${query}` : ''}`);
  },
  createTag: name => request('/tags/', { method: 'POST', body: JSON.stringify({ name }) }),
  batchCreateTags: names =>
    request('/tags/batch-create', { method: 'POST', body: JSON.stringify(names) }),
  addTagToFile: (fileId, tagId) =>
    request(`/files/${fileId}/tags`, {
      method: 'POST',
      body: JSON.stringify({ tag_id: tagId }),
    }),
  removeTagFromFile: (fileId, tagId) =>
    request(`/files/${fileId}/tags/${tagId}`, { method: 'DELETE' }),
  listConclusions: (fileId, params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).reduce((acc, [key, value]) => {
        if (value === undefined || value === null || value === '') {
          return acc;
        }
        acc[key] = value;
        return acc;
      }, {})
    ).toString();
    return request(`/files/${fileId}/conclusions/${query ? `?${query}` : ''}`);
  },
  createConclusion: (fileId, content) =>
    request(`/files/${fileId}/conclusions/`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  updateConclusion: (id, content) =>
    request(`/conclusions/${id}`, { method: 'PUT', body: JSON.stringify({ content }) }),
  deleteConclusion: id => request(`/conclusions/${id}`, { method: 'DELETE' }),
  listAnnotations: fileId => request(`/files/${fileId}/annotations/`),
  createAnnotation: (fileId, data, source = 'manual') =>
    request(`/files/${fileId}/annotations/`, {
      method: 'POST',
      body: JSON.stringify({ data, source }),
    }),
  getFileStatus: () => request('/admin/file-status/'),
  syncFiles: () => request('/admin/sync-files/', { method: 'POST' }),
  listAnalysisTools: () => request('/analysis/tools'),
  runAnalysis: payload =>
    request('/analysis/run', { method: 'POST', body: JSON.stringify(payload) }),
  listChains: () => request('/reasoning/chains'),
  listTemplates: () =>
    request('/reasoning/chains?limit=100').then(chains =>
      chains.filter(chain => chain.is_template)
    ),
  getChain: id => request(`/reasoning/chains/${id}`),
  createChain: payload =>
    request('/reasoning/chains', { method: 'POST', body: JSON.stringify(payload) }),
  createChainFromTemplate: templateId =>
    request(`/reasoning/chains/${templateId}`).then(template => {
      const newChain = {
        ...template,
        name: `${template.name} (Copy)`,
        is_template: false,
      };
      delete newChain.id;
      delete newChain.created_at;
      delete newChain.updated_at;
      return request('/reasoning/chains', { method: 'POST', body: JSON.stringify(newChain) });
    }),
  updateChain: (id, payload) =>
    request(`/reasoning/chains/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteChain: id => request(`/reasoning/chains/${id}`, { method: 'DELETE' }),
  executeChain: (id, payload) =>
    request(`/reasoning/chains/${id}/execute`, { method: 'POST', body: JSON.stringify(payload) }),
  getExecution: id => request(`/reasoning/executions/${id}`),
  getChainHistory: (id, days = 30) =>
    request(`/reasoning/chains/${id}/history?days=${days}`).catch(() => ({
      total_executions: 0,
      executions: [],
    })),
  listChainExecutions: (id, limit = 10) =>
    request(`/reasoning/chains/${id}/executions?limit=${limit}`).catch(() => []),

  // ============================================================================
  // Automation APIs
  // ============================================================================
  listAutomations: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).reduce((acc, [key, value]) => {
        if (value === undefined || value === null || value === '') {
          return acc;
        }
        acc[key] = value;
        return acc;
      }, {})
    ).toString();
    return request(`/automation/automations${query ? `?${query}` : ''}`);
  },
  getAutomation: id => request(`/automation/automations/${id}`),
  createAutomation: payload =>
    request('/automation/automations', { method: 'POST', body: JSON.stringify(payload) }),
  updateAutomation: (id, payload) =>
    request(`/automation/automations/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteAutomation: id => request(`/automation/automations/${id}`, { method: 'DELETE' }),
  executeAutomation: (id, context = null) =>
    request(`/automation/automations/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify(context),
    }),
  listAutomationExecutions: (id, params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).reduce((acc, [key, value]) => {
        if (value === undefined || value === null || value === '') {
          return acc;
        }
        acc[key] = value;
        return acc;
      }, {})
    ).toString();
    return request(`/automation/automations/${id}/executions${query ? `?${query}` : ''}`);
  },

  // ============================================================================
  // 智能分析 API (Intelligence APIs)
  // ============================================================================

  // 檔案識別與特徵提取
  identifyFile: async fileOrFileId => {
    if (typeof fileOrFileId === 'number') {
      // 使用數據庫中的檔案ID
      return request(`/intelligence/identify?file_id=${fileOrFileId}`, { method: 'POST' });
    } else {
      // 直接上傳檔案
      const formData = new FormData();
      formData.append('file', fileOrFileId);
      const token = getToken();
      const headers = {};
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      const response = await fetch(`${API_BASE}/intelligence/identify`, {
        method: 'POST',
        headers,
        body: formData,
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Request failed: ${response.status}`);
      }
      return response.json();
    }
  },

  // 檔名分析與標準化建議
  suggestNaming: filename => {
    const encodedFilename = encodeURIComponent(filename);
    return request(`/intelligence/naming/suggest?filename=${encodedFilename}`, { method: 'POST' });
  },

  // 標籤推薦
  recommendTags: (fileId, options = {}) => {
    const { topK = 10, ruleWeight = 0.6, collaborativeWeight = 0.4 } = options;
    const query = new URLSearchParams({
      file_id: fileId,
      top_k: topK,
      rule_weight: ruleWeight,
      collaborative_weight: collaborativeWeight,
    }).toString();
    return request(`/intelligence/tags/recommend?${query}`, { method: 'POST' });
  },

  // 結論生成
  generateConclusion: (fileId, language = 'zh') => {
    const query = new URLSearchParams({
      file_id: fileId,
      language,
    }).toString();
    return request(`/intelligence/conclusion/generate?${query}`, { method: 'POST' });
  },

  // 完整智能分析（一鍵執行所有功能）
  completeAnalysis: (fileId, options = {}) => {
    const { language = 'zh', topKTags = 10 } = options;
    const query = new URLSearchParams({
      file_id: fileId,
      language,
      top_k_tags: topKTags,
    }).toString();
    return request(`/intelligence/analyze/complete?${query}`, { method: 'POST' });
  },
};

export const auth = {
  setToken: token => localStorage.setItem('labflow_token', token),
  clearToken: () => localStorage.removeItem('labflow_token'),
  getToken,
  getOffline,
  setOffline,
};
