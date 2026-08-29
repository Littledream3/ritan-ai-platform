import React, { useState } from 'react';
import { BackIcon, WarningIcon, PrivacyIcon } from '../components/Icons';

/**
 * 拍摄引导页
 * 分步骤引导用户完成拍摄准备
 */
const GuidePage = ({ onNavigate }) => {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      title: '环境准备',
      description: '确保在光线充足的环境下进行拍摄',
      icon: (
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <circle cx="40" cy="40" r="35" fill="#D6EAF8"/>
          <circle cx="40" cy="35" r="15" stroke="#1B3A5C" strokeWidth="3" fill="none"/>
          <path d="M40 50V70" stroke="#1B3A5C" strokeWidth="3" strokeLinecap="round"/>
        </svg>
      )
    },
    {
      title: '角度调整',
      description: '按照引导框调整面部角度，分别拍摄正面和左右侧45°',
      icon: (
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <circle cx="40" cy="40" r="35" fill="#E8F5E9"/>
          <path d="M25 55L40 30L55 55" stroke="#4CAF50" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="40" cy="30" r="5" fill="#4CAF50"/>
        </svg>
      )
    },
    {
      title: '开始检测',
      description: '准备好后点击下方按钮开始AI皮肤检测',
      icon: (
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <circle cx="40" cy="40" r="35" fill="#E3F2FD"/>
          <circle cx="40" cy="40" r="15" stroke="#2196F3" strokeWidth="3" fill="none"/>
          <path d="M40 30V40L48 44" stroke="#2196F3" strokeWidth="3" strokeLinecap="round"/>
        </svg>
      )
    }
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onNavigate('capture');
    }
  };

  return (
    <div className="page guide-page">
      {/* 页面头部 */}
      <div className="page-header">
        <div className="back-btn" onClick={() => onNavigate('detect')}>
          <BackIcon />
        </div>
        <span className="page-title">拍摄引导</span>
        <div style={{ width: 40 }}></div>
      </div>

      {/* 引导内容 */}
      <div className="guide-content">
        {/* 步骤指示器 */}
        <div className="step-indicators">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`step-dot ${
                index === currentStep ? 'active' : ''
              } ${index < currentStep ? 'completed' : ''}`}
            />
          ))}
        </div>

        {/* 步骤内容 */}
        <div className="step-content animate-fadeIn" key={currentStep}>
          <div className="step-icon">{steps[currentStep].icon}</div>
          <span className="step-title">{steps[currentStep].title}</span>
          <span className="step-description">{steps[currentStep].description}</span>
        </div>

        {/* 注意事项 */}
        <div className="notice-section">
          <span className="notice-title">注意事项</span>
          <div className="notice-list">
            <div className="notice-item">
              <WarningIcon />
              <span>保持面部清洁，不要化妆</span>
            </div>
            <div className="notice-item">
              <WarningIcon />
              <span>头发扎起，露出完整面部</span>
            </div>
          </div>
        </div>

        {/* 隐私声明 */}
        <div className="privacy-notice">
          <PrivacyIcon />
          <span className="privacy-text">您的图像数据将加密处理，仅用于皮肤分析</span>
        </div>
      </div>

      {/* 底部按钮 */}
      <div className="guide-footer">
        <button className="btn btn-primary btn-large btn-block" onClick={handleNext}>
          {currentStep === steps.length - 1 ? '开始检测' : '下一步'}
        </button>
      </div>
    </div>
  );
};

export default GuidePage;
