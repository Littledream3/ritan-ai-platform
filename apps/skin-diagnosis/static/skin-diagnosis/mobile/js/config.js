export const CONFIG = {
  apiUrl: 'https://ritanai.com/lanjiao/api/analyze-single',
  mediaPipeBase: '/mediapipe',
  readySeconds: 3,
  frame: {
    width: 180,
    height: 240,
  },
  thresholds: {
    light: {
      minAverage: 65,
      maxAverage: 215,
      maxDarkRatio: 0.48,
      maxBrightRatio: 0.14,
    },
    face: {
      minWidthRatio: 0.28,
      maxWidthRatio: 0.68,
      minHeightRatio: 0.32,
      maxHeightRatio: 0.78,
      maxCenterOffset: 0.18,
      minAspect: 0.45,
      maxAspect: 1.25,
    },
  },
};

export const AUTH_BASE = CONFIG.apiUrl.replace('/analyze-single', '/email');
