(function () {
  'use strict';

  var API_BASE = '/lanjiao/api';
  var SESSION_KEY = 'ritan_platform_session';
  var leadModal = document.getElementById('leadModal');
  var leadForm = document.getElementById('leadForm');
  var leadStatus = document.getElementById('leadStatus');
  var leadTitle = document.getElementById('leadTitle');
  var leadIntro = document.getElementById('leadIntro');

  function getSessionId() {
    var existing = localStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    var generated = window.crypto && window.crypto.randomUUID
      ? window.crypto.randomUUID().replaceAll('-', '')
      : 'web_' + Date.now().toString(36) + Math.random().toString(36).slice(2);
    localStorage.setItem(SESSION_KEY, generated);
    return generated;
  }

  function track(eventName, metadata) {
    return fetch(API_BASE + '/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
      body: JSON.stringify({
        session_id: getSessionId(),
        event_name: eventName,
        source_page: 'skin_desktop',
        metadata: metadata || {},
      }),
    }).catch(function () {
      return null;
    });
  }

  function setupQrCodes() {
    var mobileUrl = location.origin + '/skin-diagnosis/mobile/';
    var qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=340x340&margin=18&data='
      + encodeURIComponent(mobileUrl);
    var pairs = [
      ['qrCode', 'qrSkeleton1'],
      ['qrCodeBottom', 'qrSkeleton2'],
    ];
    pairs.forEach(function (pair) {
      var image = document.getElementById(pair[0]);
      var skeleton = document.getElementById(pair[1]);
      if (!image) return;
      image.onload = image.onerror = function () {
        if (skeleton) skeleton.hidden = true;
      };
      image.src = qrUrl;
    });
    var mobileUrlElement = document.getElementById('mobileUrl');
    if (mobileUrlElement) mobileUrlElement.textContent = mobileUrl;
  }

  var leadCopy = {
    business_api: ['提交 API 接入需求', '请简要说明计划接入的终端、用户规模和使用场景。'],
    business_custom: ['提交联合定制需求', '请简要说明品牌、产品品类和希望共同解决的问题。'],
    business_technology: ['提交技术合作意向', '请简要说明研发方向、产品现状和希望讨论的合作方式。'],
    business_general: ['提交合作意向', '请留下真实联系方式和需求，团队预计在 48 小时内完成首次响应。'],
    product: ['获取产品匹配建议', '请留下联系方式，团队将结合本次评估结果进一步确认产品方向。'],
    appointment: ['预约医美透皮服务', '请留下联系方式和方便沟通的时间，由团队确认服务安排。'],
    custom_consult: ['定制化妆品咨询', '请说明重点关注的问题，团队将进一步沟通定制需求。'],
    privacy_request: ['提交数据权益申请', '请留下联系方式并说明希望查询、更正或删除的数据范围。'],
  };

  function openLeadModal(leadType) {
    var copy = leadCopy[leadType] || leadCopy.business_general;
    leadForm.reset();
    leadForm.elements.lead_type.value = leadType;
    leadTitle.textContent = copy[0];
    leadIntro.textContent = copy[1];
    leadStatus.textContent = '';
    leadModal.hidden = false;
    document.body.classList.add('modal-open');
    leadForm.elements.contact.focus();
    var consumerEvents = {
      product: 'skin_product_clicked',
      appointment: 'skin_appointment_clicked',
      custom_consult: 'skin_consult_clicked',
    };
    track(consumerEvents[leadType] || 'skin_business_clicked', { lead_type: leadType });
  }

  function closeLeadModal() {
    leadModal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  document.querySelectorAll('[data-lead-type]').forEach(function (button) {
    button.addEventListener('click', function () {
      openLeadModal(button.dataset.leadType);
    });
  });

  document.querySelectorAll('[data-track-event]').forEach(function (link) {
    link.addEventListener('click', function () {
      track(link.dataset.trackEvent, { href: link.getAttribute('href') || '' });
    });
  });

  document.querySelectorAll('[data-trust-topic]').forEach(function (detail) {
    detail.addEventListener('toggle', function () {
      if (detail.open) {
        track('skin_trust_expanded', { topic: detail.dataset.trustTopic || '' });
      }
    });
  });

  document.getElementById('leadClose').addEventListener('click', closeLeadModal);
  leadModal.addEventListener('click', function (event) {
    if (event.target === leadModal) closeLeadModal();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !leadModal.hidden) closeLeadModal();
  });

  leadForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    var submitButton = leadForm.querySelector('[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = '正在提交';
    leadStatus.textContent = '';

    var values = Object.fromEntries(new FormData(leadForm).entries());
    values.source_page = 'skin_desktop';
    try {
      var response = await fetch(API_BASE + '/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      var data = await response.json();
      if (!response.ok) throw new Error(data.detail || '提交失败，请稍后重试');
      leadStatus.textContent = '提交成功，我们已记录您的需求。';
      track('skin_lead_submitted', { lead_type: values.lead_type });
      window.setTimeout(closeLeadModal, 1400);
    } catch (error) {
      leadStatus.textContent = error.message || '提交失败，请稍后重试';
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = '确认提交';
    }
  });

  setupQrCodes();
  track('skin_page_enter', { path: location.pathname });
})();
