import React, { useState } from 'react';
import { BackIcon } from '../components/Icons';
import { CAPTURE_ANGLES } from '../utils/constants';

/**
 * 图像采集页
 * 支持多角度面部拍摄
 */
const CapturePage = ({ onNavigate }) => {
  const [currentAngle, setCurrentAngle] = useState(0);
  const [capturedImages, setCapturedImages] = useState([]);
  const [isCapturing, setIsCapturing] = useState(false);

  const handleCapture = async () => {
    setIsCapturing(true);
    // 模拟拍摄延迟
    await new Promise(resolve => setTimeout(resolve, 500));

    // 生成模拟图像
    const mockImage = `data:image/svg+xml,${encodeURIComponent(`
      <svg width="300" height="400" xmlns="http://www.w3.org/2000/svg">
        <rect width="300" height="400" fill="#1A2A3A"/>
        <circle cx="150" cy="180" r="80" fill="#4A4543"/>
        <text x="150" y="200" text-anchor="middle" fill="#6B7B8D" font-size="14">${CAPTURE_ANGLES[currentAngle].name}</text>
      </svg>
    `)}`;

    const newImages = [...capturedImages, mockImage];
    setCapturedImages(newImages);
    setIsCapturing(false);

    // 如果还有下一个角度，自动切换
    if (currentAngle < CAPTURE_ANGLES.length - 1) {
      setCurrentAngle(currentAngle + 1);
    }
  };

  const isAllCaptured = capturedImages.length === CAPTURE_ANGLES.length;

  return (
    <div className="page capture-page">
      {/* 页面头部 */}
      <div className="capture-header">
        <div className="back-btn" onClick={() => onNavigate('guide')}>
          <BackIcon />
        </div>
        <span className="capture-title">面部图像采集</span>
        <div style={{ width: 40 }}></div>
      </div>

      {/* 采集内容 */}
      <div className="capture-content">
        {/* 角度进度 */}
        <div className="angle-progress">
          {CAPTURE_ANGLES.map((angle, index) => (
            <div
              key={index}
              className={`angle-step ${
                index === currentAngle ? 'active' : ''
              } ${index < currentAngle || capturedImages[index] ? 'completed' : ''}`}
            >
              <div className="angle-number">
                {capturedImages[index] ? '✓' : index + 1}
              </div>
              <span className="angle-name">{angle.name}</span>
            </div>
          ))}
        </div>

        {/* 预览区域 */}
        <div className="preview-container">
          <div className="preview-frame">
            {capturedImages[currentAngle] ? (
              <img
                src={capturedImages[currentAngle]}
                className="preview-image"
                alt="preview"
              />
            ) : (
              <div className="preview-placeholder">
                <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                  <circle cx="40" cy="40" r="30" stroke="#666" strokeWidth="3" strokeDasharray="8 4"/>
                  <circle cx="40" cy="35" r="10" stroke="#666" strokeWidth="2"/>
                </svg>
                <span className="placeholder-text">请拍摄{CAPTURE_ANGLES[currentAngle].name}</span>
              </div>
            )}

            {/* 拍摄引导框 */}
            {!capturedImages[currentAngle] && (
              <div className="guide-overlay">
                <div className="guide-box">
                  <div className="guide-corner top-left"></div>
                  <div className="guide-corner top-right"></div>
                  <div className="guide-corner bottom-left"></div>
                  <div className="guide-corner bottom-right"></div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 缩略图 */}
        {capturedImages.length > 0 && (
          <div className="thumbnails">
            {capturedImages.map((img, index) => (
              <div key={index} className="thumbnail-item">
                <img src={img} className="thumbnail-image" alt={`thumbnail-${index}`} />
              </div>
            ))}
          </div>
        )}

        {/* 提示文字 */}
        <div className="capture-tip">
          <span className="tip-text">
            {capturedImages[currentAngle]
              ? `${CAPTURE_ANGLES[currentAngle].name}已采集${
                  currentAngle < CAPTURE_ANGLES.length - 1
                    ? '，请继续下一个角度'
                    : '，可以开始分析'
                }`
              : '请将面部对准框内，保持正对镜头'}
          </span>
        </div>
      </div>

      {/* 底部操作 */}
      <div className="capture-footer">
        {isAllCaptured ? (
          <button
            className="btn btn-secondary btn-large btn-block"
            onClick={() => onNavigate('analysis')}
          >
            开始AI分析
          </button>
        ) : (
          <div className="capture-btn-container">
            <button
              className={`capture-btn ${isCapturing ? 'capturing' : ''}`}
              onClick={handleCapture}
              disabled={isCapturing}
            >
              <div className="capture-btn-inner">
                {isCapturing ? (
                  <div className="capture-loading"></div>
                ) : (
                  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                    <circle cx="16" cy="16" r="14" fill="white"/>
                  </svg>
                )}
              </div>
            </button>
            <span className="capture-hint">点击拍照</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CapturePage;
