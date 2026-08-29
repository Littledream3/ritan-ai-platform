(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var state = {
    token: localStorage.getItem('dfu_doctor_token') || '',
    doctor: null,
    flowMode: 'existing',
    admissionId: '',
    lookupPhone: '',
    patient: null,
    matchedEncounter: null,
    encounter: null,
    dietaryOptions: [],
    trend: [],
    analysis: null,
    reportRecordId: null,
    archive: null,
    stream: null,
    captureIndex: 0,
    captureFiles: {},
    captureUrls: {},
    videoFiles: {},
    uploadedVideos: [],
    pendingFile: null,
    pendingUrl: ''
  };

  var captureSteps = [
    {key:'left_view', short:'左侧', title:'左侧视角', overlay:'guide-side', instruction:'从足部左侧平行拍摄，确保足跟、足弓和前足完整进入画面。', guide:'<svg viewBox="0 0 120 90"><path d="M10 62C24 55 35 43 46 28c8-10 18-12 28-7 7 4 11 13 17 19 6 7 14 9 19 15 4 5 2 13-5 15-22 6-66 7-91 1-6-1-8-6-4-9Z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="5 4"/></svg>'},
    {key:'right_view', short:'右侧', title:'右侧视角', overlay:'guide-side', instruction:'移动至足部右侧平行拍摄，保持与上一张相近的距离和高度。', guide:'<svg viewBox="0 0 120 90"><g transform="translate(120 0) scale(-1 1)"><path d="M10 62C24 55 35 43 46 28c8-10 18-12 28-7 7 4 11 13 17 19 6 7 14 9 19 15 4 5 2 13-5 15-22 6-66 7-91 1-6-1-8-6-4-9Z" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="5 4"/></g></svg>'},
    {key:'plantar_view', short:'足底', title:'足底视角', overlay:'guide-sole', instruction:'镜头正对足底，完整拍到脚趾、前足、足弓与足跟。', guide:'<svg viewBox="0 0 90 120"><ellipse cx="45" cy="69" rx="24" ry="39" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="5 4"/><circle cx="23" cy="24" r="7" fill="none" stroke="currentColor"/><circle cx="36" cy="18" r="8" fill="none" stroke="currentColor"/><circle cx="51" cy="17" r="8" fill="none" stroke="currentColor"/><circle cx="65" cy="21" r="7" fill="none" stroke="currentColor"/><circle cx="76" cy="29" r="6" fill="none" stroke="currentColor"/></svg>'},
    {key:'wound_closeup_1', short:'创口1', title:'最严重创口特写 1', overlay:'guide-wound', instruction:'正对最严重创口拍摄，建议创口占画面 70% 以上。', guide:'<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="38" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="5 4"/><path d="M32 50c6-14 14-20 25-13 12 8 15 23 2 29-12 5-33-1-27-16Z" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>'}, // gitleaks:allow -- UI field identifier, not a credential
    {key:'wound_closeup_2', short:'创口2', title:'最严重创口特写 2', overlay:'guide-wound', instruction:'拍摄第二严重创口；如仅一处明显创口，请从另一角度补拍。', guide:'<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="38" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="5 4"/><path d="M32 50c6-14 14-20 25-13 12 8 15 23 2 29-12 5-33-1-27-16Z" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>'} // gitleaks:allow -- UI field identifier, not a credential
  ];

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char];
    });
  }

  function toast(message) {
    var el = $('doctorToast');
    el.textContent = message;
    el.classList.add('active');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { el.classList.remove('active'); }, 2600);
  }

  function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    if (state.token) headers.Authorization = 'Bearer ' + state.token;
    options.headers = headers;
    var controller = new AbortController();
    options.signal = controller.signal;
    var timer = setTimeout(function () { controller.abort(); }, options.timeoutMs || 30000);
    return fetch(path, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var detail = data.detail;
          var message = typeof detail === 'object' ? (detail.message || '操作失败') : (detail || '操作失败');
          var error = new Error(message);
          error.status = response.status;
          error.detail = detail;
          throw error;
        }
        return data;
      });
    }).catch(function (error) {
      if (error.name === 'AbortError') throw new Error('请求超时，请检查网络后重试');
      throw error;
    }).finally(function () { clearTimeout(timer); });
  }

  function logout(showMessage) {
    stopCamera();
    state.token = '';
    state.doctor = null;
    localStorage.removeItem('dfu_doctor_token');
    $('doctorApp').hidden = true;
    $('doctorAuth').style.display = '';
    if (showMessage) toast('已退出登录');
  }

  document.querySelectorAll('[data-doctor-tab]').forEach(function (button) {
    button.addEventListener('click', function () {
      var tab = button.dataset.doctorTab;
      document.querySelectorAll('[data-doctor-tab]').forEach(function (item) { item.classList.toggle('active', item.dataset.doctorTab === tab); });
      $('doctorLoginForm').classList.toggle('active', tab === 'login');
      $('doctorRegisterForm').classList.toggle('active', tab === 'register');
      $('doctorLoginError').textContent = '';
      $('doctorRegisterError').textContent = '';
    });
  });

  $('doctorLoginForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var form = this;
    $('doctorLoginError').textContent = '';
    api('api/doctor/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:form.elements.username.value.trim(), password:form.elements.password.value})})
      .then(function (data) { state.token = data.data.access_token; localStorage.setItem('dfu_doctor_token', state.token); return enterApp(); })
      .catch(function (error) { $('doctorLoginError').textContent = error.message; });
  });

  $('doctorRegisterForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var form = this;
    $('doctorRegisterError').textContent = '';
    var payload = new FormData(form);
    api('api/doctor/register', {method:'POST', body:payload})
      .then(function (data) { $('doctorRegisterError').textContent = data.message; form.reset(); })
      .catch(function (error) { $('doctorRegisterError').textContent = error.message; });
  });

  function enterApp() {
    return api('api/doctor/me').then(function (data) {
      state.doctor = data.data;
      var name = state.doctor.real_name || state.doctor.username || '医生';
      var institution = [state.doctor.institution, state.doctor.department].filter(Boolean).join(' · ') || 'DFU 医生端';
      $('doctorName').textContent = name;
      $('doctorInstitution').textContent = institution;
      $('doctorAvatar').textContent = name.charAt(0).toUpperCase();
      $('profileAvatar').textContent = name.charAt(0).toUpperCase();
      $('profileDoctorName').textContent = name;
      $('profileUsername').textContent = state.doctor.username || '—';
      $('profileInstitution').textContent = state.doctor.institution || '未填写';
      $('profileDepartment').textContent = state.doctor.department || '未填写';
      $('profileLicense').textContent = state.doctor.license_number || '未填写';
      $('profileVerification').textContent = state.doctor.verification_status === 'approved' ? '已审核' : (state.doctor.verification_status || '待审核');
      $('doctorAuth').style.display = 'none';
      $('doctorApp').hidden = false;
      showView('dashboard');
      return loadDietaryOptions();
    }).catch(function (error) {
      if (error.status === 401) logout(false);
      else throw error;
    });
  }

  $('doctorLogout').addEventListener('click', function () { logout(true); });
  $('mobileMenuBtn').addEventListener('click', function () { document.querySelector('.doctor-sidebar').classList.toggle('open'); });
  $('todayText').textContent = new Intl.DateTimeFormat('zh-CN', {year:'numeric', month:'long', day:'numeric', weekday:'short'}).format(new Date());

  function showView(name) {
    document.querySelectorAll('.doctor-view').forEach(function (view) { view.classList.remove('active'); });
    var map = {dashboard:'dashboardView', capture:'captureView', profile:'profileView'};
    $(map[name]).classList.add('active');
    document.querySelectorAll('[data-view]').forEach(function (button) { button.classList.toggle('active', button.dataset.view === name); });
    $('viewTitle').textContent = name === 'dashboard' ? '医生工作台' : name === 'profile' ? '我的信息' : '患者登记';
    document.querySelector('.doctor-sidebar').classList.remove('open');
    if (name === 'dashboard') loadDashboard();
  }

  document.querySelectorAll('[data-view]').forEach(function (button) { button.addEventListener('click', function () { showView(button.dataset.view); }); });
  document.querySelectorAll('[data-view-dashboard]').forEach(function (button) { button.addEventListener('click', function () { showView('dashboard'); }); });
  document.querySelectorAll('[data-start-flow]').forEach(function (button) { button.addEventListener('click', function () { startFlow(button.dataset.startFlow); }); });

  function loadDashboard() {
    api('api/doctor/dashboard').then(function (data) {
      $('sumPatients').textContent = data.summary.patients;
      $('sumRecords').textContent = data.summary.records;
      $('sumToday').textContent = data.summary.today_records;
      $('sumRisk').textContent = data.summary.high_risk;
      renderEncounterRows(data.recent_encounters || []);
      renderGrade(data.grade_distribution || []);
      renderTrend(data.trend || []);
    }).catch(function (error) { toast(error.message); });
  }

  $('refreshDashboard').addEventListener('click', loadDashboard);
  $('workbenchSearch').addEventListener('submit', function (event) {
    event.preventDefault();
    var query = this.elements.query.value.trim();
    var status = this.elements.status.value;
    api('api/doctor/workbench?query=' + encodeURIComponent(query) + '&status=' + encodeURIComponent(status))
      .then(function (data) { renderEncounterRows(data.items || []); })
      .catch(function (error) { toast(error.message); });
  });

  function renderEncounterRows(rows) {
    if (!rows.length) {
      $('encounterRows').innerHTML = '<tr><td colspan="7" class="table-empty">暂无符合条件的记录</td></tr>';
      return;
    }
    var sexLabel = {male:'男', female:'女', other:'其他'};
    $('encounterRows').innerHTML = rows.map(function (row) {
      var patient = row.patient || {};
      var status = row.status === 'submitted' ? '已归档' : row.status === 'draft' ? '草稿' : '已撤回';
      var info = [patient.phone || '', row.age == null ? '' : row.age + '岁', sexLabel[row.sex] || '', row.diabetes_grade == null ? '' : '糖尿病' + (row.diabetes_grade === 'unknown' ? '未知' : row.diabetes_grade + '级')].filter(Boolean).join(' · ') || '待补充';
      return '<tr><td><strong class="mono-code">' + escapeHtml(patient.patient_code || '历史记录') + '</strong></td><td>' + escapeHtml(row.admission_id || '待补录') + '</td><td>' + escapeHtml(info) + '</td><td><span class="status-chip ' + row.status + '">' + status + '</span></td><td>' + row.record_count + ' 次检测</td><td>' + escapeHtml(row.updated_at) + '</td><td><button type="button" class="table-action" data-open-encounter="' + row.id + '">查看</button></td></tr>';
    }).join('');
    document.querySelectorAll('[data-open-encounter]').forEach(function (button) { button.addEventListener('click', function () { openEncounter(Number(button.dataset.openEncounter)); }); });
  }

  function renderGrade(rows) {
    if (!rows.length) { $('gradeChart').className = 'bar-chart empty-chart'; $('gradeChart').textContent = '暂无数据'; return; }
    var maximum = Math.max.apply(null, rows.map(function (row) { return row.count; })) || 1;
    $('gradeChart').className = 'bar-chart';
    $('gradeChart').innerHTML = rows.map(function (row) { return '<div class="bar-item"><strong>' + escapeHtml(row.grade) + '</strong><div class="bar-column"><i style="height:' + Math.max(8, row.count / maximum * 150) + 'px"></i></div><span>' + row.count + '</span></div>'; }).join('');
  }

  function renderTrend(rows) {
    state.trend = rows || [];
    rows = state.trend;
    var canvas = $('trendCanvas');
    var width = canvas.clientWidth || 500;
    var ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio; canvas.height = 220 * ratio;
    var ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); ctx.clearRect(0, 0, width, 220);
    if (!rows.length) { ctx.fillStyle = '#8b9096'; ctx.font = '14px sans-serif'; ctx.fillText('暂无数据', 18, 35); return; }
    var maximum = Math.max.apply(null, rows.map(function (row) { return row.count; })) || 1;
    var padding = 26, usable = width - padding * 2;
    ctx.beginPath();
    rows.forEach(function (row, index) { var x = padding + usable * index / Math.max(1, rows.length - 1); var y = 180 - row.count / maximum * 130; if (index) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
    ctx.strokeStyle = '#b38b4d'; ctx.lineWidth = 3; ctx.stroke();
  }

  function loadDietaryOptions() {
    if (state.dietaryOptions.length) return Promise.resolve();
    return api('api/doctor/dietary-options').then(function (data) { state.dietaryOptions = data.options || []; renderDietaryOptions([]); });
  }

  function renderDietaryOptions(selected) {
    selected = selected || [];
    $('doctorDietaryOptions').innerHTML = state.dietaryOptions.map(function (option) {
      return '<label><input type="checkbox" name="dietary_habits" value="' + escapeHtml(option.code) + '"' + (selected.indexOf(option.code) >= 0 ? ' checked' : '') + '><span>' + escapeHtml(option.label) + '</span></label>';
    }).join('');
  }

  function startFlow(mode) {
    resetWorkflow();
    state.flowMode = 'existing';
    $('newPatientIdentityForm').hidden = true;
    $('existingPatientLookupForm').hidden = false;
    $('identityHeading').textContent = '患者登记';
    $('identityNote').textContent = '输入患者手机号进行精确查询，再登记本次住院ID。';
    showView('capture');
    setStep(1);
  }

  function resetWorkflow() {
    stopCamera(); clearPending(true);
    Object.keys(state.captureUrls).forEach(function (key) { URL.revokeObjectURL(state.captureUrls[key]); });
    state.admissionId = ''; state.lookupPhone = ''; state.patient = null; state.matchedEncounter = null; state.encounter = null; state.analysis = null; state.reportRecordId = null; state.archive = null;
    state.captureIndex = 0; state.captureFiles = {}; state.captureUrls = {}; state.videoFiles = {}; state.uploadedVideos = [];
    $('newPatientIdentityForm').reset(); $('existingPatientLookupForm').reset(); $('doctorPatientProfileForm').reset();
    $('lookupPatientResult').hidden = true; $('newPatientDecision').hidden = true; $('newAdmissionField').hidden = true; $('existingIdentityNext').disabled = true;
    ['newIdentityError','lookupError','doctorProfileError','doctorCaptureError','archiveError'].forEach(function (id) { $(id).textContent = ''; });
    $('patientConsent').checked = false; $('archiveComplete').hidden = true; $('archiveCompleteActions').hidden = true; $('archiveActions').hidden = false; $('missingRequired').hidden = true;
    $('fullFootVideoInput').value = ''; $('woundVideoInput').value = ''; $('fullFootVideoName').textContent = '选择视频'; $('woundVideoName').textContent = '选择视频';
    renderDietaryOptions([]); renderCapture();
  }

  function setStep(step) {
    var screens = {1:'doctorStepIdentity', 2:'doctorStepProfile', 3:'doctorStepCapture', 4:'doctorStepReport'};
    document.querySelectorAll('.workflow-step').forEach(function (item) { item.classList.toggle('active', Number(item.dataset.step) === step); });
    document.querySelectorAll('.workflow-screen').forEach(function (screen) { screen.classList.remove('active'); });
    $(screens[step]).classList.add('active');
    if (step !== 3) stopCamera();
  }

  document.querySelectorAll('.workflow-step').forEach(function (button) {
    button.addEventListener('click', function () {
      var step = Number(button.dataset.step);
      if (step === 1 || (step === 2 && (state.admissionId || state.encounter)) || (step === 3 && state.encounter) || (step === 4 && (state.analysis || state.archive))) setStep(step);
    });
  });

  $('newPatientIdentityForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var value = this.elements.admission_id.value.trim().toUpperCase();
    if (!value) { $('newIdentityError').textContent = '请输入本次住院ID'; return; }
    state.admissionId = value;
    $('newIdentityError').textContent = '';
    fillProfileForm(); setStep(2);
  });

  $('existingPatientLookupForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var query = this.elements.query.value.trim();
    if (!query) { $('lookupError').textContent = '请输入患者手机号'; return; }
    if (!/^1[3-9]\d{9}$/.test(query)) { $('lookupError').textContent = '请输入有效的11位手机号'; return; }
    $('lookupError').textContent = '';
    state.lookupPhone = '';
    $('lookupPatientResult').hidden = true;
    $('newPatientDecision').hidden = true;
    $('newPatientIdentityForm').hidden = true;
    $('newAdmissionField').hidden = true;
    $('existingIdentityNext').disabled = true;
    api('api/doctor/patients/lookup', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:query})})
      .then(function (data) {
        if (!data.found) {
          state.lookupPhone = query;
          $('lookupPatientResult').innerHTML = '<strong>新患者</strong><span>手机号：' + escapeHtml(query) + '</span><small>系统中暂无对应档案，请确认后建立新档案。</small>';
          $('lookupPatientResult').hidden = false;
          $('newPatientDecision').hidden = false;
          return;
        }
        state.lookupPhone = ''; $('newPatientDecision').hidden = true;
        state.patient = data.patient; state.matchedEncounter = data.matched_encounter || null;
        var matchedText = '<small>手机号：' + escapeHtml(state.patient.phone) + ' · 已找到患者，请输入本次住院ID。</small>';
        $('lookupPatientResult').innerHTML = '<strong>' + escapeHtml(state.patient.patient_code) + '</strong><span>' + escapeHtml(state.patient.name || '姓名选填') + '</span>' + matchedText;
        $('lookupPatientResult').hidden = false; $('newAdmissionField').hidden = false; $('existingIdentityNext').disabled = false;
      }).catch(function (error) { $('lookupError').textContent = error.message; });
  });

  $('confirmCreateNewPatient').addEventListener('click', function () {
    if (!state.lookupPhone) { $('lookupError').textContent = '请重新输入患者手机号并查询'; return; }
    state.flowMode = 'new'; state.patient = null; state.matchedEncounter = null;
    $('existingPatientLookupForm').hidden = true;
    $('newPatientIdentityForm').hidden = false;
    $('identityHeading').textContent = '建立新患者档案';
    $('identityNote').textContent = '手机号已确认未建档，请登记本次住院ID，再完善患者临床信息。';
    $('newIdentityError').textContent = '';
    $('newPatientIdentityForm').elements.admission_id.focus();
  });

  $('backToPatientLookup').addEventListener('click', function () {
    state.flowMode = 'existing'; state.admissionId = '';
    $('newPatientIdentityForm').reset();
    $('newPatientIdentityForm').hidden = true;
    $('existingPatientLookupForm').hidden = false;
    $('identityHeading').textContent = '患者登记';
    $('identityNote').textContent = '输入患者手机号进行精确查询，再登记本次住院ID。';
    $('newIdentityError').textContent = '';
    $('existingPatientLookupForm').elements.query.focus();
  });

  $('existingIdentityNext').addEventListener('click', function () {
    var admission = $('existingPatientLookupForm').elements.admission_id.value.trim().toUpperCase();
    if (!admission && state.matchedEncounter) { openEncounter(state.matchedEncounter.id); return; }
    if (!admission) { $('lookupError').textContent = '请输入本次住院ID'; return; }
    state.admissionId = admission; state.encounter = null;
    fillProfileForm(); setStep(2);
  });

  function fillProfileForm() {
    var form = $('doctorPatientProfileForm'); form.reset();
    var source = state.encounter || {};
    var patient = state.patient || {};
    form.elements.name.value = source.name || patient.name || '';
    form.elements.phone.value = source.phone || patient.phone || state.lookupPhone || '';
    form.elements.age.value = source.age == null ? '' : source.age;
    form.elements.diabetes_grade.value = source.diabetes_grade || '';
    form.elements.residence.value = source.residence || patient.residence || '';
    var sexValue = source.sex || patient.sex;
    if (sexValue) { var radio = form.querySelector('input[name="sex"][value="' + sexValue + '"]'); if (radio) radio.checked = true; }
    renderDietaryOptions(source.dietary_habits || patient.dietary_habits || []);
    renderDraftIdentity();
  }

  function draftPayload() {
    var form = $('doctorPatientProfileForm');
    var checkedSex = form.querySelector('input[name="sex"]:checked');
    var age = form.elements.age.value.trim();
    return {
      admission_id: state.encounter ? state.encounter.admission_id : state.admissionId,
      name: form.elements.name.value.trim() || null,
      phone: form.elements.phone.value.trim() || null,
      age: age === '' ? null : Number(age),
      sex: checkedSex ? checkedSex.value : null,
      diabetes_grade: form.elements.diabetes_grade.value || null,
      residence: form.elements.residence.value.trim() || null,
      dietary_habits: Array.prototype.map.call(form.querySelectorAll('input[name="dietary_habits"]:checked'), function (input) { return input.value; })
    };
  }

  $('doctorPatientProfileForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var payload = draftPayload();
    $('doctorProfileError').textContent = '';
    if (payload.phone && !/^1[3-9]\d{9}$/.test(payload.phone)) {
      $('doctorProfileError').textContent = '请输入有效的11位手机号';
      return;
    }
    var path, method;
    if (state.encounter) { path = 'api/doctor/encounters/' + state.encounter.id; method = 'PUT'; }
    else if (state.patient) { path = 'api/doctor/patients/' + state.patient.id + '/encounters'; method = 'POST'; }
    else { path = 'api/doctor/patients'; method = 'POST'; }
    api(path, {method:method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
      .then(function (data) {
        state.patient = data.patient; state.encounter = data.encounter; state.admissionId = state.encounter.admission_id; state.lookupPhone = '';
        if (state.encounter.status === 'submitted' || state.encounter.record_count > 0) { openEncounter(state.encounter.id); return; }
        renderDraftIdentity(); resetCapture(); setStep(3); toast('草稿已保存');
      }).catch(function (error) { $('doctorProfileError').textContent = error.message; });
  });

  $('backToIdentity').addEventListener('click', function () { setStep(1); });
  $('backToProfile').addEventListener('click', function () { fillProfileForm(); setStep(2); });

  function renderDraftIdentity() {
    var patientCode = state.patient ? state.patient.patient_code : '将在保存草稿时自动生成';
    var admissionId = state.encounter ? state.encounter.admission_id : state.admissionId;
    var phone = state.encounter ? state.encounter.phone : (state.patient ? state.patient.phone : $('doctorPatientProfileForm').elements.phone.value.trim());
    var html = '<strong>患者编号：' + escapeHtml(patientCode) + '</strong><span>手机号：' + escapeHtml(phone || '待填写') + ' · 住院ID：' + escapeHtml(admissionId || '待填写') + '</span>';
    $('draftIdentity').innerHTML = html;
    $('selectedPatient').innerHTML = html;
    $('archiveIdentity').innerHTML = html;
  }

  function stopCamera() {
    if (state.stream) state.stream.getTracks().forEach(function (track) { track.stop(); });
    state.stream = null; $('doctorVideo').srcObject = null; $('doctorVideo').classList.remove('visible'); $('takeDoctorPhoto').hidden = true;
  }

  function clearPending(revoke) {
    if (revoke && state.pendingUrl) URL.revokeObjectURL(state.pendingUrl);
    state.pendingFile = null; state.pendingUrl = '';
    $('doctorPreview').classList.remove('visible'); $('doctorPreview').src = ''; $('doctorCameraPlaceholder').style.display = 'grid'; $('confirmDoctorPhoto').disabled = true; $('doctorFileInput').value = '';
  }

  function resetCapture() {
    stopCamera(); clearPending(true);
    Object.keys(state.captureUrls).forEach(function (key) { URL.revokeObjectURL(state.captureUrls[key]); });
    state.captureIndex = 0; state.captureFiles = {}; state.captureUrls = {}; state.videoFiles = {}; state.uploadedVideos = []; state.analysis = null; state.reportRecordId = null; state.archive = null;
    $('patientConsent').checked = false; $('doctorCaptureArea').hidden = false; $('doctorCloseupPrompt').hidden = true; $('doctorCaptureError').textContent = '';
    $('fullFootVideoInput').value = ''; $('woundVideoInput').value = ''; $('fullFootVideoName').textContent = '选择视频'; $('woundVideoName').textContent = '选择视频';
    renderCapture();
  }

  function renderCapture() {
    var current = captureSteps[state.captureIndex];
    var phase = state.captureIndex < 3 ? (state.captureIndex + 1) + '/3' : (state.captureIndex - 2) + '/2';
    $('doctorCapturePhase').textContent = (state.captureIndex < 3 ? '足部全景 · ' : '创口特写 · ') + phase;
    $('doctorCaptureTitle').textContent = current.title; $('doctorCaptureInstruction').textContent = current.instruction; $('doctorCaptureGuide').innerHTML = current.guide;
    $('doctorCameraOverlay').className = 'doctor-camera-overlay ' + current.overlay; $('doctorPlaceholderTitle').textContent = '准备拍摄' + current.title;
    $('doctorCaptureSlots').innerHTML = captureSteps.map(function (step, index) { var complete = !!state.captureFiles[step.key]; return '<button type="button" class="doctor-capture-slot' + (complete ? ' complete' : '') + (index === state.captureIndex ? ' active' : '') + '" data-capture-index="' + index + '"><strong>' + (complete ? '✓' : index + 1) + '</strong>' + step.short + '</button>'; }).join('');
    document.querySelectorAll('[data-capture-index]').forEach(function (button) { button.addEventListener('click', function () { stopCamera(); clearPending(true); state.captureIndex = Number(button.dataset.captureIndex); $('doctorCloseupPrompt').hidden = true; $('doctorCaptureArea').hidden = false; renderCapture(); }); });
    var completed = Object.keys(state.captureFiles).length;
    $('doctorSubmitAnalysis').disabled = completed !== captureSteps.length;
    $('doctorSubmitAnalysis').textContent = completed === captureSteps.length ? '分析五张照片' : '完成 ' + completed + '/5';
  }

  $('openDoctorCamera').addEventListener('click', function () {
    clearPending(true);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { $('doctorCaptureError').textContent = '当前浏览器不支持摄像头，请从相册选择图片'; return; }
    navigator.mediaDevices.getUserMedia({video:{facingMode:'environment', width:{ideal:1280}, height:{ideal:1280}}, audio:false})
      .then(function (stream) { stopCamera(); state.stream = stream; $('doctorVideo').srcObject = stream; $('doctorVideo').classList.add('visible'); $('doctorCameraPlaceholder').style.display = 'none'; $('takeDoctorPhoto').hidden = false; $('doctorCaptureError').textContent = ''; })
      .catch(function () { $('doctorCaptureError').textContent = '无法打开摄像头，请检查浏览器权限，或从相册选择图片'; });
  });

  $('takeDoctorPhoto').addEventListener('click', function () {
    var video = $('doctorVideo'), canvas = $('doctorCanvas'), step = captureSteps[state.captureIndex];
    canvas.width = video.videoWidth || 640; canvas.height = video.videoHeight || 640; canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(function (blob) { setPending(new File([blob], step.key + '.jpg', {type:'image/jpeg'})); }, 'image/jpeg', 0.92);
  });

  $('chooseDoctorFile').addEventListener('click', function () { $('doctorFileInput').click(); });
  $('doctorFileInput').addEventListener('change', function () { if (this.files[0]) setPending(this.files[0]); });

  function setPending(file) {
    stopCamera(); clearPending(true); state.pendingFile = file; state.pendingUrl = URL.createObjectURL(file);
    $('doctorPreview').src = state.pendingUrl; $('doctorPreview').classList.add('visible'); $('doctorCameraPlaceholder').style.display = 'none'; $('confirmDoctorPhoto').disabled = false; $('doctorCaptureError').textContent = '';
  }

  $('confirmDoctorPhoto').addEventListener('click', function () {
    if (!state.pendingFile) { $('doctorCaptureError').textContent = '请先拍摄或选择当前视角照片'; return; }
    var step = captureSteps[state.captureIndex];
    if (state.captureUrls[step.key]) URL.revokeObjectURL(state.captureUrls[step.key]);
    state.captureFiles[step.key] = state.pendingFile; state.captureUrls[step.key] = state.pendingUrl; state.pendingFile = null; state.pendingUrl = ''; clearPending(false);
    var next = -1;
    for (var index = state.captureIndex + 1; index < captureSteps.length; index += 1) if (!state.captureFiles[captureSteps[index].key]) { next = index; break; }
    if (next < 0) for (var start = 0; start < captureSteps.length; start += 1) if (!state.captureFiles[captureSteps[start].key]) { next = start; break; }
    if (state.captureIndex === 2 && next === 3) { state.captureIndex = 3; $('doctorCaptureArea').hidden = true; $('doctorCloseupPrompt').hidden = false; renderCapture(); return; }
    if (next >= 0) state.captureIndex = next;
    renderCapture();
  });

  $('startDoctorCloseup').addEventListener('click', function () { $('doctorCloseupPrompt').hidden = true; $('doctorCaptureArea').hidden = false; renderCapture(); });

  function selectOptionalVideo(role, input, nameElement) {
    var file = input.files[0];
    if (!file) { delete state.videoFiles[role]; nameElement.textContent = '选择视频'; return; }
    state.videoFiles[role] = file;
    nameElement.textContent = file.name + ' · 待上传';
  }

  $('fullFootVideoInput').addEventListener('change', function () { selectOptionalVideo('full_foot_video', this, $('fullFootVideoName')); });
  $('woundVideoInput').addEventListener('change', function () { selectOptionalVideo('wound_video', this, $('woundVideoName')); });

  function uploadOptionalVideos() {
    var roles = Object.keys(state.videoFiles);
    var uploaded = [], failed = [];
    return roles.reduce(function (promise, role) {
      return promise.then(function () {
        var form = new FormData(); form.append('video', state.videoFiles[role], state.videoFiles[role].name);
        return api('api/doctor/encounters/' + state.encounter.id + '/videos/' + role, {method:'POST', body:form, timeoutMs:180000})
          .then(function (data) { uploaded.push(data.video); })
          .catch(function (error) { failed.push((role === 'full_foot_video' ? '全足环绕视频' : '创口局部视频') + '：' + error.message); });
      });
    }, Promise.resolve()).then(function () { state.uploadedVideos = uploaded; return failed; });
  }

  $('doctorSubmitAnalysis').addEventListener('click', function () {
    if (!state.encounter) { $('doctorCaptureError').textContent = '请先保存患者草稿'; return; }
    if (!$('patientConsent').checked) { $('doctorCaptureError').textContent = '请确认已获得患者同意'; return; }
    var missing = captureSteps.filter(function (step) { return !state.captureFiles[step.key]; });
    if (missing.length) { $('doctorCaptureError').textContent = '还缺少：' + missing.map(function (step) { return step.title; }).join('、'); return; }
    var button = this; button.disabled = true; button.textContent = '五张影像分析中…';
    var form = new FormData(); captureSteps.forEach(function (step) { var file = state.captureFiles[step.key]; form.append(step.key, file, file.name || step.key + '.jpg'); }); form.append('consent_confirmed', 'true');
    api('api/doctor/encounters/' + state.encounter.id + '/predict-multi', {method:'POST', body:form, timeoutMs:180000})
      .then(function (data) {
        if (data.status === 'rejected') { var failed = captureSteps.findIndex(function (step) { return step.key === data.failed_role; }); if (failed < 0) failed = 3; var failedStep = captureSteps[failed]; if (state.captureUrls[failedStep.key]) URL.revokeObjectURL(state.captureUrls[failedStep.key]); delete state.captureUrls[failedStep.key]; delete state.captureFiles[failedStep.key]; state.captureIndex = failed; renderCapture(); throw new Error(data.reason || '图片未通过检查，请重新拍摄'); }
        if (data.status !== 'ok') throw new Error(data.message || '分析失败');
        state.analysis = data; state.encounter = data.encounter || state.encounter; renderReport(data);
        return uploadOptionalVideos().then(function (videoErrors) {
          showReportStep(); setStep(4);
          if (videoErrors.length) $('archiveError').textContent = '以下选填视频未保存，不影响归档：' + videoErrors.join('；');
        });
      }).catch(function (error) { $('doctorCaptureError').textContent = error.message; renderCapture(); });
  });

  function downloadDoctorReport(button) {
    if (!state.reportRecordId) { toast('当前评估记录尚未保存'); return; }
    var originalText = button.textContent;
    button.disabled = true;
    button.classList.add('is-loading');
    button.textContent = '正在准备报告...';
    fetch('api/reports/' + encodeURIComponent(state.reportRecordId) + '/authorize-download', {
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
      toast('报告下载已开始，如浏览器打开报告可使用页面中的保存功能');
    }).catch(function (error) {
      toast(error.message || '报告下载失败，请稍后重试');
    }).finally(function () {
      button.disabled = false; button.classList.remove('is-loading'); button.textContent = originalText;
    });
  }

  function renderReport(data) {
    var prediction = data.prediction || data;
    state.reportRecordId = data.record_id || data.id || null;
    var grade = prediction.grade || '待确认'; var confidence = Number(prediction.confidence || 0) * 100;
    var report = data.report_html || prediction.report_html || '';
    var binaryMeta = prediction.binary_probability_ulcer != null ? ' · 溃疡筛查 ' + (Number(prediction.binary_probability_ulcer) * 100).toFixed(1) + '%' : '';
    var gradeIndex = grade === 'Normal' ? -1 : Number(String(grade).replace(/[^0-9]/g, ''));
    var referral = gradeIndex >= 3 ? '<section class="doctor-referral-panel"><h3>高风险转诊建议</h3><p>请结合临床表现确认；如需转诊，请留下真实目标机构与原因。</p><div><input id="referralInstitution" maxlength="160" placeholder="目标机构"><input id="referralReason" maxlength="500" placeholder="转诊原因"><button id="createReferral" type="button">记录转诊建议</button></div><small id="referralStatus"></small></section>' : '';
    $('doctorReportContent').innerHTML = '<div class="report-hero"><span>智能辅助 Wagner 分级结果</span><strong>' + escapeHtml(grade) + '</strong><p>置信度 ' + confidence.toFixed(1) + '%' + binaryMeta + (prediction.is_borderline ? ' · 边界结果' : '') + '</p></div><div class="doctor-report-body">' + report + '</div>' + referral + '<section id="doctorCareTimeline" class="doctor-care-timeline"></section><section class="doctor-report-download-panel"><div><span>辅助评估报告</span><strong>保存本次评估的 PDF 报告</strong><small>包含患者信息、评估结果、建议与报告声明</small></div><button id="doctorDownloadReport" class="doctor-report-download" type="button"' + (state.reportRecordId ? '' : ' disabled') + '>下载评估报告（PDF）</button></section>';
    var button = $('doctorDownloadReport');
    if (button && state.reportRecordId) button.addEventListener('click', function () { downloadDoctorReport(button); });
    if (state.patient && state.patient.id) {
      api('api/doctor/patients/' + state.patient.id + '/care-timeline').then(function(data){
        var panel = $('doctorCareTimeline'); if (!panel) return;
        panel.innerHTML = '<h3>随访与愈合趋势</h3>' + ((data.timeline || []).length ? '<div>' + data.timeline.map(function(item){return '<span><b>' + escapeHtml(item.grade) + '</b><small>' + new Date(item.created_at).toLocaleDateString('zh-CN') + '</small></span>';}).join('') + '</div>' : '<p>暂无历史复拍记录</p>');
      }).catch(function(){});
    }
    var referralButton = $('createReferral');
    if (referralButton) referralButton.addEventListener('click', function(){
      var institution = $('referralInstitution').value.trim(), reason = $('referralReason').value.trim();
      if (!institution || !reason) { $('referralStatus').textContent = '请填写目标机构和转诊原因'; return; }
      api('api/doctor/referrals', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({patient_id:state.patient.id,analysis_record_id:state.reportRecordId,target_institution:institution,reason:reason})})
        .then(function(){ $('referralStatus').textContent = '转诊建议已记录'; }).catch(function(error){ $('referralStatus').textContent = error.message; });
    });
  }

  function requiredMissing() {
    var encounter = state.encounter || {};
    var missing = [];
    if (!encounter.admission_id) missing.push('住院ID');
    if (!encounter.phone) missing.push('手机号');
    if (encounter.age == null) missing.push('年龄');
    if (!encounter.sex) missing.push('性别');
    if (encounter.diabetes_grade == null) missing.push('糖尿病等级');
    if (!state.analysis && !(state.archive && state.archive.photo_count)) missing.push('五张足部照片及分析结果');
    return missing;
  }

  function showReportStep() {
    renderDraftIdentity();
    var missing = requiredMissing();
    $('missingRequired').hidden = !missing.length;
    $('missingRequired').innerHTML = missing.length ? '<strong>提交前还需补充</strong><p>' + missing.map(escapeHtml).join('、') + '</p>' : '';
    $('archiveError').textContent = '';
    if (state.encounter && state.encounter.status === 'submitted' && state.archive) showArchiveComplete(state.archive);
    else { $('reportHeading').textContent = '核对并完成归档'; $('archiveActions').hidden = false; $('archiveComplete').hidden = true; $('archiveCompleteActions').hidden = true; }
  }

  $('editClinicalInfo').addEventListener('click', function () { fillProfileForm(); setStep(2); });
  $('finalSubmit').addEventListener('click', function () {
    var missing = requiredMissing();
    if (missing.length) { $('archiveError').textContent = '请先补充：' + missing.join('、'); return; }
    if (!window.confirm('确认提交本次患者资料并完成归档吗？归档后将不能直接修改。')) return;
    var button = this; button.disabled = true; button.textContent = '正在归档…';
    api('api/doctor/encounters/' + state.encounter.id + '/submit', {method:'POST'})
      .then(function (data) { state.archive = data.archive; state.encounter.status = 'submitted'; state.encounter.submitted_at = data.archive.submitted_at; showArchiveComplete(data.archive); toast('患者资料已完成归档'); loadDashboard(); })
      .catch(function (error) { var missingFields = error.detail && error.detail.missing_fields; $('archiveError').textContent = missingFields ? '请先补充：' + missingFields.join('、') : error.message; })
      .finally(function () { button.disabled = false; button.textContent = '提交并完成归档'; });
  });

  function showArchiveComplete(archive) {
    state.archive = archive; $('reportHeading').textContent = '完成归档'; $('archiveActions').hidden = true; $('missingRequired').hidden = true;
    var doctor = archive.doctor || state.doctor || {};
    $('archiveComplete').innerHTML = '<div class="archive-success-mark">✓</div><div><strong>本次资料已正式归档</strong><dl><div><dt>患者编号</dt><dd>' + escapeHtml(archive.patient_code) + '</dd></div><div><dt>手机号</dt><dd>' + escapeHtml(archive.phone) + '</dd></div><div><dt>住院ID</dt><dd>' + escapeHtml(archive.admission_id) + '</dd></div><div><dt>采集记录编号</dt><dd>' + escapeHtml(archive.encounter_code) + '</dd></div><div><dt>提交医生</dt><dd>' + escapeHtml(doctor.real_name || doctor.username) + '</dd></div><div><dt>机构与科室</dt><dd>' + escapeHtml([doctor.institution, doctor.department].filter(Boolean).join(' · ') || '未填写') + '</dd></div><div><dt>归档时间</dt><dd>' + escapeHtml(archive.submitted_at) + '</dd></div><div><dt>媒体资料</dt><dd>' + archive.photo_count + ' 张图片 · ' + archive.video_count + ' 个视频</dd></div></dl></div>';
    $('archiveComplete').hidden = false; $('archiveCompleteActions').hidden = false;
  }

  function openEncounter(encounterId) {
    api('api/doctor/encounters/' + encounterId).then(function (data) {
      resetWorkflow(); state.flowMode = 'existing'; state.encounter = data.encounter; state.patient = data.encounter.patient; state.admissionId = data.encounter.admission_id || ''; state.analysis = data.latest_record; state.archive = data.archive; state.uploadedVideos = data.videos || [];
      showView('capture'); renderDraftIdentity(); fillProfileForm();
      if (data.latest_record) { renderReport(data.latest_record); showReportStep(); setStep(4); }
      else { setStep(2); }
    }).catch(function (error) { toast(error.message); });
  }

  $('newDoctorDetection').addEventListener('click', function () { startFlow('new'); });
  $('backDashboard').addEventListener('click', function () { showView('dashboard'); });
  window.addEventListener('resize', function () { if ($('dashboardView').classList.contains('active')) renderTrend(state.trend); });
  window.addEventListener('beforeunload', function () { stopCamera(); });

  if (state.token) enterApp().catch(function () { logout(false); });
})();
