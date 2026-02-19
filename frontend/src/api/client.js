const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

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
};

export const auth = {
  setToken: token => localStorage.setItem('labflow_token', token),
  clearToken: () => localStorage.removeItem('labflow_token'),
  getToken,
  getOffline,
  setOffline,
};
