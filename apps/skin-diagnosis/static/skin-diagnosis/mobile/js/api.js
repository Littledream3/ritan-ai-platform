import { CONFIG, AUTH_BASE } from './config.js';
import { getToken, setToken } from './session.js';
import { getConsentContext } from './engagement.js?v=20260729-platform2';

export async function sendCode(email) {
  const response = await fetch(AUTH_BASE + '/send-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || '发送失败');
  return data;
}

export async function login(email, password) {
  const response = await fetch(AUTH_BASE + '/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || '登录失败');
  setToken(data.data.access_token);
  return data;
}

export async function register(email, code, password) {
  const response = await fetch(AUTH_BASE + '/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || '注册失败');
  setToken(data.data.access_token);
  return data;
}

export async function analyzeImage(blob) {
  const form = new FormData();
  form.append('image', new File([blob], 'photo.jpg', { type: 'image/jpeg' }));
  const consent = getConsentContext();
  form.append('consent_id', consent.consentId);
  form.append('session_id', consent.sessionId);
  form.append('research_consent', consent.researchUse ? 'true' : 'false');

  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = 'Bearer ' + token;

  const response = await fetch(CONFIG.apiUrl, { method: 'POST', body: form, headers });
  const data = await response.json();
  if (!response.ok || data.status !== 'ok') {
    throw new Error(data.message || `服务器错误：${response.status}`);
  }
  return data;
}
