import React, { useState, useEffect } from 'react';
import { ANALYSIS_STEPS } from '../utils/constants';
import { generateMockAnalysisData } from '../utils/mockData';

/**
 * AI分析页
 * 展示分析进度动画
 */
const AnalysisPage = ({ onNavigate }) => {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    // 计算每个步骤的时间
    const totalTime = ANALYSIS_STEPS.length * 400; // 每个步骤400ms
    const intervalTime = totalTime / 100;

    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          // 分析完成后跳转到报告页
          setTimeout(() => {
            onNavigate('report', { analysisData: generateMockAnalysisData() });
          }, 500);
          return 100;
        }
        return prev + 1;
      });
    }, intervalTime);

    // 逐个显示分析步骤
    ANALYSIS_STEPS.forEach((_, i) => {
      setTimeout(() => setCurrentStep(i), i * 400);
    });

    return () => clearInterval(interval);
  }, [onNavigate]);

  return (
    <div className="page analysis-page">
      <div className="analysis-content">
        {/* 进度动画 */}
        <div className="analysis-animation">
          <div className="analysis-circle">
            <svg width="140" height="140" viewBox="0 0 140 140">
              {/* 背景圆环 */}
              <circle
                cx="70"
                cy="70"
                r="60"
                fill="none"
                stroke="rgba(255,255,255,0.2)"
                strokeWidth="8"
              />
              {/* 进度圆环 */}
              <circle
                cx="70"
                cy="70"
                r="60"
                fill="none"
                stroke="white"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 60}`}
                strokeDashoffset={`${2 * Math.PI * 60 * (1 - progress / 100)}`}
                transform="rotate(-90 70 70)"
              />
              {/* 中心文字 */}
              <text x="70" y="65" textAnchor="middle" fontSize="36" fontWeight="bold" fill="white">
                {progress}%
              </text>
              <text x="70" y="90" textAnchor="middle" fontSize="14" fill="rgba(255,255,255,0.7)">
                分析中
              </text>
            </svg>
          </div>
        </div>

        {/* 分析步骤列表 */}
        <div className="analysis-steps">
          {ANALYSIS_STEPS.map((step, index) => (
            <div
              key={index}
              className={`analysis-step ${
                index < currentStep ? 'completed' : ''
              } ${index === currentStep ? 'active' : ''}`}
            >
              <div className="step-indicator">
                {index < currentStep ? (
                  '✓'
                ) : index === currentStep ? (
                  <div className="step-spinner"></div>
                ) : (
                  '○'
                )}
              </div>
              <span className="step-name">{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AnalysisPage;
