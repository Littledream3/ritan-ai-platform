export const $ = (id) => document.getElementById(id);

export const dom = {
  landing: $('landing'),
  captureApp: $('captureApp'),
  reportView: $('reportView'),
  video: $('video'),
  canvas: $('canvas'),
  statusBox: $('statusBox'),
  captureNotice: $('captureNotice'),
  captureScene: $('captureScene'),
  startCameraBtn: $('startCameraBtn'),
  centerTip: $('centerTip'),
  footerHint: $('footerHint'),
  progressRing: $('progressRing'),
  lightState: $('lightState'),
  facingState: $('facingState'),
  positionState: $('positionState'),
};
