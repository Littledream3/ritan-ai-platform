(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var timelineState = { sessions: [], selected: [], objectUrls: [], renderVersion: 0 };

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char];
    });
  }

  function errorMessage(detail) {
    if (Array.isArray(detail)) return detail.map(function (item) { return item.msg || '输入不符合要求'; }).join('；');
    if (detail && typeof detail === 'object') return detail.message || '查询失败';
    return detail || '查询失败';
  }

  function api(path) {
    var token = localStorage.getItem('dfu_collection_token') || '';
    return fetch(path, {headers: {Authorization: 'Bearer ' + token}}).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) throw new Error(errorMessage(data.detail));
        return data;
      });
    });
  }

  function fetchMedia(path) {
    var token = localStorage.getItem('dfu_collection_token') || '';
    return fetch(path, {headers: {Authorization: 'Bearer ' + token}}).then(function (response) {
      if (!response.ok) throw new Error('照片读取失败');
      return response.blob();
    });
  }

  function formatTime(value) {
    return value ? value.replace('T', ' ').slice(0, 19) : '—';
  }

  function gradeLabel(value) {
    return value === 'unknown' ? '历史记录：未知' : value + ' 级';
  }

  function clearObjectUrls() {
    timelineState.objectUrls.forEach(function (url) { URL.revokeObjectURL(url); });
    timelineState.objectUrls = [];
  }

  function renderTimeline(data) {
    var patient = data.patient || {};
    timelineState.sessions = data.sessions || [];
    timelineState.selected = [];
    clearObjectUrls();
    $('timelineComparison').hidden = true;
    $('timelineResult').hidden = false;
    $('timelinePatientSummary').innerHTML =
      '<div><span>患者编号</span><strong>' + escapeHtml(patient.patient_code || '—') + '</strong></div>' +
      '<div><span>患者姓名</span><strong>' + escapeHtml(patient.name || '未填写') + '</strong></div>' +
      '<div><span>手机号</span><strong>' + escapeHtml(patient.phone || '—') + '</strong></div>' +
      '<div><span>随访次数</span><strong>' + timelineState.sessions.length + '</strong></div>';

    if (!timelineState.sessions.length) {
      $('timelineList').innerHTML = '<p class="timeline-empty">该患者暂无当前医生的采集记录。</p>';
      updateSelection();
      return;
    }

    $('timelineList').innerHTML = timelineState.sessions.map(function (session, index) {
      var status = session.status === 'completed' ? '已归档' : '采集中';
      return '<article class="timeline-item" data-timeline-id="' + session.id + '">' +
        '<div class="timeline-marker"><span></span><small>' + (timelineState.sessions.length - index) + '</small></div>' +
        '<div class="timeline-item-body"><div class="timeline-item-heading"><div><time>' + escapeHtml(formatTime(session.created_at)) + '</time><h3>' + escapeHtml(session.admission_id) + '</h3></div><span class="timeline-grade">' + escapeHtml(gradeLabel(session.diabetes_grade)) + '</span></div>' +
        '<dl><div><dt>采集编号</dt><dd>' + escapeHtml(session.encounter_code) + '</dd></div><div><dt>状态</dt><dd>' + status + '</dd></div><div><dt>照片</dt><dd>' + session.photo_count + ' / 10</dd></div><div><dt>归档时间</dt><dd>' + escapeHtml(formatTime(session.completed_at)) + '</dd></div></dl>' +
        '<button class="secondary-button timeline-select" type="button" data-select-timeline="' + session.id + '">加入对比</button></div></article>';
    }).join('');

    document.querySelectorAll('[data-select-timeline]').forEach(function (button) {
      button.addEventListener('click', function () { toggleSelection(button.dataset.selectTimeline); });
    });
    updateSelection();
  }

  function toggleSelection(sessionId) {
    var index = timelineState.selected.indexOf(sessionId);
    if (index >= 0) timelineState.selected.splice(index, 1);
    else if (timelineState.selected.length < 2) timelineState.selected.push(sessionId);
    else {
      timelineState.selected.shift();
      timelineState.selected.push(sessionId);
    }
    updateSelection();
  }

  function updateSelection() {
    document.querySelectorAll('[data-select-timeline]').forEach(function (button) {
      var selected = timelineState.selected.indexOf(button.dataset.selectTimeline) >= 0;
      button.classList.toggle('selected', selected);
      button.textContent = selected ? '已选中' : '加入对比';
      var card = button.closest('.timeline-item');
      if (card) card.classList.toggle('selected', selected);
    });
    $('timelineSelectionText').textContent = '已选择 ' + timelineState.selected.length + ' / 2 个时间点';
    $('compareTimelineButton').disabled = timelineState.selected.length !== 2;
  }

  function renderComparison() {
    if (timelineState.selected.length !== 2) return;
    clearObjectUrls();
    timelineState.renderVersion += 1;
    var renderVersion = timelineState.renderVersion;
    var selectedSessions = timelineState.selected.map(function (id) {
      return timelineState.sessions.find(function (session) { return session.id === id; });
    }).filter(Boolean).sort(function (a, b) { return String(a.created_at).localeCompare(String(b.created_at)); });

    $('timelineComparisonGrid').innerHTML = selectedSessions.map(function (session) {
      var photos = (session.media || []).filter(function (item) { return item.kind === 'photo'; });
      var photoHtml = photos.length ? photos.map(function (item) {
        return '<figure class="comparison-photo"><div><span>加载中</span><img alt="' + escapeHtml(item.label) + '" data-timeline-media="' + escapeHtml(item.content_url) + '"></div><figcaption><strong>' + escapeHtml(item.label) + '</strong><small>' + escapeHtml(formatTime(item.captured_at)) + '</small></figcaption></figure>';
      }).join('') : '<p class="timeline-empty">该时间点暂无照片。</p>';
      return '<article class="comparison-column"><header><div><p class="eyebrow">' + escapeHtml(formatTime(session.created_at)) + '</p><h3>' + escapeHtml(session.admission_id) + '</h3><small>' + escapeHtml(session.encounter_code) + '</small></div><span class="timeline-grade">' + escapeHtml(gradeLabel(session.diabetes_grade)) + '</span></header><div class="comparison-media-grid">' + photoHtml + '</div></article>';
    }).join('');

    $('timelineComparison').hidden = false;
    $('timelineComparison').scrollIntoView({behavior: 'smooth', block: 'start'});
    document.querySelectorAll('[data-timeline-media]').forEach(function (image) {
      fetchMedia(image.dataset.timelineMedia).then(function (blob) {
        var objectUrl = URL.createObjectURL(blob);
        if (renderVersion !== timelineState.renderVersion) { URL.revokeObjectURL(objectUrl); return; }
        timelineState.objectUrls.push(objectUrl);
        image.src = objectUrl;
        image.classList.add('loaded');
        var loading = image.parentElement.querySelector('span');
        if (loading) loading.hidden = true;
      }).catch(function () {
        var loading = image.parentElement.querySelector('span');
        if (loading) loading.textContent = '读取失败';
      });
    });
  }

  $('timelineSearchForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var phone = this.elements.phone.value.trim().replace(/[\s-]/g, '');
    if (phone.indexOf('+86') === 0) phone = phone.slice(3);
    var button = this.querySelector('button[type="submit"]');
    $('timelineError').textContent = '';
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      $('timelineError').textContent = '请输入有效的11位患者手机号';
      this.elements.phone.focus();
      return;
    }
    button.disabled = true;
    button.querySelector('span').textContent = '正在查询…';
    api('api/patient-timeline?phone=' + encodeURIComponent(phone)).then(renderTimeline).catch(function (error) {
      $('timelineResult').hidden = true;
      $('timelineComparison').hidden = true;
      $('timelineError').textContent = error.message;
    }).finally(function () {
      button.disabled = false;
      button.querySelector('span').textContent = '查询随访记录';
    });
  });

  $('compareTimelineButton').addEventListener('click', renderComparison);
  window.addEventListener('beforeunload', clearObjectUrls);
})();
