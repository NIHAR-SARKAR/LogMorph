import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  login: (username: string, password: string, rememberMe = false) =>
    api.post('/auth/login', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }),
  register: (data: any) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  updateMe: (data: any) => api.put('/auth/me', data),
  refresh: (token: string) => api.post('/auth/refresh', { refresh_token: token }),
  listUsers: () => api.get('/auth/users'),
  resetPassword: (data: any) => api.post('/auth/reset-password', data),
  updateRole: (userId: number, role: string) => api.put(`/auth/users/${userId}/role`, null, { params: { role } }),
  disableUser: (userId: number) => api.put(`/auth/users/${userId}/disable`),
}

// Projects
export const projectApi = {
  list: () => api.get('/projects'),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: any) => api.post('/projects', data),
  update: (id: number, data: any) => api.put(`/projects/${id}`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
  environments: (projectId: number) => api.get(`/projects/${projectId}/environments`),
  createEnvironment: (projectId: number, data: any) => api.post(`/projects/${projectId}/environments`, data),
  deleteEnvironment: (projectId: number, envId: number) => api.delete(`/projects/${projectId}/environments/${envId}`),
  logSources: (projectId: number) => api.get(`/projects/${projectId}/log-sources`),
  createLogSource: (projectId: number, data: any) => api.post(`/projects/${projectId}/log-sources`, data),
  updateLogSource: (projectId: number, sourceId: number, data: any) => api.put(`/projects/${projectId}/log-sources/${sourceId}`, data),
  deleteLogSource: (projectId: number, sourceId: number) => api.delete(`/projects/${projectId}/log-sources/${sourceId}`),
}

// Logs
export const logApi = {
  listFiles: (params?: any) => api.get('/logs/files', { params }),
  scanSource: (sourceId: number) => api.post(`/logs/files/scan/${sourceId}`),
  parseFile: (fileId: number) => api.post(`/logs/files/${fileId}/parse`),
  search: (params: any) => api.get('/logs/entries', { params }),
  getEntry: (id: number) => api.get(`/logs/entries/${id}`),
  toggleBookmark: (id: number) => api.put(`/logs/entries/${id}/bookmark`),
  updateNotes: (id: number, notes: string) => api.put(`/logs/entries/${id}/notes`, null, { params: { notes } }),
  deleteEntry: (id: number) => api.delete(`/logs/entries/${id}`),
  stats: (params?: any) => api.get('/logs/stats', { params }),
  severityDistribution: (params?: any) => api.get('/logs/severity-distribution', { params }),
  topExceptions: (params?: any) => api.get('/logs/top-exceptions', { params }),
  facets: (params?: any) => api.get('/logs/facets', { params }),
  histogram: (params?: any) => api.get('/logs/histogram', { params }),
  rawFile: (fileId: number, params?: any) => api.get(`/logs/files/${fileId}/raw`, { params }),
}

// Dashboard
export const dashboardApi = {
  stats: (days?: number) => api.get('/dashboard/stats', { params: days !== undefined ? { days } : undefined }),
  logVolume: (params?: any) => api.get('/dashboard/log-volume', { params }),
  severityChart: (params?: any) => api.get('/dashboard/severity-chart', { params }),
}

// AI
export const aiApi = {
  providers: () => api.get('/ai/providers'),
  createProvider: (data: any) => api.post('/ai/providers', data),
  updateProvider: (id: number, data: any) => api.put(`/ai/providers/${id}`, data),
  deleteProvider: (id: number) => api.delete(`/ai/providers/${id}`),
  generate: (data: any) => api.post('/ai/generate', data),
  chat: (data: any) => api.post('/ai/chat', data),
  summarize: (entries: string[], providerId?: number) => api.post('/ai/summarize', entries, { params: { provider_id: providerId } }),
  analyzeException: (exceptionType: string, stackTrace: string, providerId?: number) =>
    api.post('/ai/analyze-exception', { exception_type: exceptionType, stack_trace: stackTrace, provider_id: providerId }),
  testConnection: (providerId: number) =>
    api.post('/ai/test-connection', null, { params: { provider_id: providerId } }),
}

// Parsers
export const parserApi = {
  list: (includeBuiltin = true) => api.get('/parsers/templates', { params: { include_builtin: includeBuiltin } }),
  get: (id: number) => api.get(`/parsers/templates/${id}`),
  create: (data: any) => api.post('/parsers/templates', data),
  update: (id: number, data: any) => api.put(`/parsers/templates/${id}`, data),
  delete: (id: number) => api.delete(`/parsers/templates/${id}`),
  test: (data: any) => api.post('/parsers/test', data),
}

// Alerts
export const alertApi = {
  listRules: (params?: any) => api.get('/alerts/rules', { params }),
  createRule: (data: any) => api.post('/alerts/rules', data),
  getRule: (id: number) => api.get(`/alerts/rules/${id}`),
  updateRule: (id: number, data: any) => api.put(`/alerts/rules/${id}`, data),
  deleteRule: (id: number) => api.delete(`/alerts/rules/${id}`),
  notifications: (params?: any) => api.get('/alerts/notifications', { params }),
  markRead: (id: number) => api.put(`/alerts/notifications/${id}/read`),
}

// Settings
export const settingsApi = {
  list: (category?: string) => api.get('/settings', { params: { category } }),
  get: (key: string) => api.get(`/settings/${key}`),
  create: (data: any) => api.post('/settings', data),
  update: (key: string, data: any) => api.put(`/settings/${key}`, data),
  delete: (key: string) => api.delete(`/settings/${key}`),
}

export default api
