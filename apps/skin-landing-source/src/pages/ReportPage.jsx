import React from 'react';
import { BackIcon } from '../components/Icons';
import { generateMockAnalysisData } from '../utils/mockData';
import RadarChart from '../components/RadarChart';
import ScoreCircle from '../components/ScoreCircle';

/**
 * 报告页
 * 展示皮肤分析结果和建议
 */
const ReportPage = ({ onNavigate, data }) => {
  const analysisData = data?.analysisData || generateMockAnalysisData();

  const metrics = [
    {
      name: '皱纹分析',
      value: analysisData.wrinkles,
      color: '#1B3A5C',
      desc: analysisData.wrinkles >= 70
        ? '皱纹较少，皮肤平滑'
        : analysisData.wrinkles >= 50
        ? '轻度皱纹，注意保养'
        : '皱纹明显，建议加强护理'
    },
    {
      name: '色斑检测',
      value: analysisData.spots,
      color: '#2E86C1',
      desc: analysisData.spots >= 70
        ? '色斑较少，皮肤均匀'
        : analysisData.spots >= 50
        ? '轻度色斑，需要注意'
        : '色斑明显，建议治疗'
    },
    {
      name: '弹性评估',
      value: analysisData.elasticity,
      color: '#4DA8DA',
      desc: analysisData.elasticity >= 70
        ? '弹性良好，皮肤紧致'
        : analysisData.elasticity >= 50
        ? '轻度松弛，需要护理'
        : '弹性下降明显'
    },
    {
      name: '毛孔状况',
      value: analysisData.pores,
      color: '#FF9800',
      desc: analysisData.pores >= 70
        ? '毛孔细腻，皮肤光滑'
        : analysisData.pores >= 50
        ? '毛孔轻微粗大'
        : '毛孔粗大明显'
    }
  ];

  const handleShare = () => {
    alert('分享功能开发中');
  };

  return (
    <div className="page report-page">
      {/* 页面头部 */}
      <div className="page-header">
        <div className="back-btn" onClick={() => onNavigate('home')}>
          <BackIcon />
        </div>
        <span className="page-title">皮肤分析报告</span>
        <div style={{ width: 40 }}></div>
      </div>

      {/* 报告内容 */}
      <div className="report-content">
        {/* 综合评分卡片 */}
        <div className="card animate-fadeIn">
          <div className="score-header">
            <span className="score-label">综合评分</span>
            <span className="score-date">{analysisData.analysisDate}</span>
          </div>
          <div className="score-display">
            <div className="score-circle">
              <ScoreCircle score={analysisData.score} />
            </div>
            <div className="score-info">
              <span className="glogau-level">{analysisData.glogauLevel}</span>
              <span className="glogau-desc">{analysisData.glogauDescription}</span>
            </div>
          </div>
        </div>

        {/* 雷达图卡片 */}
        <div className="card animate-fadeIn" style={{ animationDelay: '0.1s' }}>
          <span className="card-title">皮肤状态雷达图</span>
          <RadarChart data={analysisData} />
        </div>

        {/* 详细评估指标卡片 */}
        <div className="card animate-fadeIn" style={{ animationDelay: '0.2s' }}>
          <span className="card-title">详细评估指标</span>
          {metrics.map((item, i) => (
            <div key={i} className="metric-item">
              <div className="metric-header">
                <span className="metric-name">{item.name}</span>
                <span className="metric-value">{item.value}分</span>
              </div>
              <div className="metric-bar">
                <div
                  className="metric-fill"
                  style={{ width: `${item.value}%`, backgroundColor: item.color }}
                />
              </div>
              <span className="metric-desc">{item.desc}</span>
            </div>
          ))}
        </div>

        {/* 个性化建议卡片 */}
        <div className="card animate-fadeIn" style={{ animationDelay: '0.3s' }}>
          <span className="card-title">个性化护肤建议</span>
          {analysisData.recommendations.map((rec, i) => (
            <div key={i} className="recommendation-item">
              <div className="rec-number">{i + 1}</div>
              <span className="rec-text">{rec}</span>
            </div>
          ))}
        </div>

        {/* 操作按钮 */}
        <div className="report-actions">
          <button className="btn btn-outline" onClick={() => onNavigate('home')}>
            返回首页
          </button>
          <button className="btn btn-primary" onClick={handleShare}>
            分享报告
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportPage;
