import React, { useState } from 'react';
import { BackIcon } from '../components/Icons';

/**
 * 检测入口页 — 四模块全屏上下分段式布局
 * 模块1：顶部 AI 检测可视化区
 * 模块2：检测辅助功能区
 * 模块3：用户授权区
 * 模块4：核心行动按钮区
 */
const DetectEntryPage = ({ onNavigate }) => {
  const [agreed, setAgreed] = useState(false);

  return (
    <div className="detect-entry-page">

      {/* ===== 模块1：顶部 AI 检测可视化区 ===== */}
      <div className="detect-visual-section">
        {/* 顶部导航 */}
        <div className="detect-top-bar">
          <div className="detect-back-btn" onClick={() => onNavigate('home')}>
            <BackIcon />
          </div>
          <span className="detect-top-title">AI 皮肤衰老检测</span>
          <div style={{ width: 40 }} />
        </div>

        {/* 人像背景 + AI检测网格 */}
        <div className="detect-face-area">
          {/* 背景科技纹理 */}
          <div className="detect-tech-bg">
            <div className="detect-grid-overlay" />
            <div className="detect-data-lines" />
          </div>

          {/* 人像 */}
          <div className="detect-face-wrap">
            <img
              src="./picture/页面.png"
              alt="AI皮肤检测"
              className="detect-face-img"
            />

            {/* AI 人脸网格线 */}
            <svg className="detect-face-mesh" viewBox="0 0 320 400" preserveAspectRatio="xMidYMid slice">
              {/* 面部轮廓 */}
              <ellipse cx="160" cy="175" rx="85" ry="105" stroke="rgba(255,255,255,0.35)" strokeWidth="1" fill="none" />
              {/* 眼周关键点连线 */}
              <line x1="115" y1="135" x2="135" y2="128" stroke="rgba(255,255,255,0.5)" strokeWidth="1" />
              <line x1="135" y1="128" x2="150" y2="132" stroke="rgba(255,255,255,0.5)" strokeWidth="1" />
              <line x1="170" y1="132" x2="185" y2="128" stroke="rgba(255,255,255,0.5)" strokeWidth="1" />
              <line x1="185" y1="128" x2="205" y2="135" stroke="rgba(255,255,255,0.5)" strokeWidth="1" />
              {/* 眼周环绕 */}
              <circle cx="142" cy="135" r="2.5" fill="rgba(255,255,255,0.6)" />
              <circle cx="178" cy="135" r="2.5" fill="rgba(255,255,255,0.6)" />
              {/* 眉弓 */}
              <path d="M108 122 Q140 108 175 115 Q195 118 212 122" stroke="rgba(255,255,255,0.4)" strokeWidth="1" fill="none" />
              {/* 法令纹区域 */}
              <path d="M130 175 Q135 200 128 225" stroke="rgba(255,255,255,0.35)" strokeWidth="1" fill="none" />
              <path d="M190 175 Q185 200 192 225" stroke="rgba(255,255,255,0.35)" strokeWidth="1" fill="none" />
              {/* 额头纹理区 */}
              <path d="M120 100 Q160 88 200 100" stroke="rgba(255,255,255,0.3)" strokeWidth="0.8" fill="none" />
              <path d="M125 110 Q160 98 195 110" stroke="rgba(255,255,255,0.25)" strokeWidth="0.8" fill="none" />
              {/* 下颌线 */}
              <path d="M100 200 Q160 260 220 200" stroke="rgba(255,255,255,0.3)" strokeWidth="1" fill="none" />
              {/* 鼻梁 */}
              <line x1="160" y1="125" x2="160" y2="168" stroke="rgba(255,255,255,0.4)" strokeWidth="0.8" />
              {/* 关键点标记 */}
              <circle cx="130" cy="170" r="1.8" fill="rgba(255,255,255,0.5)" />
              <circle cx="190" cy="170" r="1.8" fill="rgba(255,255,255,0.5)" />
              <circle cx="160" cy="168" r="2" fill="rgba(255,255,255,0.5)" />
              <circle cx="135" cy="148" r="1.5" fill="rgba(255,255,255,0.4)" />
              <circle cx="185" cy="148" r="1.5" fill="rgba(255,255,255,0.4)" />
              <circle cx="160" cy="130" r="1.5" fill="rgba(255,255,255,0.45)" />
            </svg>

            {/* L形取景框 — 左上角 */}
            <div className="detect-viewfinder detect-viewfinder--tl">
              <div className="detect-vf-h"></div>
              <div className="detect-vf-v"></div>
            </div>
            {/* L形取景框 — 左下角 */}
            <div className="detect-viewfinder detect-viewfinder--bl">
              <div className="detect-vf-v"></div>
              <div className="detect-vf-h"></div>
            </div>

          </div>
        </div>
      </div>

      {/* ===== 模块2：检测辅助功能区 ===== */}
      <div className="detect-aux-section">
        <div className="detect-aux-item">
          <div className="detect-aux-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              {/* 关美颜 — 人像+斜线禁止 */}
              <circle cx="24" cy="16" r="9" stroke="white" strokeWidth="2" fill="none" />
              <path d="M8 42C8 33.163 15.163 26 24 26C32.837 26 40 33.163 40 42" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
              <line x1="10" y1="10" x2="38" y2="38" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
            </svg>
          </div>
          <span className="detect-aux-text">关美颜</span>
        </div>

        <div className="detect-aux-item">
          <div className="detect-aux-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              {/* 摘眼镜 — 眼镜 + 叉号 */}
              <circle cx="17" cy="18" r="7" stroke="white" strokeWidth="2" fill="none" />
              <circle cx="31" cy="18" r="7" stroke="white" strokeWidth="2" fill="none" />
              <path d="M10 18H24M24 18H38" stroke="white" strokeWidth="2" />
              <path d="M24 18V22" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="6" y1="6" x2="42" y2="42" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
            </svg>
          </div>
          <span className="detect-aux-text">摘眼镜</span>
        </div>

        <div className="detect-aux-item">
          <div className="detect-aux-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              {/* 无背光 — 灯泡 + 禁止 */}
              <circle cx="24" cy="22" r="13" stroke="white" strokeWidth="2" fill="none" />
              <path d="M18 36C18 38.209 20.686 40 24 40C27.314 40 30 38.209 30 36" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="24" y1="18" x2="24" y2="28" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M24 9V5" stroke="white" strokeWidth="2" strokeLinecap="round" />
              {/* 背光方向箭头 + 禁止 */}
              <path d="M30 8L42 20" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <path d="M42 20L36 10" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="32" y1="14" x2="40" y2="22" stroke="rgba(255,255,255,0.6)" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <span className="detect-aux-text">无背光</span>
        </div>

        <div className="detect-aux-item">
          <div className="detect-aux-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              {/* 无曝光 — 太阳/闪光线 + 禁止 */}
              <circle cx="24" cy="24" r="8" stroke="white" strokeWidth="2" fill="none" />
              {/* 光芒线条 */}
              <line x1="24" y1="2" x2="24" y2="10" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="24" y1="38" x2="24" y2="46" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="2" y1="24" x2="10" y2="24" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="38" y1="24" x2="46" y2="24" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="8.5" y1="8.5" x2="14" y2="14" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="34" y1="34" x2="39.5" y2="39.5" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="8.5" y1="39.5" x2="14" y2="34" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="34" y1="14" x2="39.5" y2="8.5" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <span className="detect-aux-text">无曝光</span>
        </div>
      </div>

      {/* ===== 模块3：用户授权区 ===== */}
      <div className="detect-auth-section">
        <div className="detect-auth-bg">
          {/* 勾选框 */}
          <div
            className={`detect-checkbox ${agreed ? 'detect-checkbox--checked' : ''}`}
            onClick={() => setAgreed(!agreed)}
          >
            {agreed && (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 7L6 10L11 4" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>

          {/* 文字说明 */}
          <span className="detect-auth-text">
            我已阅读并同意
            <span
              className="detect-auth-link"
              onClick={(e) => { e.stopPropagation(); alert('《兰峤用户服务协议》内容'); }}
            >
              《兰峤用户服务协议》
            </span>
            和
            <span
              className="detect-auth-link"
              onClick={(e) => { e.stopPropagation(); alert('《兰峤隐私保护政策》内容'); }}
            >
              《兰峤隐私保护政策》
            </span>
          </span>
        </div>
      </div>

      {/* ===== 模块4：核心行动按钮区 ===== */}
      <div className="detect-action-section">
        <button
          className={`detect-action-btn ${agreed ? 'detect-action-btn--active' : 'detect-action-btn--disabled'}`}
          disabled={!agreed}
          onClick={() => agreed && onNavigate('guide')}
        >
          {agreed ? (
            <>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{ marginRight: 8 }}>
                <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2" />
                <path d="M10 8L16 12L10 16V8Z" fill="white" />
              </svg>
              开始皮肤衰老检测
            </>
          ) : (
            '请先阅读并同意协议'
          )}
        </button>
      </div>

    </div>
  );
};

export default DetectEntryPage;