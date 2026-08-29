import React, { useEffect, useRef, useState } from 'react';

/* ================================================================
   SkinAgingSection — 皮肤衰老分级诊断模块
   区块 A：认知建立（衰老等级卡片）
   区块 B：技术介绍（AI检测 + 专家研发 + 大数据验证）
   区块 C：信任背书 + 行动召唤
   ================================================================ */

// ---- 区块A：四个衰老等级数据 ----
const AGING_LEVELS = [
  { level: 'Ⅰ级', name: '轻度老化', desc: '细纹初现、轻微色斑', color: '#4DA8DA', img: './picture/等级1.png' },
  { level: 'Ⅱ级', name: '中度老化', desc: '明显纹路、皮肤暗沉', color: '#2E86C1', img: './picture/等级2.png' },
  { level: 'Ⅲ级', name: '重度老化', desc: '深层皱纹、色斑扩散', color: '#1B3A6E', img: './picture/等级3.png' },
  { level: 'Ⅳ级', name: '极重度老化', desc: '严重松弛、深度老化', color: '#0D1E3A', img: './picture/等级4.png' },
];

// ---- 区块B-2：合作机构节点（环形布局）----
const PARTNER_INSTITUTIONS = [
  { name: '上海交通大学\n医学院附属医院', x: '50%', y: '18%' },
  { name: '重庆医科大学\n第三医院', x: '25%', y: '30%' },
  { name: '北京协和医院', x: '75%', y: '30%' },
  { name: '昆明医科大学\n一附属医院', x: '25%', y: '60%' },
  { name: '第四军医大学\n西京医院', x: '75%', y: '60%' },
  { name: '上海皮肤病医院', x: '50%', y: '80%' },
];

// ---- 六所合作医院各自独立图标 ----
const HOSPITAL_ICONS = [
  /* 0 上海交通大学医学院附属医院 — 学术殿堂 */
  <svg key="h0" width="22" height="22" viewBox="0 0 24 24" fill="none">
    <path d="M12 2L3 7v5c0 4.4 3.6 8 9 10 5.4-2 9-5.6 9-10V7l-9-5z" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" strokeLinejoin="round"/>
    <path d="M8 10l3 3 5-5" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>,
  /* 1 重庆医科大学第三医院 — 医学十字 */
  <svg key="h1" width="22" height="22" viewBox="0 0 24 24" fill="none">
    <rect x="8" y="2" width="8" height="20" rx="3" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none"/>
    <rect x="2" y="8" width="20" height="8" rx="3" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none"/>
    <circle cx="12" cy="12" r="2" fill="rgba(255,255,255,0.4)"/>
  </svg>,
  /* 2 北京协和医院 — 盾牌认证 */
  <svg key="h2" width="22" height="22" viewBox="0 0 24 24" fill="none">
    <path d="M12 2L4 5v6c0 5.5 3.8 10.7 8 12 4.2-1.3 8-6.5 8-12V5l-8-3z" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" strokeLinejoin="round"/>
    <circle cx="12" cy="11" r="3" stroke="rgba(255,255,255,0.6)" strokeWidth="1.2" fill="none"/>
    <path d="M12 8v6M9 11h6" stroke="rgba(255,255,255,0.6)" strokeWidth="1" strokeLinecap="round"/>
  </svg>,
  /* 3 昆明医科大学一附属医院 — 基因健康 */
  <svg key="h3" width="22" height="22" viewBox="0 0 24 24" fill="none">
    <path d="M7 3C4.5 6.5 4.5 17.5 7 21" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
    <path d="M17 3C19.5 6.5 19.5 17.5 17 21" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
    <path d="M9 9h6M9 13h6M9 17h6" stroke="rgba(255,255,255,0.55)" strokeWidth="1" strokeLinecap="round"/>
  </svg>,
  /* 4 第四军医大学西京医院 — 军医之星 */
  <svg key="h4" width="22" height="22" viewBox="0 0 24 24" fill="none">
    <polygon points="12,1.5 15.5,8.5 23,9.5 17.5,15 19,22.5 12,18.5 5,22.5 6.5,15 1,9.5 8.5,8.5" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" strokeLinejoin="round"/>
    <circle cx="12" cy="12" r="2.5" fill="rgba(255,255,255,0.35)"/>
  </svg>,
  /* 5 上海皮肤病医院 — 皮肤专科 */
  <svg key="h5" width="22" height="22" viewBox="0 0 24 24" fill="none">
    <circle cx="8.5" cy="8" r="3.5" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none"/>
    <circle cx="15.5" cy="10" r="3.5" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none"/>
    <circle cx="9" cy="17" r="3.5" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none"/>
    <circle cx="8.5" cy="8" r="1" fill="rgba(255,255,255,0.4)"/>
    <circle cx="15.5" cy="10" r="1" fill="rgba(255,255,255,0.4)"/>
    <circle cx="9" cy="17" r="1" fill="rgba(255,255,255,0.4)"/>
  </svg>,
];

// ---- 区块B-3：高校科研合作图谱 ----
const UNIVERSITY_NODES = [
  { name: '北京大学', img: './picture/pku.png', size: 90, isCenter: true, imgScale: 115 },
  { name: '清华大学', img: './picture/tsinghua.png', size: 56, imgScale: 120 },
  { name: '上海交通大学', img: './picture/sjtu.png', size: 56, imgScale: 100 },
  { name: '华中科技大学', img: './picture/hust.png', size: 56, imgScale: 100 },
  { name: '耶鲁大学', img: './picture/yale.png', size: 56, imgScale: 120 },
];

// ---- 科研/医疗功能图标生成器（白色主题）----
const FUNC_ICON_SVGS = {
  dna: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M7 3C4.5 6.5 4.5 17.5 7 21" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M17 3c2.5 3.5 2.5 14.5 0 18" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="9" y1="7" x2="15" y2="7" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
      <line x1="9" y1="11" x2="15" y2="11" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
      <line x1="9" y1="15" x2="15" y2="15" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
    </svg>
  ),
  beaker: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M8 2v5l-4 13c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2l-4-13V2" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinejoin="round"/>
      <line x1="8" y1="7" x2="16" y2="7" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
      <circle cx="10" cy="15" r="2.5" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.55)" strokeWidth="1"/>
      <circle cx="14" cy="13" r="1.5" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.45)" strokeWidth="0.8"/>
    </svg>
  ),
  ai: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="3" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <path d="M7 12h10M12 7v10" stroke="rgba(255,255,255,0.55)" strokeWidth="1.2" strokeLinecap="round"/>
      <circle cx="12" cy="12" r="2" fill="rgba(255,255,255,0.15)"/>
      <circle cx="18" cy="6" r="1.2" fill="rgba(255,255,255,0.25)"/>
    </svg>
  ),
  data: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="16" width="5" height="6" rx="1" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <rect x="9.5" y="10" width="5" height="12" rx="1" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <rect x="17" y="4" width="5" height="18" rx="1" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
    </svg>
  ),
  medical: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="8" y="2" width="8" height="20" rx="3" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <rect x="2" y="8" width="20" height="8" rx="3" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <circle cx="12" cy="12" r="1.5" fill="rgba(255,255,255,0.2)"/>
    </svg>
  ),
  microscope: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="10" cy="10" r="5" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <path d="M15 15l5 5" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round"/>
      <line x1="3" y1="22" x2="16" y2="22" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="10" cy="10" r="2" fill="rgba(255,255,255,0.15)"/>
    </svg>
  ),
  globe: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5"/>
      <ellipse cx="12" cy="12" rx="4" ry="9" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
      <line x1="3" y1="12" x2="21" y2="12" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
      <path d="M6 6c2 2 4 3 6 3s4-1 6-3M6 18c2-2 4-3 6-3s4 1 6 3" stroke="rgba(255,255,255,0.45)" strokeWidth="0.8"/>
    </svg>
  ),
  book: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M4 3h6c2 0 2 2 2 2v14s0-2-2-2H4V3z" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M20 3h-6c-2 0-2 2-2 2v14s0-2 2-2h6V3z" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinejoin="round"/>
      <line x1="12" y1="8" x2="12" y2="15" stroke="rgba(255,255,255,0.4)" strokeWidth="0.8"/>
    </svg>
  ),
};

// ================================================================
// 子组件
// ================================================================

/** 进入视口动画 Hook */
const useInView = (threshold = 0.25) => {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setInView(true); obs.disconnect(); } }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, inView];
};

/** 步骤编号组件 */
const StepNumber = ({ num, inView: visible }) => (
  <div className="sa-step-num">
    <span className={`sa-step-num-text ${visible ? 'sa-step-num--animated' : ''}`}>{String(num).padStart(2, '0')}</span>
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="sa-step-arrow">
      <path d="M2 1L8 5L2 9" fill="#F0C040" />
    </svg>
  </div>
);

// ================================================================
// 主组件
// ================================================================
const SkinAgingSection = ({ onNavigate }) => {
  const [refA, inViewA] = useInView(0.2);
  const [refB, inViewB] = useInView(0.15);
  const [refC, inViewC] = useInView(0.2);

  // 动态生成高校周边元素图标（随机1~3个，挂载时确定一次）
  const elementIconsData = React.useMemo(() => {
    const iconKeys = ['dna', 'beaker', 'ai', 'data', 'medical', 'microscope', 'globe', 'book'];

    // 4 所合作高校的位置及可选元素图标点位（SVG viewBox 320×280）
    // CSS% → SVG: x = % * 3.2, y = % * 2.8
    const partnerConfigs = [
      {
        // 清华大学 — 顶部  CSS(50%,17%) → SVG(160,48)
        uniIdx: 0,
        partnerSvg: { x: 160, y: 48 },
        iconOptions: [
          { x: '28%', y: '7%',  svg: { x: 90, y: 20 } },
          { x: '63%', y: '7%',  svg: { x: 202, y: 20 } },
        ],
      },
      {
        // 上海交通大学 — 右侧  CSS(84%,50%) → SVG(269,140)
        uniIdx: 1,
        partnerSvg: { x: 269, y: 140 },
        iconOptions: [
          { x: '93%', y: '39%', svg: { x: 298, y: 109 } },
          { x: '93%', y: '61%', svg: { x: 298, y: 171 } },
          { x: '93%', y: '50%', svg: { x: 298, y: 140 } },
        ],
      },
      {
        // 华中科技大学 — 底部  CSS(50%,82%) → SVG(160,230)
        uniIdx: 2,
        partnerSvg: { x: 160, y: 230 },
        iconOptions: [
          { x: '39%', y: '91%', svg: { x: 125, y: 255 } },
          { x: '61%', y: '91%', svg: { x: 195, y: 255 } },
          { x: '50%', y: '95%', svg: { x: 160, y: 266 } },
        ],
      },
      {
        // 耶鲁大学 — 左侧  CSS(16%,50%) → SVG(51,140)
        uniIdx: 3,
        partnerSvg: { x: 51, y: 140 },
        iconOptions: [
          { x: '7%',  y: '39%', svg: { x: 22, y: 109 } },
          { x: '7%',  y: '61%', svg: { x: 22, y: 171 } },
          { x: '7%',  y: '50%', svg: { x: 22, y: 140 } },
        ],
      },
    ];

    return partnerConfigs.map((cfg) => {
      const seed = cfg.uniIdx * 7 + 13;
      const count = (seed % 3) + 1; // 1~3 个元素图标
      const selected = [];
      const usedKeys = new Set();
      const usedPos = new Set();

      for (let j = 0; j < count; j++) {
        let keyIdx = (seed * (j + 1) * 5) % iconKeys.length;
        let key = iconKeys[keyIdx];
        if (usedKeys.has(key)) key = iconKeys[(keyIdx + j) % iconKeys.length];
        usedKeys.add(key);

        let posIdx = (seed + j * 3) % cfg.iconOptions.length;
        if (usedPos.has(posIdx)) posIdx = (posIdx + 1) % cfg.iconOptions.length;
        usedPos.add(posIdx);

        const pos = cfg.iconOptions[posIdx];
        selected.push({ key, x: pos.x, y: pos.y, svg: pos.svg });
      }

      return {
        uniIdx: cfg.uniIdx,
        partnerSvg: cfg.partnerSvg,
        icons: selected,
      };
    });
  }, []);

  // 外围节点 CSS 位置（4 所合作高校）
  const UNI_POSITIONS = [
    { x: '50%', y: '17%' },  // 清华大学 — 顶部
    { x: '84%', y: '50%' },  // 上海交通大学 — 右侧
    { x: '50%', y: '82%' },  // 华中科技大学 — 底部
    { x: '16%', y: '50%' },  // 耶鲁大学 — 左侧
  ];

  return (
    <div className="skin-aging-section">
      {/* ==================== 区块A：认知建立 ==================== */}
      <div className="sa-block sa-block-a" ref={refA}>
        {/* A-1 标题区 */}
        <div className={`sa-title-group ${inViewA ? 'sa-fade-in' : ''}`}>
          <h2 className="sa-main-title">
            皮肤衰老要先明确衰老<span className="sa-gold">【等级】</span>
          </h2>
          <p className="sa-desc-text">
            根据《国际皮肤光老化分级标准》将皮肤衰老划分为四个等级
          </p>
        </div>

        {/* A-2 衰老等级卡片列 */}
        <div className="sa-level-scroll">
          {AGING_LEVELS.map((item, i) => (
            <div
              key={item.level}
              className={`sa-level-card ${inViewA ? 'sa-fade-in-up' : ''}`}
              style={{ '--delay': `${i * 80}ms`, '--card-color': item.color }}
            >
              <span className="sa-level-tag" style={{ color: '#F0C040' }}>{item.level}</span>
              <div className="sa-level-illus">
                <img src={item.img} alt={item.level} className="sa-level-img" />
              </div>
              <span className="sa-level-name">{item.name}</span>
              <span className="sa-level-desc">{item.desc}</span>
            </div>
          ))}
        </div>

        {/* 底部说明 */}
        <p className={`sa-note-text ${inViewA ? 'sa-fade-in' : ''}`} style={{ '--delay': '400ms' }}>
          国际公认 Glogau 光老化分级体系，科学量化皮肤衰老程度
        </p>
      </div>

      {/* ==================== 区块B：技术介绍 ==================== */}
      <div className="sa-block sa-block-b" ref={refB}>
        {/* B-0 区块大标题 */}
        <div className={`sa-title-group ${inViewB ? 'sa-fade-in' : ''}`}>
          <h2 className="sa-main-title sa-main-title--sm">
            因此我们研创<span className="sa-gold">AI衰老检测</span>技术
          </h2>
        </div>

        {/* B-1 步骤01：AI测肤 */}
        <div className={`sa-step-block ${inViewB ? 'sa-fade-in' : ''}`} style={{ '--delay': '100ms' }}>
          <div className="sa-step-header">
            <StepNumber num={1} inView={inViewB} />
            <span className="sa-step-title">AI测肤 | <span style={{ fontWeight: 400, opacity: 0.8 }}>2分钟即可出具衰老诊断报告</span></span>
          </div>

          {/* 模块示意图 */}
          <div className="sa-demo-image-wrap">
            <img src="./picture/模块图.png" alt="AI测肤模块示意" className="sa-demo-image" />
          </div>
        </div>

        {/* B-2 步骤02：专家联合研发 */}
        <div className={`sa-step-block ${inViewB ? 'sa-fade-in' : ''}`} style={{ '--delay': '200ms' }}>
          <div className="sa-step-header">
            <StepNumber num={2} inView={inViewB} />
            <span className="sa-step-title">皮肤科专家领衔研发 | <span style={{ fontWeight: 400, opacity: 0.8 }}>以医学角度诊断皮肤衰老</span></span>
          </div>

          {/* 机构网络图（环形布局） */}
          <div className="sa-network-graph">
            {/* 背景底图 */}
            <div className="sa-network-bg" />
            {/* 连接线与装饰环 */}
            <svg className="sa-network-lines" viewBox="0 0 320 280" preserveAspectRatio="none">
              {/* 装饰环形轨道 */}
              <circle cx="160" cy="123" r="94" stroke="rgba(255,255,255,0.15)" strokeWidth="1" strokeDasharray="5 8" fill="none" />
              <circle cx="160" cy="123" r="66" stroke="rgba(255,255,255,0.10)" strokeWidth="0.5" strokeDasharray="3 6" fill="none" />
              {/* 连线（白亮） */}
              <line x1="160" y1="123" x2="160" y2="50" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 3" />
              <line x1="160" y1="123" x2="240" y2="84" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 3" />
              <line x1="160" y1="123" x2="240" y2="168" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 3" />
              <line x1="160" y1="123" x2="160" y2="224" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 3" />
              <line x1="160" y1="123" x2="80" y2="168" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 3" />
              <line x1="160" y1="123" x2="80" y2="84" stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 3" />
            </svg>
            {/* 机构节点 */}
            {PARTNER_INSTITUTIONS.map((inst, i) => (
              <div key={i} className={`sa-net-node sa-net-node--inst ${inViewB ? 'sa-node-appear' : ''}`}
                style={{ left: inst.x, top: inst.y, '--delay': `${300 + i * 100}ms` }}>
                <div className="sa-net-dot">
                  {HOSPITAL_ICONS[i]}
                </div>
                <span className="sa-net-label">{inst.name.split('\n').map((l, j) => <span key={j}>{l}<br /></span>)}</span>
              </div>
            ))}
            {/* 中心节点 */}
            <div className={`sa-net-node sa-net-node--center ${inViewB ? 'sa-node-appear' : ''}`}
              style={{ left: '50%', top: '44%', '--delay': '900ms' }}>
              <div className="sa-net-dot sa-net-dot--gold">
                <svg width="34" height="34" viewBox="0 0 28 28" fill="none">
                  <circle cx="14" cy="14" r="12" fill="url(#goldGrad)" />
                  <text x="14" y="18.5" textAnchor="middle" fontSize="11" fontWeight="bold" fill="white">兰</text>
                  <defs>
                    <linearGradient id="goldGrad" x1="0" y1="0" x2="28" y2="28">
                      <stop stopColor="#F0C040" /><stop offset="1" stopColor="#D4A843" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <span className="sa-net-label sa-net-label--gold">兰峤AI研究院</span>
            </div>
          </div>
        </div>

        {/* B-3 步骤03：算法大数据验证 */}
        <div className={`sa-step-block ${inViewB ? 'sa-fade-in' : ''}`} style={{ '--delay': '300ms' }}>
          <div className="sa-step-header">
            <StepNumber num={3} inView={inViewB} />
            <span className="sa-step-title">算法团队筛选百万数据 | <span style={{ fontWeight: 400, opacity: 0.8 }}>定制精准皮肤衰老诊断报告</span></span>
          </div>

          {/* 高校科研合作可视化图谱 */}
          <div className="sa-uni-collab">
            {/* 装饰背景微网格 */}
            <div className="sa-uni-bg-grid" />
            {/* 连线层 */}
            <svg className="sa-uni-lines" viewBox="0 0 320 280" preserveAspectRatio="none">
              {/* 科技感装饰环 */}
              <circle cx="160" cy="140" r="102" stroke="rgba(255,255,255,0.08)" strokeWidth="0.8" strokeDasharray="3 7" fill="none" />
              <circle cx="160" cy="140" r="74" stroke="rgba(255,255,255,0.12)" strokeWidth="0.6" strokeDasharray="2 5" fill="none" />
              <circle cx="160" cy="140" r="48" stroke="rgba(240,192,64,0.15)" strokeWidth="0.8" strokeDasharray="3 4" fill="none" />

              {/* 中心到各合作高校连线 */}
              {elementIconsData.map((item) => (
                <line key={`radial-${item.uniIdx}`}
                  x1="160" y1="140"
                  x2={item.partnerSvg.x} y2={item.partnerSvg.y}
                  stroke="rgba(255,255,255,0.3)" strokeWidth="1.2" strokeDasharray="4 4" />
              ))}

              {/* 环形连线：清华 → 上海交大 → 华中科技 → 耶鲁 → 清华 */}
              {elementIconsData.map((item, i) => {
                const next = elementIconsData[(i + 1) % elementIconsData.length];
                return (
                  <line key={`ring-${i}`}
                    x1={item.partnerSvg.x} y1={item.partnerSvg.y}
                    x2={next.partnerSvg.x} y2={next.partnerSvg.y}
                    stroke="rgba(255,255,255,0.22)" strokeWidth="1" strokeDasharray="3 5" />
                );
              })}

              {/* 高校到元素图标的连线 */}
              {elementIconsData.map((item) =>
                item.icons.map((ico, j) => (
                  <line key={`elem-${item.uniIdx}-${j}`}
                    x1={item.partnerSvg.x} y1={item.partnerSvg.y}
                    x2={ico.svg.x} y2={ico.svg.y}
                    stroke="rgba(255,255,255,0.28)" strokeWidth="0.9" strokeDasharray="2 3" />
                ))
              )}
            </svg>

            {/* 合作高校节点（纯图标） */}
            {UNIVERSITY_NODES.filter(u => !u.isCenter).map((uni, i) => (
              <div key={i}
                className={`sa-uni-partner ${inViewB ? 'sa-node-appear' : ''}`}
                style={{ left: UNI_POSITIONS[i].x, top: UNI_POSITIONS[i].y, '--delay': `${300 + i * 120}ms` }}>
                <div className="sa-uni-partner-dot">
                  {uni.img ? (
                    <img src={uni.img} alt={uni.name} className="sa-uni-partner-img"
                      style={{ width: `${uni.imgScale}%`, height: `${uni.imgScale}%` }} />
                  ) : (
                    <span className="sa-uni-partner-text">{uni.name}</span>
                  )}
                </div>
              </div>
            ))}

            {/* 中心节点：北京大学 */}
            <div className={`sa-uni-center ${inViewB ? 'sa-node-appear' : ''}`}
              style={{ left: '50%', top: '50%', '--delay': '600ms' }}>
              <div className="sa-uni-center-ring sa-uni-center-ring--outer" />
              <div className="sa-uni-center-ring sa-uni-center-ring--inner" />
              <div className="sa-uni-center-dot">
                <img src="./picture/pku.png" alt="北京大学" className="sa-uni-center-img"
                  style={{ width: '115%', height: '115%' }} />
              </div>
            </div>

            {/* 各高校周边的元素图标（动态数量） */}
            {elementIconsData.map((group) =>
              group.icons.map((ico, j) => (
                <div key={`${group.uniIdx}-${j}`}
                  className={`sa-uni-func ${inViewB ? 'sa-func-appear' : ''}`}
                  style={{ left: ico.x, top: ico.y, '--delay': `${700 + group.uniIdx * 150 + j * 80}ms` }}>
                  <div className="sa-uni-func-dot">
                    {FUNC_ICON_SVGS[ico.key]}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* 数据背书文字 */}
          <div className={`sa-cert-block ${inViewB ? 'sa-fade-in' : ''}`} style={{ '--delay': '1000ms' }}>
            <div className="sa-cert-item">
              <div className="sa-cert-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="#4DA8DA" strokeWidth="1.5" />
                  <path d="M8 12l3 3 5-5" stroke="#4DA8DA" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div className="sa-cert-text">
                <p>检测结果经过全国<span className="sa-cert-highlight">9个省份14家</span>三甲医院临床研究认证</p>
              </div>
            </div>
            <div className="sa-cert-item">
              <div className="sa-cert-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="#4DA8DA" strokeWidth="1.5" />
                  <path d="M12 7v5l3 3" stroke="#4DA8DA" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </div>
              <div className="sa-cert-text">
                <p>准确度获<span className="sa-cert-highlight">30年资质医生</span>认可</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== 区块C：信任背书 + 行动召唤 ==================== */}
      <div className="sa-block sa-block-c" ref={refC}>
        {/* C-1 行动按钮 */}
        <button
          className={`sa-cta-btn ${inViewC ? 'sa-cta--visible' : ''}`}
          onClick={() => onNavigate('detect')}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" style={{ marginRight: 6 }}>
            <path d="M4 2L14 9L4 16" fill="white" />
          </svg>
          立即检测皮肤
        </button>

        {/* C-2 过渡标题 */}
        <p className={`sa-transition-title ${inViewC ? 'sa-fade-in' : ''}`}>
          依据诊断结果出具个性化治疗方案
        </p>
      </div>
    </div>
  );
};

export default SkinAgingSection;
