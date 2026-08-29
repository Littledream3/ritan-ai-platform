import React from 'react';

const GLOGAU_COLORS = {
  excellent: '#4CAF50',
  good: '#FF9800',
  fair: '#F44336'
};

/**
 * 评分圆环组件
 * @param {Object} props
 * @param {number} props.score - 综合评分 (0-100)
 * @param {number} props.size - 圆环尺寸
 */
const ScoreCircle = ({ score, size = 140 }) => {
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - score / 100);

  // 根据分数确定颜色
  const getColor = () => {
    if (score >= 80) return GLOGAU_COLORS.excellent;
    if (score >= 60) return GLOGAU_COLORS.good;
    return GLOGAU_COLORS.fair;
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* 背景圆环 */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#E2E8F0"
        strokeWidth="10"
      />
      {/* 进度圆环 */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={getColor()}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={strokeDashoffset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: 'stroke-dashoffset 0.5s ease' }}
      />
      {/* 中心文字 */}
      <text
        x={size / 2}
        y={size / 2 - 10}
        textAnchor="middle"
        fontSize="36"
        fontWeight="bold"
        fill="#1A2A3A"
      >
        {score}
      </text>
      <text
        x={size / 2}
        y={size / 2 + 15}
        textAnchor="middle"
        fontSize="14"
        fill="#6B7B8D"
      >
        / 100
      </text>
    </svg>
  );
};

export default ScoreCircle;
