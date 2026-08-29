import { dom, $ } from './dom.js';
import {
  getRetestComparison,
  openLeadModal,
  scheduleRetest,
  trackEvent,
} from './engagement.js?v=20260729-platform2';

export function transformResponse(data) {
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

export function showReport(result) {
  dom.captureApp.classList.remove('active');
  dom.reportView.classList.add('active');
  window.scrollTo({ top: 0, behavior: 'auto' });

  const metricHtml = result.metrics.map(([name, value]) => `
    <div class="metric-card">
      <span>${name}</span>
      <strong>${value}<small>分</small></strong>
      <p>${metricStatus(value)}</p>
    </div>
  `).join('');
  const comparison = getRetestComparison(result);
  const solutionRows = buildSolutionReference(result);
  const comparisonHtml = comparison ? `
    <section class="retest-comparison">
      <h3>7 天复测对比</h3>
      <div class="retest-comparison-grid">
        <span>综合状态变化</span><strong>${formatChange(comparison.scoreChange)} 分</strong>
        ${comparison.metricChanges.map(([name, change]) => `
          <span>${name}</span><strong>${formatChange(change)} 分</strong>
        `).join('')}
      </div>
      <p class="retest-status">基线保存于 ${formatDate(comparison.baselineDate)}，本对比仅限当前设备。</p>
    </section>
  ` : '';

  $('reportContent').innerHTML = `
    <section class="report-hero">
      <p class="platform-kicker">SKIN ASSESSMENT REPORT</p>
      <h2>肌肤状态评估结果</h2>
      <div class="score-summary">
        <div class="score-number">${result.score}</div>
        <div><strong>综合状态参考</strong><span>皮肤年龄：${result.skinAge ?? '--'} 岁</span></div>
      </div>
      <p>${result.glogauLevel} ${result.glogauDesc}，结果依据本次图像生成。</p>
    </section>
    <section class="report-grid">${metricHtml}</section>
    <section class="report-text">${renderReportText(result.report)}</section>
    <section class="solution-reference">
      <p class="platform-kicker">PERSONALIZED ROUTE</p>
      <h2>个体化透皮方案建议</h2>
      <p>以下内容依据本次图像中的重点指标生成，用作后续产品匹配与专业沟通参考。</p>
      <div class="solution-reference-table">
        <div><b>关注方向</b><b>成分建议</b><b>剂型路线</b><b>建议周期</b></div>
        ${solutionRows.map((row) => `
          <div><span>${row.focus}</span><span>${row.ingredient}</span><span>${row.route}</span><span>${row.cycle}</span></div>
        `).join('')}
      </div>
      <small>成分浓度及适用性需结合肤质、既往使用情况和专业人员意见确认。</small>
    </section>
    <section class="report-next">
      <p class="platform-kicker">NEXT STEP</p>
      <h2>选择适合您的下一步</h2>
      <div class="report-action-grid">
        <button type="button" data-result-lead="product"><strong>产品匹配建议</strong><span>进一步了解适合的产品方向</span></button>
        <button type="button" data-result-lead="appointment"><strong>预约服务咨询</strong><span>由团队确认可提供的服务</span></button>
        <button type="button" data-result-lead="custom_consult"><strong>定制方案咨询</strong><span>围绕重点问题进一步沟通</span></button>
      </div>
      <button id="scheduleRetest" class="retest-button" type="button">设置 7 天后复测</button>
      <p id="retestStatus" class="retest-status" aria-live="polite"></p>
    </section>
    ${comparisonHtml}
    <section class="report-disclaimer">
      本报告用于肌肤状态与日常护理方向参考，不替代皮肤科医生的诊断和治疗意见。
    </section>
    <nav class="report-sticky-actions" aria-label="报告行动入口">
      <button type="button" data-result-lead="product">产品匹配</button>
      <button type="button" data-result-lead="appointment">预约服务</button>
      <button type="button" data-result-lead="custom_consult">定制咨询</button>
    </nav>
  `;

  document.querySelectorAll('[data-result-lead]').forEach((button) => {
    button.addEventListener('click', () => openLeadModal(button.dataset.resultLead));
  });
  $('scheduleRetest').addEventListener('click', () => {
    const dueAt = scheduleRetest(result);
    $('retestStatus').textContent = `已在本设备保存复测基线，建议于 ${formatDate(dueAt)} 后再次评估。`;
  });
  trackEvent('skin_report_generated', {
    score_band: Math.floor(result.score / 10) * 10,
  });
  if (comparison) {
    trackEvent('skin_retest_comparison_viewed', {
      score_direction: comparison.scoreChange > 0 ? 'up' : comparison.scoreChange < 0 ? 'down' : 'flat',
    });
  }
}

function metricStatus(value) {
  if (value >= 80) return '状态较稳定';
  if (value >= 60) return '建议持续关注';
  return '建议重点关注';
}

function formatDate(timestamp) {
  const date = new Date(timestamp);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}

function formatChange(value) {
  const rounded = Math.round(Number(value) || 0);
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

function buildSolutionReference(result) {
  const references = {
    皱纹分析: { ingredient: '维 A 类｜专业评估', route: '缓释路线', cycle: '8 至 12 周' },
    色斑检测: { ingredient: '烟酰胺｜2% 至 5%', route: '微乳路线', cycle: '8 至 12 周' },
    弹性评估: { ingredient: '多肽类｜配方评估', route: '脂质体路线', cycle: '8 至 12 周' },
    毛孔状况: { ingredient: '烟酰胺｜2% 至 5%', route: '微乳路线', cycle: '6 至 8 周' },
  };
  const sorted = [...result.metrics].sort((left, right) => left[1] - right[1]).slice(0, 2);
  const rows = sorted.map(([focus]) => ({ focus, ...references[focus] }));
  rows.push({
    focus: '屏障支持',
    ingredient: '神经酰胺｜1% 至 3%',
    route: '脂质体路线',
    cycle: '持续 8 周',
  });
  return rows;
}

function renderReportText(text) {
  if (!text) return '<p>暂无报告正文。</p>';
  return text.split('\n\n').filter(Boolean).map((block) => {
    const trimmed = block.trim();
    if (trimmed.startsWith('**【')) return `<h2>${escapeHtml(trimmed.replaceAll('*', ''))}</h2>`;
    return `<p>${escapeHtml(trimmed)}</p>`;
  }).join('');
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
