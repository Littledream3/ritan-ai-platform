import { $ } from './dom.js';
import { isLoggedIn } from './session.js';
import { createAuthModal } from './auth.js';
import { startCamera, stopCamera, initMediaPipe, isMediaPipeReady } from './camera.js?v=20260729-platform2';
import { closeCapture, showCaptureNotice } from './ui.js';
import { createConsentFlow, createLeadFlow, trackEvent } from './engagement.js?v=20260729-platform2';

// 页面加载后立即开始预加载人脸检测引擎，避免用户点击后等待
initMediaPipe();

const consentFlow = createConsentFlow(() => showCaptureNotice());
createLeadFlow();
const authModal = createAuthModal(() => consentFlow.open());
trackEvent('skin_page_enter', { path: location.pathname });

$('startCameraBtn').addEventListener('click', async () => {
  const loadingEl = $('noticeLoading');
  const btn = $('startCameraBtn');
  if (!isMediaPipeReady()) {
    loadingEl.hidden = false;
    btn.disabled = true;
    btn.textContent = '加载中…';
    await initMediaPipe();
    loadingEl.hidden = true;
    btn.disabled = false;
    btn.textContent = '立即体验';
  }
  trackEvent('skin_camera_started');
  startCamera();
});

document.querySelectorAll('[data-start]').forEach((button) => {
  button.addEventListener('click', () => {
    if (isLoggedIn()) consentFlow.open();
    else authModal.open();
  });
});

$('backLanding').addEventListener('click', () => {
  stopCamera();
  closeCapture();
});

$('closeCapture').addEventListener('click', () => {
  stopCamera();
  closeCapture();
});

$('restartBtn').addEventListener('click', () => {
  stopCamera();
  showCaptureNotice();
});

window.addEventListener('pagehide', () => stopCamera());
