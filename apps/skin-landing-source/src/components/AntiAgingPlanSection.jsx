import React, { useEffect, useRef, useState } from 'react';

/* ================================================================
   AntiAgingPlanSection — 依据诊断结果出具抗衰方案
   模块 1：页面标题区
   模块 2：专家团队与诊断报告区
   模块 3：定制抗衰方案区（医/妆/养）
   ================================================================ */

// ---- 专家团图片路径 ----
const EXPERT_IMG_1 = './picture/专家团1.jpg';
const EXPERT_IMG_2 = './picture/专家团2.jpg';
const EXPERT_IMG_3 = './picture/专家团3.jpg';

// ---- 方案维度数据 (医/妆/养) ----
const PLAN_DIMENSIONS = [
  {
    key: 'medical',
    label: '医',
    title: '医疗级抗衰方案',
    desc: '如射频/光子项目',
    items: ['医用抗衰药膏', '光电项目', '注射填充方案'],
    color: '#0A2463',
  },
  {
    key: 'cosmetic',
    label: '妆',
    title: '功效型抗衰护肤品',
    desc: '如A醇/玻色因精华',
    items: ['抗衰精华', '修复面霜', '安瓶浓缩液'],
    color: '#1E3A8A',
  },
  {
    key: 'nutrition',
    label: '养',
    title: '内调抗衰营养方案',
    desc: '如胶原蛋白/抗衰膳食',
    items: ['胶原蛋白口服液', '营养粉', '抗衰食品'],
    color: '#2E86C1',
  },
];

// ---- 进入视口动画 Hook ----
const useInView = (threshold = 0.2) => {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setInView(true);
          obs.disconnect();
        }
      },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, inView];
};

// ================================================================
// 子组件
// ================================================================

/** 印章组件 */
const RedSeal = () => (
  <div className="aap-seal">
    <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
      <circle cx="36" cy="36" r="34" stroke="#D92B2B" strokeWidth="2.5" fill="none" />
      <circle cx="36" cy="36" r="30" stroke="#D92B2B" strokeWidth="0.8" fill="none" strokeDasharray="2 3" />
      <text x="36" y="27" textAnchor="middle" fontSize="8" fontWeight="700" fill="#D92B2B">皮肤检测</text>
      <text x="36" y="39" textAnchor="middle" fontSize="7" fontWeight="600" fill="#D92B2B">专 用 章</text>
      <text x="36" y="52" textAnchor="middle" fontSize="6" fill="#D92B2B">皮肤科</text>
    </svg>
  </div>
);

/** 盾牌图标 */
const ShieldIcon = () => (
  <svg width="12" height="14" viewBox="0 0 12 14" fill="none" style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: 4 }}>
    <path d="M6 1L1 3v4.5c0 2.8 2.2 5.2 5 5.5 2.8-.3 5-2.7 5-5.5V3L6 1z" stroke="#D4A843" strokeWidth="1.2" fill="none" />
    <path d="M4 6.5l1.5 1.5 2.5-3" stroke="#D4A843" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" fill="none" />
  </svg>
);

/** 对勾图标 */
const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: 4 }}>
    <circle cx="7" cy="7" r="6" fill="#27AE60" />
    <path d="M4 7l2 2 4-4" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
  </svg>
);

/** 方案维度箭头 */
const PlanArrow = () => (
  <div className="aap-plan-arrow-wrap">
    <svg className="aap-plan-arrow-svg" width="100%" height="40" viewBox="0 0 200 40" preserveAspectRatio="none">
      <defs>
        <pattern id="dotPattern" patternUnits="userSpaceOnUse" width="6" height="6">
          <circle cx="3" cy="3" r="1" fill="#B0C4D8" opacity="0.5" />
        </pattern>
      </defs>
      {/* 虚线箭头主体 */}
      <line x1="10" y1="20" x2="170" y2="20" stroke="#4DA8DA" strokeWidth="1.5" strokeDasharray="6 4" />
      {/* 箭头尖 */}
      <polygon points="185,20 172,13 172,27" fill="#4DA8DA" />
      {/* 点阵填充 */}
      <rect x="10" y="8" width="170" height="24" fill="url(#dotPattern)" opacity="0.4" />
    </svg>
  </div>
);

// ================================================================
// 主组件
// ================================================================
const AntiAgingPlanSection = ({ onNavigate }) => {
  const [ref1, inView1] = useInView(0.15);
  const [ref2, inView2] = useInView(0.15);
  const [ref3, inView3] = useInView(0.15);

  return (
    <div className="anti-aging-plan-section">
      {/* ==================== 模块 1：页面标题区 ==================== */}
      <div className={`aap-title-section ${inView1 ? 'aap-visible' : ''}`} ref={ref1}>
        <h1 className="aap-main-title">依据皮肤衰老诊断结果出具抗衰方案</h1>
        <p className="aap-sub-title-en">ANTI-AGING PLAN BASED ON DIAGNOSTIC RESULTS</p>
        <div className="aap-title-divider"></div>
      </div>

      {/* ==================== 模块 2：专家团队与诊断报告区 ==================== */}
      <div className={`aap-report-section ${inView2 ? 'aap-visible' : ''}`} ref={ref2}>

        {/* ---- 2-1 专家团队展示卡片 ---- */}
        <div className="aap-expert-card">
          <div className="aap-expert-card-bg"></div>
          <div className="aap-expert-left">
            <h3 className="aap-expert-title">「皮肤抗衰」专家团</h3>
            <p className="aap-expert-subtitle">已累计服务 500,000 + 皮肤衰老管理用户</p>
            <div className="aap-expert-badge">
              <ShieldIcon />
              国家卫健委认证皮肤科医生
            </div>
            {/* 移动端医生展示 */}
            <div className="aap-expert-doctors-mobile">
              <div className="aap-expert-doctors-stack">
                <div className="aap-expert-doctor-cutout">
                  <img src={EXPERT_IMG_1} alt="皮肤科医生" />
                </div>
                <div className="aap-expert-doctor-cutout">
                  <img src={EXPERT_IMG_2} alt="皮肤科医生" />
                </div>
                <div className="aap-expert-doctor-cutout">
                  <img src={EXPERT_IMG_3} alt="皮肤科医生" />
                </div>
              </div>
            </div>
          </div>
          {/* 桌面端：三位医生逐层叠加 */}
          <div className="aap-expert-right">
            <div className="aap-expert-doctors-stack">
              <div className="aap-expert-doctor-cutout" style={{ zIndex: 3 }}>
                <img src={EXPERT_IMG_1} alt="皮肤科医生" />
              </div>
              <div className="aap-expert-doctor-cutout" style={{ zIndex: 2 }}>
                <img src={EXPERT_IMG_2} alt="皮肤科医生" />
              </div>
              <div className="aap-expert-doctor-cutout" style={{ zIndex: 1 }}>
                <img src={EXPERT_IMG_3} alt="皮肤科医生" />
              </div>
            </div>
          </div>
        </div>

        {/* ---- 2-2 诊断报告卡片 ---- */}
        <div className="aap-report-card">
          {/* 顶部状态条 */}
          <div className="aap-report-status">
            <span className="aap-report-status-left">
              <CheckIcon />
              生效中
            </span>
            <span className="aap-report-status-right">
              有效期 <span className="aap-report-expiry">23:59:59</span>
            </span>
          </div>

          {/* 核心信息区 — 双列布局 */}
          <div className="aap-report-body">
            <div className="aap-report-grid">
              {/* 左列 */}
              <div className="aap-report-col">
                <div className="aap-report-row">
                  <span className="aap-report-label">诊断结果</span>
                  <span className="aap-report-value aap-report-value--highlight">
                    皮肤衰老 <strong>Ⅲ 级</strong>（重度老化）
                  </span>
                </div>
                <div className="aap-report-row">
                  <span className="aap-report-label">诊断时间</span>
                  <span className="aap-report-value">2025.06.10 14:30:00</span>
                </div>
              </div>

              {/* 分割线 */}
              <div className="aap-report-col-divider"></div>

              {/* 右列 */}
              <div className="aap-report-col">
                <div className="aap-report-row">
                  <span className="aap-report-label">诊断医生</span>
                  <span className="aap-report-value">XXX 主任医师</span>
                </div>
                <div className="aap-report-row aap-report-row--seal">
                  <span className="aap-report-label">报告凭证</span>
                  <span className="aap-report-value">加盖医院/机构红色公章</span>
                  <RedSeal />
                </div>
              </div>
            </div>
          </div>

          {/* 底部补充说明 */}
          <p className="aap-report-disclaimer">
            本报告为 AI + 医生联合评估结果，仅供皮肤管理参考
          </p>
        </div>
      </div>

      {/* ==================== 模块 3：定制抗衰方案区 ==================== */}
      <div className={`aap-plan-section ${inView3 ? 'aap-visible' : ''}`} ref={ref3}>
        {/* 模块标题 */}
        <div className="aap-plan-header">
          <h3 className="aap-plan-title">定制搭配抗衰方案</h3>
          <div className="aap-plan-title-line"></div>
        </div>

        {/* 方案卡片 */}
        <div className="aap-plan-card">
          {PLAN_DIMENSIONS.map((dim, idx) => (
            <div key={dim.key} className="aap-plan-row">
              {/* 维度标识 — 蓝色虚线圆圈 + 大字 */}
              <div className="aap-plan-badge-wrap">
                <div className="aap-plan-badge" style={{ borderColor: dim.color }}>
                  <span className="aap-plan-badge-text">{dim.label}</span>
                </div>
              </div>

              {/* 箭头 + 描述 */}
              <div className="aap-plan-desc-wrap">
                <PlanArrow />
                <div className="aap-plan-desc-text">
                  <span className="aap-plan-desc-title">{dim.title}</span>
                  <span className="aap-plan-desc-sub">（{dim.desc}）</span>
                </div>
              </div>

              {/* 产品示意 */}
              <div className="aap-plan-products">
                {dim.items.map((item, i) => (
                  <div key={i} className="aap-plan-product-item">
                    <div className="aap-plan-product-icon">
                      {dim.key === 'medical' && (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                          <rect x="8" y="2" width="8" height="20" rx="3" stroke="#0A2463" strokeWidth="1.5" />
                          <rect x="2" y="8" width="20" height="8" rx="3" stroke="#0A2463" strokeWidth="1.5" />
                          <circle cx="12" cy="12" r="2" fill="rgba(10,36,99,0.15)" />
                        </svg>
                      )}
                      {dim.key === 'cosmetic' && (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                          <path d="M12 2L8 8h8l-4-6z" stroke="#1E3A8A" strokeWidth="1.5" strokeLinejoin="round" />
                          <rect x="6" y="8" width="12" height="14" rx="2" stroke="#1E3A8A" strokeWidth="1.5" />
                          <line x1="12" y1="12" x2="12" y2="17" stroke="#1E3A8A" strokeWidth="1" strokeLinecap="round" />
                        </svg>
                      )}
                      {dim.key === 'nutrition' && (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                          <circle cx="12" cy="12" r="9" stroke="#2E86C1" strokeWidth="1.5" />
                          <path d="M8 10c0-1.5 1.5-3 4-3s4 1.5 4 3c0 2-4 6-4 6s-4-4-4-6z" stroke="#2E86C1" strokeWidth="1.2" fill="none" />
                          <circle cx="12" cy="9" r="1" fill="rgba(46,134,193,0.3)" />
                        </svg>
                      )}
                    </div>
                    <span className="aap-plan-product-name">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ==================== 定制按钮 ==================== */}
      <div className={`aap-customize-wrap ${inView3 ? 'aap-visible' : ''}`}>
        <button
          className="aap-customize-btn"
          onClick={() => onNavigate('detect')}
        >
          <span>点击定制</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  );
};

export default AntiAgingPlanSection;
