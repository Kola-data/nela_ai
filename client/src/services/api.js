import axios from 'axios';

const API_BASE_URL = 'http://localhost:8001/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 errors (unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/users/login', { email, password });
    return response.data;
  },
  register: async (userData) => {
    const response = await api.post('/users/', userData);
    return response.data;
  },
  getCurrentUser: async () => {
    const response = await api.get('/users/me');
    return response.data;
  },
};

// Document API
export const documentAPI = {
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/ai/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  getStatus: async (docId) => {
    const response = await api.get(`/ai/documents/${docId}/status`);
    return response.data;
  },
  delete: async (docId) => {
    const response = await api.delete(`/ai/documents/${docId}`);
    return response.data;
  },
  listFiles: async () => {
    const response = await api.get('/ai/files');
    return response.data;
  },
  getStorageInfo: async () => {
    const response = await api.get('/ai/storage/info');
    return response.data;
  },
};

// AI API
export const aiAPI = {
  query: async (prompt, userId = null) => {
    const response = await api.post('/ai/prompt', { prompt, user_id: userId });
    return response.data;
  },
  getConversationHistory: async (limit = 10) => {
    const response = await api.get(`/ai/conversation/history?limit=${limit}`);
    return response.data;
  },
  clearConversationHistory: async () => {
    const response = await api.delete('/ai/conversation/clear');
    return response.data;
  },
};

export default api;
