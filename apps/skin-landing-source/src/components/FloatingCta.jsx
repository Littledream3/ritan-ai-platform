import React, { useState, useRef, useCallback, useEffect } from 'react';

/* ================================================================
   FloatingCta — 可拖拽悬浮按钮
   默认固定于页面底部 TabBar 上方，可随意拖拽到任意位置
   点击跳转外部链接 https://ritanai.com/ （新标签页）
   ================================================================ */

const FloatingCta = () => {
  const btnRef = useRef(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [initialized, setInitialized] = useState(false);
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const posStart = useRef({ x: 0, y: 0 });
  const hasMoved = useRef(false);

  // 初始化默认位置：底部居中（TabBar 上方）
  useEffect(() => {
    const el = btnRef.current;
    if (!el || initialized) return;
    const rect = el.getBoundingClientRect();
    const btnWidth = rect.width;
    const defaultX = (window.innerWidth - btnWidth) / 2;
    const defaultY = window.innerHeight - 75 - rect.height;
    setPosition({ x: defaultX, y: defaultY });
    setInitialized(true);
  }, [initialized]);

  // pointer 事件
  const handlePointerDown = useCallback((e) => {
    dragging.current = true;
    hasMoved.current = false;
    dragStart.current = { x: e.clientX, y: e.clientY };
    posStart.current = { x: position.x, y: position.y };
    e.target.setPointerCapture(e.pointerId);
    e.preventDefault();
  }, [position]);

  const handlePointerMove = useCallback((e) => {
    if (!dragging.current) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      hasMoved.current = true;
    }
    const newX = Math.max(0, Math.min(window.innerWidth - 100, posStart.current.x + dx));
    const newY = Math.max(0, Math.min(window.innerHeight - 50, posStart.current.y + dy));
    setPosition({ x: newX, y: newY });
  }, []);

  const handlePointerUp = useCallback((e) => {
    dragging.current = false;
    if (e.target.releasePointerCapture) {
      e.target.releasePointerCapture(e.pointerId);
    }
  }, []);

  // 仅在未拖拽时触发点击跳转
  const handleClick = useCallback(() => {
    if (hasMoved.current) return;
    window.open('https://ritanai.com/', '_blank', 'noopener,noreferrer');
  }, []);

  return (
    <div
      ref={btnRef}
      className="floating-cta"
      style={{
        left: initialized ? `${position.x}px` : '50%',
        top: initialized ? `${position.y}px` : 'auto',
        bottom: initialized ? 'auto' : '75px',
        transform: initialized ? 'none' : 'translateX(-50%)',
        touchAction: 'none',
        cursor: 'grab',
      }}
      onClick={handleClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* 技术支持图标 */}
      <div className="floating-cta-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="#1B3A5C" strokeWidth="1.5" fill="none" />
          <path d="M8 12h3l-1 5 5-7h-3l1-5-5 7z" stroke="#1B3A5C" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <circle cx="18" cy="6" r="1.5" fill="#2E86C1" opacity="0.6" />
        </svg>
      </div>
      {/* 文字 */}
      <span className="floating-cta-text">日坛AI提供技术支持</span>
      {/* 右箭头 */}
      <svg className="floating-cta-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path d="M9 18L15 12L9 6" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
};

export default FloatingCta;
