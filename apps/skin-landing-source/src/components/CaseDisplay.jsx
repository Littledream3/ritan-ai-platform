import React, { useState, useEffect, useCallback, useRef } from 'react';

const cases = [
  {
    id: 1,
    tag: '痤疮治疗',
    tagClass: 'case-tag-acne',
    title: '重度痤疮综合治疗方案',
    desc: '经过3个月中西医结合治疗，面部痤疮明显消退，皮肤恢复光滑',
  },
  {
    id: 2,
    tag: '色斑淡化',
    tagClass: 'case-tag-spot',
    title: '黄褐斑激光联合治疗',
    desc: '光子嫩肤+中药调理，色斑面积减少80%，肤色均匀透亮',
  },
  {
    id: 3,
    tag: '抗衰老',
    tagClass: 'case-tag-aging',
    title: '面部年轻化综合方案',
    desc: '热玛吉+玻尿酸填充，面部轮廓提升，皱纹深度减少50%',
  },
  {
    id: 4,
    tag: '疤痕修复',
    tagClass: 'case-tag-acne',
    title: '痤疮疤痕综合修复方案',
    desc: '点阵激光+微针联合治疗，疤痕明显淡化，皮肤质地显著改善',
  },
  {
    id: 5,
    tag: '敏感肌修复',
    tagClass: 'case-tag-spot',
    title: '面部敏感肌屏障修复',
    desc: '舒敏治疗+医用修复产品，皮肤屏障功能恢复，泛红干痒消退',
  },
];

const CaseDisplay = ({ onNavigate }) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(0);
  const [dragOffset, setDragOffset] = useState(0);
  const trackRef = useRef(null);
  const autoPlayRef = useRef(null);

  const resetAutoPlay = useCallback(() => {
    if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    autoPlayRef.current = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % cases.length);
    }, 3000);
  }, []);

  useEffect(() => {
    resetAutoPlay();
    return () => clearInterval(autoPlayRef.current);
  }, [resetAutoPlay]);

  const goTo = useCallback((index) => {
    setActiveIndex(index);
    resetAutoPlay();
  }, [resetAutoPlay]);

  // Mouse drag handlers
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStart(e.clientX);
    setDragOffset(0);
  }, []);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    setDragOffset(e.clientX - dragStart);
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);
    if (dragOffset < -40) {
      goTo((activeIndex + 1) % cases.length);
    } else if (dragOffset > 40) {
      goTo((activeIndex - 1 + cases.length) % cases.length);
    }
    setDragOffset(0);
  }, [isDragging, dragOffset, activeIndex, goTo]);

  // Touch drag handlers
  const handleTouchStart = useCallback((e) => {
    setIsDragging(true);
    setDragStart(e.touches[0].clientX);
    setDragOffset(0);
  }, []);

  const handleTouchMove = useCallback((e) => {
    if (!isDragging) return;
    setDragOffset(e.touches[0].clientX - dragStart);
  }, [isDragging, dragStart]);

  const handleTouchEnd = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);
    if (dragOffset < -40) {
      goTo((activeIndex + 1) % cases.length);
    } else if (dragOffset > 40) {
      goTo((activeIndex - 1 + cases.length) % cases.length);
    }
    setDragOffset(0);
  }, [isDragging, dragOffset, activeIndex, goTo]);

  const getCardStyle = (index) => {
    const diff = index - activeIndex;
    const isActive = diff === 0;
    const dragEffect = isDragging ? dragOffset : 0;

    let translateX = 0;
    let opacity = 0;
    let scale = 1;
    let zIndex = 1;

    if (isActive) {
      translateX = dragEffect;
      opacity = 1;
      scale = 1;
      zIndex = 5;
    } else if (diff === 1 || diff === -(cases.length - 1)) {
      translateX = 270 + dragEffect;
      opacity = 0.55;
      scale = 0.9;
      zIndex = 3;
    } else if (diff === -1 || diff === (cases.length - 1)) {
      translateX = -270 + dragEffect;
      opacity = 0.55;
      scale = 0.9;
      zIndex = 3;
    } else if (Math.abs(diff) === 2) {
      translateX = diff > 0 ? 290 : -290;
      opacity = 0;
      scale = 0.8;
      zIndex = 1;
    } else {
      opacity = 0;
      translateX = 310;
      zIndex = 0;
    }

    return {
      transform: `translateX(${translateX}px) scale(${scale})`,
      opacity,
      zIndex,
      boxShadow: isActive
        ? '0 8px 24px rgba(27,58,92,0.18)'
        : '0 2px 8px rgba(27,58,92,0.06)',
      transition: isDragging ? 'none' : 'all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      pointerEvents: isActive ? 'auto' : 'none',
    };
  };

  return (
    <div className="case-carousel-section">
      <div className="case-carousel-title">诊断案例展示</div>
      <div
        className="case-carousel-track"
        ref={trackRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="case-carousel-viewport">
          {cases.map((c, index) => (
            <div
              key={c.id}
              className={`case-carousel-card ${index === activeIndex ? 'active' : ''}`}
              style={getCardStyle(index)}
            >
              <div className="case-card-images">
                <div className="case-img-half">
                  <span className="case-img-label case-label-before">BEFORE</span>
                  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                    <circle cx="40" cy="38" r="22" fill="#E8C8C0"/>
                    <circle cx="34" cy="34" r="3" fill="#C0392B" opacity="0.5"/>
                    <circle cx="46" cy="34" r="3" fill="#C0392B" opacity="0.5"/>
                    <circle cx="38" cy="44" r="2" fill="#C0392B" opacity="0.4"/>
                    <circle cx="44" cy="44" r="2" fill="#C0392B" opacity="0.4"/>
                  </svg>
                </div>
                <div className="case-img-half">
                  <span className="case-img-label case-label-after">AFTER</span>
                  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                    <circle cx="40" cy="38" r="22" fill="#F5E0D0"/>
                    <circle cx="34" cy="34" r="2.5" fill="#8D6E63" opacity="0.3"/>
                    <circle cx="46" cy="34" r="2.5" fill="#8D6E63" opacity="0.3"/>
                    <path d="M32 48C35 51 45 51 48 48" stroke="#8D6E63" strokeWidth="1.5" opacity="0.4" fill="none"/>
                  </svg>
                </div>
              </div>
              <div className="case-card-body">
                <span className={`case-card-tag ${c.tagClass}`}>{c.tag}</span>
                <div className="case-card-title">{c.title}</div>
                <div className="case-card-desc">{c.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="carousel-dots">
        {cases.map((_, i) => (
          <div
            key={i}
            className={`carousel-dot ${i === activeIndex ? 'active' : ''}`}
            onClick={() => goTo(i)}
          />
        ))}
      </div>
      <div className="carousel-learn-more" onClick={() => onNavigate('detect')}>
        <span>开启蜕变</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </div>
  );
};

export default CaseDisplay;
