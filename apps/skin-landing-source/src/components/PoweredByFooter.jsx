import React from 'react';

/**
 * 日坛AI技术支持底部组件
 * 技术团队可根据需要调整样式和链接
 */
const PoweredByFooter = () => (
  <div className="powered-by-footer">
    <a
      href="http://ritanai.com/"
      target="_blank"
      rel="noreferrer"
      className="ritanai-link"
      aria-label="日坛AI提供技术支持"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M8 4V8L11 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
      <span>日坛AI提供技术支持</span>
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M4 2L8 6L4 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </a>
  </div>
);

export default PoweredByFooter;
