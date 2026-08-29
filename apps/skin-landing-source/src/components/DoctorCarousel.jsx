import React, { useState, useEffect, useCallback, useRef } from 'react';

const doctors = [
  { id: 1, name: '张医生', title: '主任医师', dept: '皮肤科', img: './picture/医生1.jpg' },
  { id: 2, name: '李医生', title: '副主任医师', dept: '医学美容科', img: './picture/医生2.jpg' },
  { id: 3, name: '王医生', title: '主任医师', dept: '皮肤外科', img: './picture/医生3.jpg' },
  { id: 4, name: '陈医生', title: '主治医师', dept: '中西医结合科', img: './picture/医生4.jpg' },
  { id: 5, name: '刘医生', title: '特邀专家', dept: '整形外科', img: './picture/医生5.jpg' },
];

const DoctorCarousel = ({ onNavigate }) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(0);
  const [dragOffset, setDragOffset] = useState(0);
  const trackRef = useRef(null);
  const autoPlayRef = useRef(null);

  // Reset autoplay timer
  const resetAutoPlay = useCallback(() => {
    if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    autoPlayRef.current = setInterval(() => {
      setActiveIndex(prev => (prev + 1) % doctors.length);
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
      // Swipe left → next
      goTo((activeIndex + 1) % doctors.length);
    } else if (dragOffset > 40) {
      // Swipe right → prev
      goTo((activeIndex - 1 + doctors.length) % doctors.length);
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
      goTo((activeIndex + 1) % doctors.length);
    } else if (dragOffset > 40) {
      goTo((activeIndex - 1 + doctors.length) % doctors.length);
    }
    setDragOffset(0);
  }, [isDragging, dragOffset, activeIndex, goTo]);

  // Calculate card positions relative to active
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
    } else if (diff === 1 || diff === -(doctors.length - 1)) {
      // Next card — positioned to the right, partially visible
      translateX = 240 + dragEffect;
      opacity = 0.55;
      scale = 0.9;
      zIndex = 3;
    } else if (diff === -1 || diff === (doctors.length - 1)) {
      // Previous card — positioned to the left, partially visible
      translateX = -240 + dragEffect;
      opacity = 0.55;
      scale = 0.9;
      zIndex = 3;
    } else if (Math.abs(diff) === 2) {
      // Two away — further out, hidden
      translateX = diff > 0 ? 280 : -280;
      opacity = 0;
      scale = 0.8;
      zIndex = 1;
    } else {
      opacity = 0;
      translateX = 300;
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
    <div className="doctor-carousel-section">
      <div className="doctor-carousel-title">专业医生在线问诊</div>
      <div
        className="doctor-carousel-track"
        ref={trackRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="doctor-carousel-viewport">
          {doctors.map((doc, index) => {
            return (
              <div
                key={doc.id}
                className={`doctor-card ${index === activeIndex ? 'active' : ''}`}
                style={getCardStyle(index)}
                onClick={() => {
                  if (index === activeIndex) onNavigate('detect');
                }}
              >
                <div className="doctor-card-avatar">
                  <img src={doc.img} alt={doc.name} className="doctor-card-avatar-img" />
                </div>
                <div className="doctor-card-name">{doc.name}</div>
                <div className="doctor-card-title">{doc.title}</div>
                <div className="doctor-card-dept">{doc.dept}</div>
                <button className="doctor-card-btn">立即咨询</button>
              </div>
            );
          })}
        </div>
      </div>
      <div className="carousel-dots">
        {doctors.map((_, i) => (
          <div
            key={i}
            className={`carousel-dot ${i === activeIndex ? 'active' : ''}`}
            onClick={() => goTo(i)}
          />
        ))}
      </div>
      <div className="carousel-learn-more" onClick={() => onNavigate('detect')}>
        <span>了解更多</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </div>
  );
};

export default DoctorCarousel;
