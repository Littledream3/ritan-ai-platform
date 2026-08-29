import { CONFIG } from './config.js';
import { dom } from './dom.js';
import { analyzeImage } from './api.js?v=20260729-platform2';
import { showReport, transformResponse } from './report.js?v=20260729-platform2';
import { trackEvent } from './engagement.js?v=20260729-platform2';
import { renderChecks, setCaptureProgress, setCaptureTip, setFooterHint, setStatus, showCaptureScene } from './ui.js';

const initialChecks = () => ({
  light: { ok: false, text: '不佳' },
  facing: { ok: false, text: '不佳' },
  position: { ok: false, text: '不佳' },
});

const state = {
  stream: null,
  detector: null,
  rafId: null,
  captured: false,
  analyzing: false,
  stableSince: 0,
  lastDetectAt: 0,
  checks: initialChecks(),
};

// Eager init: start loading MediaPipe as early as possible
let mediaPipePromise = null;
let mediaPipeReady = false;

export async function initMediaPipe() {
  if (mediaPipePromise) return mediaPipePromise;
  mediaPipePromise = loadFaceDetector().then(() => { mediaPipeReady = true; });
  return mediaPipePromise;
}

export function isMediaPipeReady() {
  return mediaPipeReady;
}

export function stopCamera() {
  if (state.rafId) cancelAnimationFrame(state.rafId);
  state.rafId = null;
  if (state.stream) {
    state.stream.getTracks().forEach(track => track.stop());
    state.stream = null;
  }
  if (dom.video) dom.video.srcObject = null;
}

export async function startCamera() {
  resetCaptureState();
  showCaptureScene();
  setCaptureTip('正在准备检测');

  if (!navigator.mediaDevices?.getUserMedia) {
    setCaptureTip('无法打开相机');
    setStatus('当前浏览器不支持摄像头采集，请使用 HTTPS 环境和支持相机的浏览器。', true);
    return;
  }

  // If MediaPipe isn't ready yet, show a loading message
  if (!mediaPipeReady) {
    setCaptureTip('首次加载检测引擎');
    setFooterHint('正在下载 AI 模型，约需几秒，后续使用将秒开');
  }

  try {
    await loadFaceDetector();
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 1600 } },
      audio: false,
    });
    dom.video.srcObject = state.stream;
    await dom.video.play();
    setCaptureTip('请将面部置于框线范围内');
    setFooterHint('三项均达到要求后，将保持 3 秒自动拍摄');
    state.rafId = requestAnimationFrame(analyzeFrame);
  } catch (err) {
    setCaptureTip('无法打开相机');
    setFooterHint('请允许相机权限后重新进入检测');
    setStatus(err.message || '无法打开摄像头，请检查浏览器权限。', true);
  }
}

function resetCaptureState() {
  stopCamera();
  state.captured = false;
  state.analyzing = false;
  state.stableSince = 0;
  state.lastDetectAt = 0;
  state.checks = initialChecks();
  renderChecks(state.checks);
  setCaptureProgress(0);
  setCaptureTip('请将面部置于框线范围内');
  setFooterHint('三项均达到要求后，将保持 3 秒自动拍摄');
  setStatus('');
}

async function loadFaceDetector() {
  if (state.detector) return state.detector;
  const vision = await import(`${CONFIG.mediaPipeBase}/vision_bundle.mjs`);
  const fileset = await vision.FilesetResolver.forVisionTasks(`${CONFIG.mediaPipeBase}/wasm`);
  try {
    state.detector = await createDetector(vision, fileset, 'GPU');
  } catch (err) {
    state.detector = await createDetector(vision, fileset, 'CPU');
  }
  return state.detector;
}

function createDetector(vision, fileset, delegate) {
  return vision.FaceDetector.createFromOptions(fileset, {
    baseOptions: {
      modelAssetPath: `${CONFIG.mediaPipeBase}/models/blaze_face_short_range.tflite`,
      delegate,
    },
    runningMode: 'VIDEO',
    minDetectionConfidence: 0.55,
  });
}

async function analyzeFrame(now) {
  if (state.captured || state.analyzing) return;
  if (dom.video.readyState < 2 || dom.video.videoWidth === 0) {
    state.rafId = requestAnimationFrame(analyzeFrame);
    return;
  }
  if (now - state.lastDetectAt < 180) {
    state.rafId = requestAnimationFrame(analyzeFrame);
    return;
  }
  state.lastDetectAt = now;

  const ctx = prepareFrameCanvas();
  const light = evaluateLight(getFrameStats(ctx));
  const detections = detectFaces(now);
  const face = evaluateFace(detections[0]);
  state.checks = { light, facing: face.facing, position: face.position };
  renderChecks(state.checks);

  if (Object.values(state.checks).every(item => item.ok)) {
    if (!state.stableSince) state.stableSince = now;
    const elapsed = now - state.stableSince;
    const progress = Math.min(100, (elapsed / (CONFIG.readySeconds * 1000)) * 100);
    setCaptureProgress(progress);
    const remaining = Math.max(0, Math.ceil(CONFIG.readySeconds - elapsed / 1000));
    setCaptureTip(remaining > 0 ? `请保持稳定 ${remaining} 秒` : '正在自动拍摄');
    setFooterHint('检测条件良好，请保持当前姿势');
    if (elapsed >= CONFIG.readySeconds * 1000) {
      await captureAndSubmit();
      return;
    }
  } else {
    state.stableSince = 0;
    setCaptureProgress(0);
    updateGuidance(detections[0], light, face);
  }

  state.rafId = requestAnimationFrame(analyzeFrame);
}

function prepareFrameCanvas() {
  dom.canvas.width = CONFIG.frame.width;
  dom.canvas.height = CONFIG.frame.height;
  const ctx = dom.canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(dom.video, 0, 0, dom.canvas.width, dom.canvas.height);
  return ctx;
}

function detectFaces(now) {
  try {
    return state.detector.detectForVideo(dom.video, now).detections || [];
  } catch (err) {
    setStatus('人脸检测失败，请刷新页面重试。', true);
    return [];
  }
}

function getFrameStats(ctx) {
  const image = ctx.getImageData(0, 0, CONFIG.frame.width, CONFIG.frame.height);
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
  const t = CONFIG.thresholds.light;
  if (stats.average < t.minAverage || stats.darkRatio > t.maxDarkRatio) return { ok: false, text: '不佳' };
  if (stats.average > t.maxAverage || stats.brightRatio > t.maxBrightRatio) return { ok: false, text: '不佳' };
  return { ok: true, text: '良好' };
}

function evaluateFace(detection) {
  if (!detection?.boundingBox || !dom.video.videoWidth || !dom.video.videoHeight) {
    return {
      facing: { ok: false, text: '不佳' },
      position: { ok: false, text: '不佳' },
    };
  }

  const t = CONFIG.thresholds.face;
  const box = detection.boundingBox;
  const ox = box.originX ?? box.origin_x ?? 0;
  const oy = box.originY ?? box.origin_y ?? 0;
  const cx = (ox + box.width / 2) / dom.video.videoWidth;
  const cy = (oy + box.height / 2) / dom.video.videoHeight;
  const widthRatio = box.width / dom.video.videoWidth;
  const heightRatio = box.height / dom.video.videoHeight;
  const centered = Math.hypot(cx - 0.5, cy - 0.48) < t.maxCenterOffset;
  const sizeOk = widthRatio >= t.minWidthRatio && widthRatio <= t.maxWidthRatio
    && heightRatio >= t.minHeightRatio && heightRatio <= t.maxHeightRatio;
  const aspect = box.width / box.height;
  const facingOk = aspect >= t.minAspect && aspect <= t.maxAspect;

  return {
    facing: { ok: facingOk, text: facingOk ? '良好' : '不佳' },
    position: { ok: centered && sizeOk, text: centered && sizeOk ? '良好' : '不佳' },
  };
}

function updateGuidance(detection, light, face) {
  if (!detection) {
    setCaptureTip('请将面部置于框线范围内');
    setFooterHint('保持正脸，头发和眼镜不要遮挡面部');
  } else if (!light.ok) {
    setCaptureTip('请调整灯光');
    setFooterHint('避免过暗、背光或强反光环境');
  } else if (!face.facing.ok) {
    setCaptureTip('请面向前方');
    setFooterHint('眼睛张开向前看，头部保持水平');
  } else {
    setCaptureTip('请将面部置于框线范围内');
    setFooterHint('让脸部居中，距离手机不要过近或过远');
  }
}

async function captureAndSubmit() {
  if (state.captured) return;
  state.captured = true;
  state.analyzing = true;
  if (state.rafId) cancelAnimationFrame(state.rafId);
  setCaptureTip('正在分析肌肤状态');
  setFooterHint('AI 正在分析，通常需要 20-60 秒');

  const blob = await captureVideoFrame();
  if (!blob) {
    state.captured = false;
    state.analyzing = false;
    setStatus('拍摄失败，请重新检测。', true);
    return;
  }

  setStatus('AI 正在分析您的肌肤状态，请保持页面打开。');
  try {
    trackEvent('skin_capture_completed');
    const data = await analyzeImage(blob);
    stopCamera();
    showReport(transformResponse(data));
  } catch (err) {
    state.captured = false;
    state.analyzing = false;
    setStatus(err.message || '分析失败，请稍后重试。', true);
    setCaptureTip('分析失败');
    setFooterHint('点击下方提示区域重新检测', () => startCamera());
  }
}

function captureVideoFrame() {
  const output = document.createElement('canvas');
  output.width = dom.video.videoWidth;
  output.height = dom.video.videoHeight;
  output.getContext('2d').drawImage(dom.video, 0, 0, output.width, output.height);
  return new Promise(resolve => output.toBlob(resolve, 'image/jpeg', 0.92));
}
