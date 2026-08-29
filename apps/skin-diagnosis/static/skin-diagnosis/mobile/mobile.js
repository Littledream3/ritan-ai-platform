const API_URL = 'https://ritanai.com/lanjiao/api/analyze-single';
const AUTH_BASE = API_URL.replace('/analyze-single', '/email');
const MP_BASE = '/mediapipe';
const READY_SECONDS = 3;
const FRAME_WIDTH = 180;
const FRAME_HEIGHT = 240;

function getToken() {
  return localStorage.getItem('lanjiao_token');
}
function setToken(t) {
  localStorage.setItem('lanjiao_token', t);
}
function isLoggedIn() {
  return !!getToken();
}

const capState = {
  stream: null,
  detector: null,
  rafId: null,
  captured: false,
  analyzing: false,
  stableSince: 0,
  lastDetectAt: 0,
  checks: {
    light: { ok: false, text: '不佳' },
    facing: { ok: false, text: '不佳' },
    position: { ok: false, text: '不佳' },
  },
};

const $ = (id) => document.getElementById(id);
const landing = $('landing');
const captureApp = $('captureApp');
const reportView = $('reportView');
const video = $('video');
const canvas = $('canvas');
const statusBox = $('statusBox');
const captureNotice = $('captureNotice');
const captureScene = $('captureScene');
const startCameraBtn = $('startCameraBtn');
const centerTip = $('centerTip');
const footerHint = $('footerHint');
const progressRing = $('progressRing');
const lightState = $('lightState');
const facingState = $('facingState');
const positionState = $('positionState');

const authModal = {
  overlay: $('authModal'),
  loginForm: $('loginForm'),
  registerForm: $('registerForm'),
  loginError: $('loginError'),
  registerError: $('registerError'),
  sendCodeBtn: $('sendCodeBtn'),
  codeCooldown: 0,

  open() {
    this.overlay.classList.add('active');
    this.switchTab('login');
  },
  close() {
    this.overlay.classList.remove('active');
  },
  switchTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    this.loginForm.classList.toggle('active', tab === 'login');
    this.registerForm.classList.toggle('active', tab === 'register');
    this.loginError.textContent = '';
    this.registerError.textContent = '';
  },
  async sendCode() {
    const email = this.registerForm.email.value.trim();
    if (!email) {
      this.registerError.textContent = '请先输入邮箱';
      return;
    }
    this.sendCodeBtn.disabled = true;
    this.sendCodeBtn.textContent = '发送中...';
    try {
      const r = await fetch(AUTH_BASE + '/send-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || '发送失败');
      this.registerError.textContent = d.message || '验证码已发送，请查收邮件';
      this.registerError.style.color = '#30d158';
      this.codeCooldown = 60;
      this._tickCooldown();
    } catch (e) {
      this.registerError.textContent = e.message;
      this.registerError.style.color = '#a43a2f';
      this.sendCodeBtn.disabled = false;
      this.sendCodeBtn.textContent = '获取验证码';
    }
  },
  _tickCooldown() {
    if (this.codeCooldown <= 0) {
      this.sendCodeBtn.disabled = false;
      this.sendCodeBtn.textContent = '获取验证码';
      return;
    }
    this.sendCodeBtn.textContent = `${this.codeCooldown}s`;
    this.codeCooldown--;
    setTimeout(() => this._tickCooldown(), 1000);
  },
  async login(email, password) {
    const r = await fetch(AUTH_BASE + '/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || '登录失败');
    setToken(d.data.access_token);
    this.onAuthSuccess();
  },
  async register(email, code, password) {
    const r = await fetch(AUTH_BASE + '/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code, password }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || '注册失败');
    setToken(d.data.access_token);
    this.onAuthSuccess();
  },
  onAuthSuccess() {
    this.close();
    showCaptureNotice();
  },
};

$('authClose').addEventListener('click', () => authModal.close());
$('authSkip').addEventListener('click', () => {
  authModal.close();
  showCaptureNotice();
});
document.querySelectorAll('.auth-tab').forEach(tab => {
  tab.addEventListener('click', () => authModal.switchTab(tab.dataset.tab));
});
authModal.sendCodeBtn.addEventListener('click', () => authModal.sendCode());
authModal.loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  authModal.loginError.textContent = '';
  try {
    await authModal.login(authModal.loginForm.email.value.trim(), authModal.loginForm.password.value);
  } catch (err) {
    authModal.loginError.textContent = err.message;
  }
});
authModal.registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  authModal.registerError.textContent = '';
  authModal.registerError.style.color = '#a43a2f';
  try {
    await authModal.register(
      authModal.registerForm.email.value.trim(),
      authModal.registerForm.code.value.trim(),
      authModal.registerForm.password.value,
    );
  } catch (err) {
    authModal.registerError.textContent = err.message;
  }
});

document.querySelectorAll('[data-start]').forEach((btn) => {
  btn.addEventListener('click', () => {
    if (isLoggedIn()) showCaptureNotice();
    else authModal.open();
  });
});

$('backLanding').addEventListener('click', () => {
  stopCamera();
  captureApp.classList.remove('active');
  landing.style.display = '';
});
$('closeCapture').addEventListener('click', () => {
  stopCamera();
  captureApp.classList.remove('active');
  landing.style.display = '';
});
$('restartBtn').addEventListener('click', () => {
  stopCamera();
  capState.captured = false;
  capState.analyzing = false;
  reportView.classList.remove('active');
  showCaptureNotice();
});
startCameraBtn.addEventListener('click', () => startCamera());

function showCaptureNotice() {
  stopCamera();
  landing.style.display = 'none';
  reportView.classList.remove('active');
  captureApp.classList.add('active');
  captureNotice.hidden = false;
  captureScene.hidden = true;
  setStatus('');
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function resetCaptureState() {
  capState.captured = false;
  capState.analyzing = false;
  capState.stableSince = 0;
  capState.lastDetectAt = 0;
  capState.checks = {
    light: { ok: false, text: '不佳' },
    facing: { ok: false, text: '不佳' },
    position: { ok: false, text: '不佳' },
  };
  renderChecks();
  progressRing.style.setProperty('--capture-progress', '0%');
  centerTip.textContent = '请将面部置于框线范围内';
  footerHint.textContent = '三项均达到要求后，将保持 3 秒自动拍摄';
  footerHint.onclick = null;
  setStatus('');
}

async function loadFaceDetector() {
  if (capState.detector) return capState.detector;
  const vision = await import(`${MP_BASE}/vision_bundle.mjs`);
  const fileset = await vision.FilesetResolver.forVisionTasks(`${MP_BASE}/wasm`);
  try {
    capState.detector = await vision.FaceDetector.createFromOptions(fileset, {
      baseOptions: {
        modelAssetPath: `${MP_BASE}/models/blaze_face_short_range.tflite`,
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      minDetectionConfidence: 0.55,
    });
  } catch (err) {
    capState.detector = await vision.FaceDetector.createFromOptions(fileset, {
      baseOptions: {
        modelAssetPath: `${MP_BASE}/models/blaze_face_short_range.tflite`,
        delegate: 'CPU',
      },
      runningMode: 'VIDEO',
      minDetectionConfidence: 0.55,
    });
  }
  return capState.detector;
}

async function startCamera() {
  resetCaptureState();
  captureNotice.hidden = true;
  captureScene.hidden = false;
  centerTip.textContent = '正在准备检测';
  footerHint.textContent = '正在加载本地人脸检测模型';

  if (!navigator.mediaDevices?.getUserMedia) {
    centerTip.textContent = '无法打开相机';
    setStatus('当前浏览器不支持摄像头采集，请使用 HTTPS 环境和支持相机的浏览器。', true);
    return;
  }

  try {
    await loadFaceDetector();
    capState.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 1600 } },
      audio: false,
    });
    video.srcObject = capState.stream;
    await video.play();
    centerTip.textContent = '请将面部置于框线范围内';
    footerHint.textContent = '三项均达到要求后，将保持 3 秒自动拍摄';
    capState.rafId = requestAnimationFrame(analyzeFrame);
  } catch (err) {
    centerTip.textContent = '无法打开相机';
    footerHint.textContent = '请允许相机权限后重新进入检测';
    setStatus(err.message || '无法打开摄像头，请检查浏览器权限。', true);
  }
}

function stopCamera() {
  if (capState.rafId) cancelAnimationFrame(capState.rafId);
  capState.rafId = null;
  if (capState.stream) {
    capState.stream.getTracks().forEach(track => track.stop());
    capState.stream = null;
  }
  if (video) video.srcObject = null;
}

async function analyzeFrame(now) {
  if (capState.captured || capState.analyzing) return;
  if (video.readyState < 2 || video.videoWidth === 0) {
    capState.rafId = requestAnimationFrame(analyzeFrame);
    return;
  }
  if (now - capState.lastDetectAt < 180) {
    capState.rafId = requestAnimationFrame(analyzeFrame);
    return;
  }
  capState.lastDetectAt = now;

  canvas.width = FRAME_WIDTH;
  canvas.height = FRAME_HEIGHT;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const light = evaluateLight(getFrameStats(ctx, canvas.width, canvas.height));
  let detections = [];
  try {
    detections = capState.detector.detectForVideo(video, now).detections || [];
  } catch (err) {
    setStatus('人脸检测失败，请刷新页面重试。', true);
  }
  const face = evaluateFace(detections[0]);
  capState.checks = { light, facing: face.facing, position: face.position };
  renderChecks();

  const allOk = Object.values(capState.checks).every(item => item.ok);
  if (allOk) {
    if (!capState.stableSince) capState.stableSince = now;
    const elapsed = now - capState.stableSince;
    const progress = Math.min(100, (elapsed / (READY_SECONDS * 1000)) * 100);
    progressRing.style.setProperty('--capture-progress', `${progress}%`);
    const remaining = Math.max(0, Math.ceil(READY_SECONDS - elapsed / 1000));
    centerTip.textContent = remaining > 0 ? `请保持稳定 ${remaining} 秒` : '正在自动拍摄';
    footerHint.textContent = '检测条件良好，请保持当前姿势';
    if (elapsed >= READY_SECONDS * 1000) {
      await captureAndSubmit();
      return;
    }
  } else {
    capState.stableSince = 0;
    progressRing.style.setProperty('--capture-progress', '0%');
    updateGuidance(detections[0], light, face);
  }

  capState.rafId = requestAnimationFrame(analyzeFrame);
}

function getFrameStats(ctx, width, height) {
  const image = ctx.getImageData(0, 0, width, height);
  const data = image.data;
  let total = 0;
  let dark = 0;
  let bright = 0;
  for (let i = 0; i < data.length; i += 4) {
    const v = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    total += v;
    if (v < 45) dark++;
    if (v > 235) bright++;
  }
  const pixels = data.length / 4;
  return { average: total / pixels, darkRatio: dark / pixels, brightRatio: bright / pixels };
}

function evaluateLight(stats) {
  if (stats.average < 65 || stats.darkRatio > 0.48) return { ok: false, text: '不佳' };
  if (stats.average > 215 || stats.brightRatio > 0.14) return { ok: false, text: '不佳' };
  return { ok: true, text: '良好' };
}

function evaluateFace(detection) {
  if (!detection?.boundingBox || !video.videoWidth || !video.videoHeight) {
    return {
      facing: { ok: false, text: '不佳' },
      position: { ok: false, text: '不佳' },
    };
  }
  const box = detection.boundingBox;
  const ox = box.originX ?? box.origin_x ?? 0;
  const oy = box.originY ?? box.origin_y ?? 0;
  const cx = (ox + box.width / 2) / video.videoWidth;
  const cy = (oy + box.height / 2) / video.videoHeight;
  const widthRatio = box.width / video.videoWidth;
  const heightRatio = box.height / video.videoHeight;
  const centered = Math.hypot(cx - 0.5, cy - 0.48) < 0.18;
  const sizeOk = widthRatio >= 0.28 && widthRatio <= 0.68 && heightRatio >= 0.32 && heightRatio <= 0.78;
  const aspect = box.width / box.height;
  const facingOk = aspect >= 0.45 && aspect <= 1.25;
  return {
    facing: { ok: facingOk, text: facingOk ? '良好' : '不佳' },
    position: { ok: centered && sizeOk, text: centered && sizeOk ? '良好' : '不佳' },
  };
}

function updateGuidance(detection, light, face) {
  if (!detection) {
    centerTip.textContent = '请将面部置于框线范围内';
    footerHint.textContent = '保持正脸，头发和眼镜不要遮挡面部';
  } else if (!light.ok) {
    centerTip.textContent = '请调整灯光';
    footerHint.textContent = '避免过暗、背光或强反光环境';
  } else if (!face.facing.ok) {
    centerTip.textContent = '请面向前方';
    footerHint.textContent = '眼睛张开向前看，头部保持水平';
  } else {
    centerTip.textContent = '请将面部置于框线范围内';
    footerHint.textContent = '让脸部居中，距离手机不要过近或过远';
  }
}

function renderChecks() {
  renderCheck(lightState, capState.checks.light);
  renderCheck(facingState, capState.checks.facing);
  renderCheck(positionState, capState.checks.position);
}

function renderCheck(element, status) {
  if (!element) return;
  element.classList.toggle('ok', status.ok);
  element.classList.toggle('bad', !status.ok);
  element.querySelector('strong').textContent = status.text;
}

async function captureAndSubmit() {
  if (capState.captured) return;
  capState.captured = true;
  capState.analyzing = true;
  if (capState.rafId) cancelAnimationFrame(capState.rafId);
  centerTip.textContent = '正在分析肌肤状态';
  footerHint.textContent = 'AI 正在分析，通常需要 20-60 秒';

  const output = document.createElement('canvas');
  output.width = video.videoWidth;
  output.height = video.videoHeight;
  output.getContext('2d').drawImage(video, 0, 0, output.width, output.height);
  const blob = await new Promise(resolve => output.toBlob(resolve, 'image/jpeg', 0.92));
  if (!blob) {
    capState.captured = false;
    capState.analyzing = false;
    setStatus('拍摄失败，请重新检测。', true);
    return;
  }

  const form = new FormData();
  form.append('image', new File([blob], 'photo.jpg', { type: 'image/jpeg' }));
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = 'Bearer ' + token;
  setStatus('AI 正在分析您的肌肤状态，请保持页面打开。');

  try {
    const response = await fetch(API_URL, { method: 'POST', body: form, headers });
    const data = await response.json();
    if (!response.ok || data.status !== 'ok') throw new Error(data.message || `服务器错误：${response.status}`);
    stopCamera();
    showReport(transformResponse(data));
  } catch (err) {
    capState.captured = false;
    capState.analyzing = false;
    setStatus(err.message || '分析失败，请稍后重试。', true);
    centerTip.textContent = '分析失败';
    footerHint.textContent = '点击下方提示区域重新检测';
    footerHint.onclick = () => startCamera();
  }
}

function transformResponse(data) {
  const s = data.skin_scores || {};
  const toScore = (val) => Math.max(0, Math.min(100, Math.round((1 - val / 5) * 100)));
  const avg = (...keys) => keys.reduce((sum, key) => sum + (s[key] || 0), 0) / keys.length;
  const score = toScore(avg('眼周细纹', '额头皱纹', '皮肤弹性', '色斑', '肤色不均', '雀斑', '泛红程度', '毛孔粗大', '黑眼圈'));
  const glogau = score >= 80 ? ['Ⅰ级', '轻度光老化']
    : score >= 60 ? ['Ⅱ级', '中度光老化']
    : score >= 40 ? ['Ⅲ级', '重度光老化']
    : ['Ⅳ级', '严重光老化'];
  return {
    score,
    skinAge: data.age,
    glogauLevel: glogau[0],
    glogauDesc: glogau[1],
    report: data.report || '',
    metrics: [
      ['皱纹分析', toScore(avg('眼周细纹', '额头皱纹'))],
      ['色斑检测', toScore(avg('色斑', '雀斑', '肤色不均'))],
      ['弹性评估', toScore(s['皮肤弹性'] || 0)],
      ['毛孔状况', toScore(s['毛孔粗大'] || 0)],
    ],
  };
}

function showReport(result) {
  captureApp.classList.remove('active');
  reportView.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'auto' });
  const metricHtml = result.metrics.map(([name, value]) => `
    <div class="metric-card">
      <strong><span>${name}</span><span>${value}分</span></strong>
      <div class="bar"><i style="width:${value}%"></i></div>
    </div>
  `).join('');
  $('reportContent').innerHTML = `
    <section class="report-hero">
      <p class="brand-kicker">AOJIAO SKIN DIAGNOSIS</p>
      <h2>个人化智能皮肤分析结果</h2>
      <div class="score-number">${result.score}</div>
      <p>皮肤年龄：${result.skinAge ?? '--'} 岁 · ${result.glogauLevel} ${result.glogauDesc}</p>
    </section>
    <section class="report-grid">${metricHtml}</section>
    <section class="report-text">${renderReportText(result.report)}</section>
  `;
}

function renderReportText(text) {
  if (!text) return '<p>暂无报告正文。</p>';
  return text.split('\n\n').filter(Boolean).map(block => {
    const trimmed = block.trim();
    if (trimmed.startsWith('**【')) return `<h2>${escapeHtml(trimmed.replaceAll('*', ''))}</h2>`;
    return `<p>${escapeHtml(trimmed)}</p>`;
  }).join('');
}

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.className = message ? `status-box active${isError ? ' error-text' : ''}` : 'status-box';
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
