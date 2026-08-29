(function () {
  'use strict';

  function escapeText(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function urgencyTone(urgency) {
    if (urgency === '立即急诊' || urgency === '紧急抢救') return 'critical';
    if (urgency === '紧急就诊') return 'high';
    if (urgency === '尽快就诊') return 'moderate';
    return 'routine';
  }

  function cleanReportHtml(html) {
    var container = document.createElement('div');
    container.innerHTML = html || '';

    ['.result-grade', '.result-confidence', '.result-borderline', '.urgency-tag'].forEach(function (selector) {
      var node = container.querySelector(selector);
      if (node) node.remove();
    });

    container.querySelectorAll('.section-title, .section-subtitle, .disclaimer').forEach(function (node) {
      node.textContent = node.textContent
        .replace(/[📋🩺🏠⚠️]/g, '')
        .replace(/AI 辅助评估/g, '智能辅助评估')
        .replace(/[—–]/g, '-')
        .trim();
    });

    return container.innerHTML;
  }

  function downloadAssessmentReport(recordId, button) {
    if (!recordId) {
      showToast('当前结果尚未保存，暂时无法下载报告');
      return;
    }
    var originalText = button.textContent;
    button.disabled = true;
    button.classList.add('is-loading');
    button.textContent = '正在准备报告...';

    fetch('api/reports/' + encodeURIComponent(recordId) + '/authorize-download', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { Authorization: 'Bearer ' + state.token }
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) throw new Error(data.detail || '报告准备失败，请稍后重试');
        return data;
      });
    }).then(function (data) {
      var link = document.createElement('a');
      link.href = data.download_url;
      link.download = '';
      link.setAttribute('aria-hidden', 'true');
      document.body.appendChild(link);
      link.click();
      link.remove();
      showToast('报告下载已开始，如浏览器打开报告可使用页面中的保存功能');
    }).catch(function (error) {
      showToast(error.message || '报告下载失败，请稍后重试');
    }).finally(function () {
      button.disabled = false;
      button.classList.remove('is-loading');
      button.textContent = originalText;
    });
  }

  function renderProfessionalReport(data) {
    var pred = data.prediction || {};
    var rec = data.recommendations || {};
    var grade = escapeText(pred.grade || '待确认');
    var urgency = escapeText(rec.urgency || '请咨询医生');
    var confidence = (Number(pred.confidence || 0) * 100).toFixed(1);
    var recordId = data.record_id || data.id || null;
    var ulcerProbability = pred.binary_probability_ulcer != null
      ? (Number(pred.binary_probability_ulcer) * 100).toFixed(1)
      : null;

    captureApp.classList.remove('active');
    reportView.classList.add('active');
    reportView.setAttribute('aria-label', '检测报告');
    reportContent.setAttribute('role', 'region');
    reportContent.setAttribute('aria-label', '检测结果');
    reportContent.setAttribute('aria-live', 'polite');
    window.scrollTo({ top: 0, behavior: 'auto' });

    var gradeHtml =
      '<section class="report-hero" aria-labelledby="reportResultTitle">' +
        '<div class="report-heading">' +
          '<p class="report-eyebrow">智能辅助评估结果</p>' +
          '<h2 id="reportResultTitle">Wagner 分级评估</h2>' +
          '<p>根据本次上传的创面影像生成</p>' +
        '</div>' +
        '<div class="clinical-summary-card">' +
          '<div class="grade-summary">' +
            '<span>本次评估分级</span>' +
            '<strong class="score-number">' + grade + '</strong>' +
          '</div>' +
          '<dl class="confidence-summary">' +
            '<div><dt>评估置信度</dt><dd>' + confidence + '%</dd></div>' +
            (ulcerProbability != null
              ? '<div><dt>溃疡筛查概率</dt><dd>' + ulcerProbability + '%</dd></div>'
              : '') +
          '</dl>' +
        '</div>' +
        (pred.is_borderline
          ? '<aside class="clinical-alert" role="note">' +
              '<strong>结果提示</strong>' +
              '<p>本次结果接近相邻分级，次选为 ' + escapeText(pred.secondary_grade || '') +
              '（' + (Number(pred.secondary_confidence || 0) * 100).toFixed(1) +
              '%）。建议由专业医生结合临床表现进一步确认。</p>' +
            '</aside>'
          : '') +
        '<div class="care-priority care-priority-' + urgencyTone(rec.urgency) + '">' +
          '<span>建议就医时效</span>' +
          '<strong>' + urgency + '</strong>' +
        '</div>' +
      '</section>';

    var probabilities = Array.isArray(pred.probabilities) ? pred.probabilities : [];
    var grades = probabilities.length === 7
      ? ['Normal', 'Grade 0', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5']
      : ['Grade 1', 'Grade 2', 'Grade 3', 'Grade 4'];
    var topProbabilities = probabilities.map(function (probability, index) {
      return { grade: grades[index], probability: Number(probability || 0) };
    }).sort(function (a, b) {
      return b.probability - a.probability;
    }).slice(0, 2);

    var probabilitiesHtml = '';
    if (topProbabilities.length) {
      probabilitiesHtml =
        '<section class="report-grid" aria-labelledby="distributionTitle">' +
          '<div class="report-section-heading">' +
            '<h3 id="distributionTitle">结果分布</h3>' +
            '<p>概率较高的两个分级</p>' +
          '</div>' +
          '<div class="probability-list">';

      topProbabilities.forEach(function (item, index) {
        probabilitiesHtml +=
          '<div class="probability-item">' +
            '<span class="probability-rank">' + (index + 1) + '</span>' +
            '<strong>' + escapeText(item.grade) + '</strong>' +
            '<span class="probability-value">' + (item.probability * 100).toFixed(1) + '%</span>' +
          '</div>';
      });

      probabilitiesHtml += '</div></section>';
    }

    var adviceHtml =
      '<section class="report-text" aria-labelledby="adviceTitle">' +
        '<div class="report-section-heading">' +
          '<h3 id="adviceTitle">健康建议</h3>' +
          '<p>请结合自身情况并遵循医生指导</p>' +
        '</div>' +
        '<div class="report-advice-body">' + cleanReportHtml(data.report_html) + '</div>' +
      '</section>';

    var numericGrade = pred.grade === 'Normal' ? -1 : Number(String(pred.grade || '').replace(/[^0-9]/g, ''));
    var careActions = '';
    if (numericGrade >= 3) {
      careActions = '<section class="dfu-result-path critical" role="alert"><strong>请立即由执业医师确认</strong><p>当前分级提示较高风险。本页不展示产品推荐或广告，请优先联系急诊或创面专科，勿因线上信息延误就医。</p></section>';
    } else if (numericGrade === 2) {
      careActions = '<section class="dfu-result-path warning"><strong>建议尽快就诊</strong><p>请尽快前往创面、内分泌或相关专科评估。</p><button type="button" onclick="showPartnerInstitutions()">查看合作机构接入状态</button></section>';
    } else {
      careActions = '<section class="dfu-result-path routine"><strong>护理与复拍计划</strong><p>保持创面清洁并遵循医生指导；如已授权随访，可查看 7/14 天站内复拍计划。</p><button type="button" onclick="loadHistory()">查看历史与复拍记录</button></section>';
    }
    var actionsHtml = careActions +
      '<section id="patientFollowupPanel" class="dfu-followup-panel" aria-live="polite"></section>' +
      '<div class="dfu-fixed-disclaimer">本结果仅为智能分级参考，不构成医学诊断或治疗建议。任何等级均应由执业医师确认。</div>' +
      '<div class="report-actions">' +
        '<button id="downloadAssessmentReport" class="report-download-btn" type="button"' + (recordId ? '' : ' disabled') + '>下载评估报告</button>' +
        '<button class="secondary-btn" type="button" onclick="restartDetection()">重新检测</button>' +
      '</div>';

    reportContent.innerHTML = gradeHtml + probabilitiesHtml + adviceHtml + actionsHtml;
    var downloadButton = document.getElementById('downloadAssessmentReport');
    if (downloadButton && recordId) {
      downloadButton.addEventListener('click', function () { downloadAssessmentReport(recordId, downloadButton); });
    }
    if (state && state.token) {
      fetch('api/patient/followups', {headers:{Authorization:'Bearer ' + state.token}})
        .then(function(r){return r.ok ? r.json() : null;}).then(function(data){
          var panel = document.getElementById('patientFollowupPanel');
          if (!panel || !data) return;
          var pending = (data.plans || []).filter(function(item){return item.status === 'pending';});
          var timeline = data.timeline || [];
          panel.innerHTML = '<h3>复拍与愈合趋势</h3>' +
            (pending.length ? '<p>' + pending.map(function(item){return item.interval_days + ' 天复拍：' + new Date(item.due_at).toLocaleDateString('zh-CN');}).join(' · ') + '</p>' : '<p>尚未生成复拍提醒，可在下一次检测前选择随访授权。</p>') +
            (timeline.length > 1 ? '<div class="dfu-timeline">' + timeline.map(function(item){return '<span><b>' + escapeText(item.grade) + '</b><small>' + new Date(item.created_at).toLocaleDateString('zh-CN') + '</small></span>';}).join('') + '</div>' : '');
        }).catch(function(){});
    }
  }

  window.showPartnerInstitutions = function(){
    fetch('api/public/partner-institutions').then(function(r){return r.json();}).then(function(data){
      if (!data.institutions || !data.institutions.length) return showToast('合作机构正在接入中，请先根据就医建议前往就近正规医疗机构');
      showToast(data.institutions.map(function(item){return item.name;}).join('、'));
    }).catch(function(){showToast('机构目录暂不可用，请前往就近正规医疗机构');});
  };

  window.showReport = renderProfessionalReport;
  showReport = renderProfessionalReport;
})();
