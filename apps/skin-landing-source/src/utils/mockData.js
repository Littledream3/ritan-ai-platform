/**
 * Mock data generator for skin analysis
 * 技术团队需要替换为真实的API调用
 */

const GlogauLevels = [
  { level: 'Ⅰ级', description: '轻度光老化 - 无明显皱纹，轻度色素改变' },
  { level: 'Ⅱ级', description: '中度光老化 - 早期皱纹，轻中度色斑' },
  { level: 'Ⅲ级', description: '重度光老化 - 中度皱纹，明显色斑' },
  { level: 'Ⅳ级', description: '严重光老化 - 严重皱纹，皮肤弹性差' }
];

export const generateMockAnalysisData = () => {
  const baseScore = Math.floor(Math.random() * 30) + 60;
  const levelIndex = Math.min(3, Math.floor((100 - baseScore) / 25));

  return {
    score: baseScore,
    wrinkles: Math.floor(Math.random() * 40) + 40,
    spots: Math.floor(Math.random() * 30) + 30,
    elasticity: Math.floor(Math.random() * 40) + 50,
    pores: Math.floor(Math.random() * 30) + 40,
    photoaging: Math.floor(Math.random() * 30) + 40,
    glogauLevel: GlogauLevels[levelIndex].level,
    glogauDescription: GlogauLevels[levelIndex].description,
    recommendations: [
      '建议使用含有视黄醇的抗衰精华',
      '加强防晒措施，SPF30以上',
      '考虑进行光子嫩肤治疗',
      '保持充足睡眠和水分摄入'
    ],
    analysisDate: new Date().toLocaleDateString('zh-CN')
  };
};

/**
 * 模拟AI皮肤分析API调用
 * @param {string[]} images - 面部图像数组
 * @returns {Promise<Object>} 分析结果
 */
export const analyzeSkin = async (images) => {
  // TODO: 技术团队需要替换为真实的API调用
  // 示例API调用：
  // const response = await fetch('/api/skin/analyze', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ images })
  // });
  // return await response.json();

  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(generateMockAnalysisData());
    }, 2000);
  });
};

/**
 * 模拟创面愈合分析API调用
 * @param {string[]} images - 创面图像数组
 * @param {string} surgeryType - 手术类型
 * @returns {Promise<Object>} 分析结果
 */
export const analyzeWound = async (images, surgeryType) => {
  // TODO: 技术团队需要替换为真实的API调用
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        healingRate: Math.floor(Math.random() * 30) + 60,
        woundArea: Math.floor(Math.random() * 50) + 20,
        inflammation: Math.floor(Math.random() * 20) + 10,
        recommendation: '创面愈合进度正常，请继续保持清洁护理'
      });
    }, 2000);
  });
};

/**
 * 获取Glogau分级标准描述
 * @param {string} level - 分级等级
 * @returns {Object} 分级描述
 */
export const getGlogauDescription = (level) => {
  return GlogauLevels.find(g => g.level === level) || GlogauLevels[0];
};
