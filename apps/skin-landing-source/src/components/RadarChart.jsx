import React from 'react';

const GLOGAU_COLORS = {
  excellent: '#4CAF50',
  good: '#FF9800',
  fair: '#F44336'
};

/**
 * 雷达图组件
 * 用于展示皮肤各项指标的得分情况
 * @param {Object} data - 皮肤分析数据
 */
const RadarChart = ({ data }) => {
  const items = [
    { name: '皱纹', value: data.wrinkles || 0 },
    { name: '色斑', value: data.spots || 0 },
    { name: '弹性', value: data.elasticity || 0 },
    { name: '毛孔', value: data.pores || 0 },
    { name: '光老化', value: data.photoaging || 0 }
  ];

  const centerX = 140;
  const centerY = 140;
  const maxRadius = 100;

  // 计算多边形顶点
  const points = items.map((item, i) => {
    const angle = (i * 72 - 90) * Math.PI / 180;
    const r = (item.value / 100) * maxRadius;
    return `${centerX + r * Math.cos(angle)},${centerY + r * Math.sin(angle)}`;
  }).join(' ');

  return (
    <div className="radar-chart-container">
      <svg width="280" height="280" viewBox="0 0 280 280">
        {/* 背景网格 */}
        {[1, 2, 3, 4, 5].map(i => (
          <circle
            key={`grid-${i}`}
            cx={centerX}
            cy={centerY}
            r={i * 20}
            fill="none"
            stroke="#E2E8F0"
            strokeWidth="1"
          />
        ))}

        {/* 轴线 */}
        {[0, 72, 144, 216, 288].map((angle, i) => {
          const rad = (angle - 90) * Math.PI / 180;
          return (
            <line
              key={`axis-${i}`}
              x1={centerX}
              y1={centerY}
              x2={centerX + maxRadius * Math.cos(rad)}
              y2={centerY + maxRadius * Math.sin(rad)}
              stroke="#E2E8F0"
              strokeWidth="1"
            />
          );
        })}

        {/* 数据多边形 */}
        <polygon
          points={points}
          fill="rgba(27, 58, 92, 0.3)"
          stroke="#1B3A5C"
          strokeWidth="2"
        />

        {/* 数据点 */}
        {items.map((item, i) => {
          const angle = (i * 72 - 90) * Math.PI / 180;
          const r = (item.value / 100) * maxRadius;
          return (
            <circle
              key={`point-${i}`}
              cx={centerX + r * Math.cos(angle)}
              cy={centerY + r * Math.sin(angle)}
              r="6"
              fill="#1B3A5C"
              stroke="white"
              strokeWidth="2"
            />
          );
        })}

        {/* 标签 */}
        {items.map((item, i) => {
          const angle = (i * 72 - 90) * Math.PI / 180;
          const labelRadius = maxRadius + 30;
          const x = centerX + labelRadius * Math.cos(angle);
          const y = centerY + labelRadius * Math.sin(angle);

          return (
            <text
              key={`label-${i}`}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#6B7B8D"
              fontSize="12"
            >
              {item.name}
            </text>
          );
        })}
      </svg>
    </div>
  );
};

export default RadarChart;
