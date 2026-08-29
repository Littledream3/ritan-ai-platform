/**
 * 应用常量配置
 */

// 拍摄角度配置
export const CAPTURE_ANGLES = [
  { id: 0, name: '正面', angle: 0 },
  { id: 1, name: '左侧45°', angle: -45 },
  { id: 2, name: '右侧45°', angle: 45 }
];

// 分析步骤配置
export const ANALYSIS_STEPS = [
  '图像预处理',
  '人脸检测与对齐',
  '皮肤区域分割',
  '皱纹分析',
  '色斑检测',
  '弹性评估',
  '综合评分生成'
];

// 皮肤评估维度
export const SKIN_DIMENSIONS = [
  { key: 'wrinkles', name: '皱纹', unit: '分' },
  { key: 'spots', name: '色斑', unit: '分' },
  { key: 'elasticity', name: '弹性', unit: '分' },
  { key: 'pores', name: '毛孔', unit: '分' },
  { key: 'photoaging', name: '光老化', unit: '分' }
];

// Glogau光老化分级标准
export const GLOGAU_LEVELS = [
  { level: 'Ⅰ级', scoreRange: [80, 100], features: ['无明显皱纹', '轻度色素改变', '皮肤质地良好'] },
  { level: 'Ⅱ级', scoreRange: [60, 79], features: ['早期皱纹', '轻中度色斑', '轻微皮肤松弛'] },
  { level: 'Ⅲ级', scoreRange: [40, 59], features: ['中度皱纹', '明显色斑', '皮肤弹性下降'] },
  { level: 'Ⅳ级', scoreRange: [0, 39], features: ['严重皱纹', '皮肤弹性差', '明显光老化迹象'] }
];

// API配置
export const API_CONFIG = {
  baseUrl: 'https://api.ritanai.com',
  endpoints: {
    skinAnalyze: '/api/skin/analyze',
    woundAnalyze: '/api/wound/analyze',
    userHistory: '/api/user/history'
  },
  timeout: 30000
};

// 性能等级阈值
export const SCORE_THRESHOLDS = {
  excellent: 80,
  good: 60,
  fair: 40
};

// 首页图片路径 (存放于 public/picture/，使用相对路径兼容 file:// 双击打开)
export const DOCTOR_IMG_1 = './picture/图片1.png';
export const DOCTOR_IMG_2 = './picture/图片2.jpg';
export const DOCTOR_IMG_3 = './picture/图片3.jpg';
