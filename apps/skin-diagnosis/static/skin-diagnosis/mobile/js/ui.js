import { dom } from './dom.js';

export function setStatus(message, isError = false) {
  dom.statusBox.textContent = message;
  dom.statusBox.className = message ? `status-box active${isError ? ' error-text' : ''}` : 'status-box';
}

export function setCaptureTip(message) {
  dom.centerTip.textContent = message;
}

export function setFooterHint(message, onClick = null) {
  dom.footerHint.textContent = message;
  dom.footerHint.onclick = onClick;
}

export function renderChecks(checks) {
  renderCheck(dom.lightState, checks.light);
  renderCheck(dom.facingState, checks.facing);
  renderCheck(dom.positionState, checks.position);
}

function renderCheck(element, status) {
  if (!element) return;
  element.classList.toggle('ok', status.ok);
  element.classList.toggle('bad', !status.ok);
  element.querySelector('strong').textContent = status.text;
}

export function showCaptureNotice() {
  dom.landing.style.display = 'none';
  dom.reportView.classList.remove('active');
  dom.captureApp.classList.add('active');
  dom.captureNotice.hidden = false;
  dom.captureScene.hidden = true;
  setStatus('');
  window.scrollTo({ top: 0, behavior: 'auto' });
}

export function showCaptureScene() {
  dom.captureNotice.hidden = true;
  dom.captureScene.hidden = false;
}

export function closeCapture() {
  dom.captureApp.classList.remove('active');
  dom.landing.style.display = '';
}

export function setCaptureProgress(progress) {
  dom.progressRing.style.setProperty('--capture-progress', `${progress}%`);
}
