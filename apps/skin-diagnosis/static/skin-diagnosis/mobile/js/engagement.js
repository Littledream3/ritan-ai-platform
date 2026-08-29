import { getToken } from './session.js';

const API_BASE = '/lanjiao/api';
const SESSION_KEY = 'ritan_platform_session';
let consentContext = {
  consentId: '',
  researchUse: false,
};

function getSessionId() {
  let existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  existing = window.crypto && window.crypto.randomUUID
    ? window.crypto.randomUUID().replaceAll('-', '')
    : `mobile_${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  localStorage.setItem(SESSION_KEY, existing);
  return existing;
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function getConsentContext() {
  return {
    consentId: consentContext.consentId,
    researchUse: consentContext.researchUse,
    sessionId: getSessionId(),
  };
}

export function trackEvent(eventName, metadata = {}) {
  return fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    keepalive: true,
    body: JSON.stringify({
      session_id: getSessionId(),
      event_name: eventName,
      source_page: 'skin_mobile',
      metadata,
    }),
  }).catch(() => null);
}

export function createConsentFlow(onConfirmed) {
  const modal = document.getElementById('consentModal');
  const form = document.getElementById('consentForm');
  const closeButton = document.getElementById('consentClose');
  const researchInput = document.getElementById('researchConsent');
  const serviceInput = document.getElementById('serviceConsent');
  const contactField = document.getElementById('consentContactField');
  const contactInput = document.getElementById('consentContact');
  const errorElement = document.getElementById('consentError');
  const submitButton = form.querySelector('[type="submit"]');

  function close() {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  function open() {
    errorElement.textContent = '';
    modal.hidden = false;
    document.body.classList.add('modal-open');
    submitButton.focus();
  }

  serviceInput.addEventListener('change', () => {
    contactField.hidden = !serviceInput.checked;
    contactInput.required = serviceInput.checked;
    if (serviceInput.checked) contactInput.focus();
  });

  closeButton.addEventListener('click', close);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) close();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorElement.textContent = '';
    submitButton.disabled = true;
    submitButton.textContent = '正在记录授权';

    try {
      const response = await fetch(`${API_BASE}/consents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          session_id: getSessionId(),
          source_page: 'skin_mobile',
          research_use: researchInput.checked,
          service_followup: serviceInput.checked,
          contact: serviceInput.checked ? contactInput.value.trim() : '',
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '授权记录失败，请稍后重试');
      consentContext = {
        consentId: data.consent_id,
        researchUse: researchInput.checked,
      };
      trackEvent('skin_consent_confirmed', {
        research_use: researchInput.checked,
        service_followup: serviceInput.checked,
      });
      close();
      onConfirmed();
    } catch (error) {
      errorElement.textContent = error.message || '授权记录失败，请稍后重试';
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = '确认并继续';
    }
  });

  return { open, close };
}

const leadCopy = {
  product: ['获取产品匹配建议', '请留下联系方式，团队将根据本次评估结果进一步了解您的需求。'],
  appointment: ['预约服务咨询', '请留下联系方式和方便沟通的时间，由团队确认可提供的服务。'],
  custom_consult: ['定制方案咨询', '请说明希望重点改善的问题，团队将进一步与您沟通。'],
};

let activeLeadFlow = null;

export function createLeadFlow() {
  const modal = document.getElementById('mobileLeadModal');
  const form = document.getElementById('mobileLeadForm');
  const closeButton = document.getElementById('mobileLeadClose');
  const title = document.getElementById('mobileLeadTitle');
  const intro = document.getElementById('mobileLeadIntro');
  const status = document.getElementById('mobileLeadStatus');
  const submitButton = form.querySelector('[type="submit"]');

  function close() {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  function open(leadType) {
    const copy = leadCopy[leadType] || leadCopy.custom_consult;
    form.reset();
    form.elements.lead_type.value = leadType;
    title.textContent = copy[0];
    intro.textContent = copy[1];
    status.textContent = '';
    modal.hidden = false;
    document.body.classList.add('modal-open');
    form.elements.contact.focus();
    const eventName = leadType === 'product'
      ? 'skin_product_clicked'
      : leadType === 'appointment'
        ? 'skin_appointment_clicked'
        : 'skin_consult_clicked';
    trackEvent(eventName);
  }

  closeButton.addEventListener('click', close);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) close();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.textContent = '';
    submitButton.disabled = true;
    submitButton.textContent = '正在提交';
    const values = Object.fromEntries(new FormData(form).entries());
    values.source_page = 'skin_mobile';

    try {
      const response = await fetch(`${API_BASE}/leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || '提交失败，请稍后重试');
      status.textContent = '提交成功，我们已记录您的需求。';
      trackEvent('skin_lead_submitted', { lead_type: values.lead_type });
      window.setTimeout(close, 1400);
    } catch (error) {
      status.textContent = error.message || '提交失败，请稍后重试';
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = '确认提交';
    }
  });

  activeLeadFlow = { open, close };
  return activeLeadFlow;
}

export function openLeadModal(leadType) {
  if (!activeLeadFlow) activeLeadFlow = createLeadFlow();
  activeLeadFlow.open(leadType);
}

export function scheduleRetest(result) {
  const now = Date.now();
  const payload = {
    createdAt: now,
    dueAt: now + 7 * 24 * 60 * 60 * 1000,
    score: result.score,
    skinAge: result.skinAge,
    metrics: result.metrics,
  };
  localStorage.setItem('ritan_skin_retest_baseline', JSON.stringify(payload));
  trackEvent('skin_retest_clicked');
  return payload.dueAt;
}

export function getRetestComparison(result) {
  try {
    const baseline = JSON.parse(localStorage.getItem('ritan_skin_retest_baseline') || 'null');
    if (!baseline || !Array.isArray(baseline.metrics)) return null;
    const previousMetrics = Object.fromEntries(baseline.metrics);
    const metricChanges = result.metrics.map(([name, value]) => [
      name,
      value - Number(previousMetrics[name] || 0),
    ]);
    return {
      baselineDate: baseline.createdAt,
      scoreChange: result.score - Number(baseline.score || 0),
      metricChanges,
    };
  } catch {
    return null;
  }
}
