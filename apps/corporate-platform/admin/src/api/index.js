import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

// 请求拦截器 — 自动附带 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 — 统一错误处理
api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/admin/login') {
          window.location.href = '/admin/login'
        }
      }
      ElMessage.error(data?.detail || error.message)
    }
    return Promise.reject(error)
  }
)

// ---- Auth ----

export function loginApi(data) {
  return api.post('/auth/login', data)
}

export function registerApi(data) {
  return api.post('/auth/register', data)
}

export function sendCodeApi(data) {
  return api.post('/auth/send-code', data)
}

export function getMe() {
  return api.get('/auth/me')
}

export function forgotPasswordApi(data) {
  return api.post('/auth/forgot-password', data)
}

export function resetPasswordApi(data) {
  return api.post('/auth/reset-password', data)
}

// ---- Chat ----

export function chatApi(data) {
  return api.post('/chat', data)
}

// ---- Images ----

export function getImageModels() {
  return api.get('/images/models')
}

export function generateImage(data) {
  return api.post('/images/generate', data)
}

// ---- Videos ----

export function getVideoModels() {
  return api.get('/videos/models')
}

export function generateVideo(data) {
  return api.post('/videos/generate', data)
}

// ---- Stats ----

export function getTodayStats() {
  return api.get('/stats/today')
}

export function getHistory(params) {
  return api.get('/stats/history', { params })
}

// ---- Admin ----

export function getAdminStats(days = 7) {
  return api.get('/admin/stats', { params: { days } })
}

export function getAdminLogs(params) {
  return api.get('/admin/logs', { params })
}

export function getAdminUsers(params) {
  return api.get('/admin/users', { params })
}

export function editUser(userId, data) {
  return api.put(`/admin/users/${userId}`, data)
}

export function getModels() {
  return api.get('/models')
}

// ---- Export ----

export function exportDocumentApi(data) {
  return api.post('/export', data, { responseType: 'blob' })
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('下载成功')
}

export default api
