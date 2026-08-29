import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';

/**
 * 模拟在线咨询用户数据 — 三组不重复
 */
const MOCK_USERS_ROW1 = [
  { nickname: '张女士', avatar: '👩🏻' },
  { nickname: '李先生', avatar: '👨🏻' },
  { nickname: '王女士', avatar: '👩🏼' },
  { nickname: '赵先生', avatar: '👨🏼' },
  { nickname: '刘女士', avatar: '👩' },
  { nickname: '陈先生', avatar: '👨' },
  { nickname: '杨女士', avatar: '👩🏽' },
  { nickname: '黄女士', avatar: '👩🏻' },
  { nickname: '周先生', avatar: '👨🏽' },
  { nickname: '吴女士', avatar: '👩🏼' },
  { nickname: '郑先生', avatar: '👨🏻' },
  { nickname: '孙女士', avatar: '👩' },
];

const MOCK_USERS_ROW2 = [
  { nickname: '朱先生', avatar: '👨🏼' },
  { nickname: '马女士', avatar: '👩🏽' },
  { nickname: '胡先生', avatar: '👨' },
  { nickname: '林女士', avatar: '👩🏻' },
  { nickname: '何先生', avatar: '👨🏽' },
  { nickname: '郭女士', avatar: '👩🏼' },
  { nickname: '罗先生', avatar: '👨🏻' },
  { nickname: '梁女士', avatar: '👩' },
  { nickname: '宋先生', avatar: '👨🏼' },
  { nickname: '唐女士', avatar: '👩🏻' },
  { nickname: '韩先生', avatar: '👨' },
  { nickname: '冯女士', avatar: '👩🏽' },
];

const MOCK_USERS_ROW3 = [
  { nickname: '曹先生', avatar: '👨🏻' },
  { nickname: '彭女士', avatar: '👩🏼' },
  { nickname: '曾先生', avatar: '👨🏽' },
  { nickname: '肖女士', avatar: '👩' },
  { nickname: '田先生', avatar: '👨🏼' },
  { nickname: '董女士', avatar: '👩🏻' },
  { nickname: '潘先生', avatar: '👨' },
  { nickname: '袁女士', avatar: '👩🏽' },
  { nickname: '蔡先生', avatar: '👨🏻' },
  { nickname: '蒋女士', avatar: '👩🏼' },
  { nickname: '余先生', avatar: '👨🏽' },
  { nickname: '杜女士', avatar: '👩' },
];

/**
 * 翻牌数字组件 — 单个数字位
 */
const FlipDigit = ({ digit, prevDigit, flipping }) => {
  return (
    <div className="flip-digit-wrapper">
      <div className={`flip-digit-card ${flipping ? 'flip-digit--flipping' : ''}`}>
        <div className="flip-digit-face flip-digit-face--front">
          <span>{prevDigit}</span>
        </div>
        <div className="flip-digit-face flip-digit-face--back">
          <span>{digit}</span>
        </div>
      </div>
    </div>
  );
};

/**
 * 翻牌数字计数器 — 6 位数字
 * 第一阶段：0 → 500000，easeOutCubic 缓动，约 3 秒
 * 第二阶段：500001 → 500020，极其缓慢递增（每 4 秒 +1），到 500020 停止
 */
const FlipCounter = ({ value, animate }) => {
  const [displayDigits, setDisplayDigits] = useState([]);
  const [prevDigits, setPrevDigits] = useState([]);
  const [flippingMask, setFlippingMask] = useState([]);
  const animFrameRef = useRef(null);
  const slowTimerRef = useRef(null);
  const startTimeRef = useRef(null);
  const currentSlowValueRef = useRef(0);
  const DURATION_FAST = 3000;               // 快速阶段：3 秒冲到 500000
  const TARGET_FAST = 500000;
  const SLOW_INCREMENT_INTERVAL = 4000;     // 慢速阶段：每 4 秒 +1
  const SLOW_MAX = 500020;

  const len = String(value).length;

  const pad = useCallback((v) => String(Math.floor(v)).padStart(len, '0'), [len]);

  useEffect(() => {
    if (!animate || value <= 0) return;

    startTimeRef.current = null;
    currentSlowValueRef.current = TARGET_FAST;

    const initialDigits = pad(0).split('');
    setDisplayDigits(initialDigits);
    setPrevDigits(initialDigits);
    setFlippingMask(Array(len).fill(false));

    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

    // ===== 第一阶段：快速冲到 500000 =====
    const animateFast = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / DURATION_FAST, 1);
      const easedProgress = easeOutCubic(progress);

      const currentVal = Math.floor(easedProgress * TARGET_FAST);
      const currentStr = pad(currentVal);
      const digits = currentStr.split('');

      setDisplayDigits((prev) => {
        const newMask = Array(len).fill(false);
        digits.forEach((d, i) => {
          if (d !== prev[i]) newMask[i] = true;
        });
        setPrevDigits(prev);
        setFlippingMask(newMask);
        return digits;
      });

      if (progress < 1) {
        animFrameRef.current = requestAnimationFrame(animateFast);
      } else {
        setDisplayDigits(pad(TARGET_FAST).split(''));
        setPrevDigits(pad(TARGET_FAST).split(''));
        setFlippingMask(Array(len).fill(false));
        startSlowPhase();
      }
    };

    // ===== 第二阶段：极其缓慢地递增到 500020 停止 =====
    const startSlowPhase = () => {
      const tickSlow = () => {
        currentSlowValueRef.current += 1;
        const newVal = currentSlowValueRef.current;
        const newStr = pad(newVal);
        const digits = newStr.split('');

        setDisplayDigits((prev) => {
          const newMask = Array(len).fill(false);
          digits.forEach((d, i) => {
            if (d !== prev[i]) newMask[i] = true;
          });
          setPrevDigits(prev);
          setFlippingMask(newMask);
          return digits;
        });

        if (currentSlowValueRef.current < SLOW_MAX) {
          slowTimerRef.current = setTimeout(tickSlow, SLOW_INCREMENT_INTERVAL);
        }
      };

      slowTimerRef.current = setTimeout(tickSlow, SLOW_INCREMENT_INTERVAL);
    };

    animFrameRef.current = requestAnimationFrame(animateFast);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (slowTimerRef.current) clearTimeout(slowTimerRef.current);
    };
  }, [animate, value, pad]);

  useEffect(() => {
    if (flippingMask.some(Boolean)) {
      const timer = setTimeout(() => {
        setPrevDigits(displayDigits);
        setFlippingMask(Array(displayDigits.length).fill(false));
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [flippingMask, displayDigits]);

  return (
    <div className="flip-counter">
      {displayDigits.map((digit, i) => (
        <FlipDigit
          key={i}
          digit={digit}
          prevDigit={prevDigits[i] || digit}
          flipping={flippingMask[i]}
        />
      ))}
    </div>
  );
};

/**
 * 跑马灯用户动态标签 — 单行
 */
const MarqueeRow = ({ users, speed, direction = 'normal' }) => {
  const shuffled = useMemo(() => {
    const arr = [...users];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }, [users]);

  const doubled = useMemo(() => [...shuffled, ...shuffled], [shuffled]);

  return (
    <div className="marquee-track-wrapper">
      <div
        className="marquee-track"
        style={{
          '--marquee-speed': `${speed}s`,
          animationDirection: direction,
        }}
      >
        {doubled.map((user, i) => (
          <div key={i} className="marquee-tag">
            <span className="marquee-tag-avatar">{user.avatar}</span>
            <span className="marquee-tag-nickname">{user.nickname}</span>
            <span className="marquee-tag-status">正在咨询</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 虚幻装饰元素 — 填充数字周围空白
 */
const FloatingDecorations = () => (
  <div className="flip-decorations" aria-hidden="true">
    {/* 柔和光晕 */}
    <div className="flip-deco-orb flip-deco-orb--1"></div>
    <div className="flip-deco-orb flip-deco-orb--2"></div>
    <div className="flip-deco-orb flip-deco-orb--3"></div>
    {/* 细小光点 */}
    <div className="flip-deco-dot flip-deco-dot--1"></div>
    <div className="flip-deco-dot flip-deco-dot--2"></div>
    <div className="flip-deco-dot flip-deco-dot--3"></div>
    <div className="flip-deco-dot flip-deco-dot--4"></div>
    <div className="flip-deco-dot flip-deco-dot--5"></div>
    {/* 淡色圆环 */}
    <div className="flip-deco-ring flip-deco-ring--1"></div>
    <div className="flip-deco-ring flip-deco-ring--2"></div>
    {/* 十字星 */}
    <div className="flip-deco-star flip-deco-star--1"></div>
    <div className="flip-deco-star flip-deco-star--2"></div>
  </div>
);

/**
 * 数据统计模块
 */
const Statistics = () => {
  const [animated, setAnimated] = useState(false);
  const sectionRef = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setAnimated(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  const TARGET_VALUE = 500020;

  return (
    <div className="stats-section-v2" ref={sectionRef}>
      {/* 顶部引导语 */}
      <p className="stats-section-v2-header">皮肤用户已得到改善</p>

      {/* 核心数据统计区 — 翻牌数字卡片（含虚幻装饰） */}
      <div className="stats-flip-card">
        <FloatingDecorations />
        <div className="stats-flip-value-row">
          {animated ? (
            <FlipCounter value={TARGET_VALUE} animate={animated} />
          ) : (
            <span className="stats-flip-placeholder">500000</span>
          )}
          <span className="stats-flip-plus">+</span>
        </div>
      </div>

      {/* 用户动态区 — 三行不规律跑马灯 */}
      <div className="stats-marquee-section">
        <MarqueeRow users={MOCK_USERS_ROW1} speed={32} direction="normal" />
        <MarqueeRow users={MOCK_USERS_ROW2} speed={38} direction="reverse" />
        <MarqueeRow users={MOCK_USERS_ROW3} speed={28} direction="normal" />
      </div>
    </div>
  );
};

export default Statistics;
