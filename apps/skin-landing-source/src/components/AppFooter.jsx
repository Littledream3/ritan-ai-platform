import React from 'react';

/* ================================================================
   AppFooter — 页面底部模块
   模块 1：顶部品牌引导区（品牌名 + 引导文案 + 英文辅助 + 分割线）
   模块 2：中间渠道矩阵区（公众号 / 抗衰顾问 / 小红书）
   模块 3：底部品牌标识区（兰峤 LANQIAO Logo）
   ================================================================ */

// ---- 抗衰顾问图标 ----
const ConsultantIcon = () => (
  <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
    <circle cx="26" cy="26" r="24" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" />
    {/* 人物头部 */}
    <circle cx="26" cy="17" r="6" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" fill="none" />
    {/* 人物身体 */}
    <path d="M12 42C12 34.268 18.268 28 26 28C33.732 28 40 34.268 40 42" stroke="rgba(255,255,255,0.85)" strokeWidth="1.5" strokeLinecap="round" fill="none" />
    {/* 听诊器 */}
    <path d="M34 14C34 11.791 35.791 10 38 10C40.209 10 42 11.791 42 14C42 16.209 40.209 18 38 18" stroke="rgba(255,255,255,0.65)" strokeWidth="1.2" strokeLinecap="round" fill="none" />
    <path d="M38 18V24C38 26.209 36.209 28 34 28" stroke="rgba(255,255,255,0.65)" strokeWidth="1.2" strokeLinecap="round" fill="none" />
    {/* 十字标识 */}
    <rect x="31.5" y="24" width="5" height="5" rx="1" stroke="rgba(255,255,255,0.55)" strokeWidth="1" fill="none" />
  </svg>
);

// ---- 渠道数据 ----
const CHANNELS = [
  {
    type: 'image',
    imgSrc: './picture/微信.png',
    title: 'LANQIAO 公众号',
    desc: '获取专业抗衰指南',
  },
  {
    type: 'svg',
    icon: <ConsultantIcon />,
    title: 'LANQIAO 抗衰顾问',
    desc: '一对一皮肤管理咨询',
  },
  {
    type: 'image',
    imgSrc: './picture/小红书.png',
    title: 'LANQIAO 官方账号',
    desc: '抗衰干货与案例分享',
  },
];

// ================================================================
// 主组件
// ================================================================
const AppFooter = () => (
  <footer className="app-footer">
    {/* ========== 模块 1 + 2：品牌引导区 + 渠道矩阵（蓝色背景） ========== */}
    <div className="af-blue-section">
      {/* 顶部白色圆角曲线 */}
      <div className="af-curve af-curve--top">
        <svg viewBox="0 0 390 40" preserveAspectRatio="none" className="af-curve-svg">
          <path d="M0 40C0 40 65 0 195 0C325 0 390 40 390 40V0H0V40Z" fill="#0A2463" />
        </svg>
      </div>

      {/* ---- 模块 1：顶部品牌引导区 ---- */}
      <div className="af-hero">
        <p className="af-hero-brand">关注 <strong className="af-hero-brand-name">兰峤 LANQIAO</strong></p>
        <p className="af-hero-main">— 了解更多皮肤抗衰知识 —</p>
        <p className="af-hero-sub">Follow Us And Learn More About Anti-Aging</p>
        <div className="af-hero-divider">
          <svg width="100%" height="2" viewBox="0 0 320 2" preserveAspectRatio="none">
            <line x1="0" y1="1" x2="320" y2="1" stroke="rgba(255,255,255,0.3)" strokeWidth="1" strokeDasharray="4 5" />
          </svg>
        </div>
      </div>

      {/* ---- 模块 2：中间渠道矩阵区 ---- */}
      <div className="af-channels">
        {CHANNELS.map((ch, i) => (
          <div key={i} className="af-channel-item">
            <div className="af-channel-icon">
              {ch.type === 'image' ? (
                <img src={ch.imgSrc} alt={ch.title} className="af-channel-img" />
              ) : (
                ch.icon
              )}
            </div>
            <p className="af-channel-title">{ch.title}</p>
            <p className="af-channel-desc">{ch.desc}</p>
          </div>
        ))}
      </div>

      {/* 底部白色圆角曲线 */}
      <div className="af-curve af-curve--bottom">
        <svg viewBox="0 0 390 40" preserveAspectRatio="none" className="af-curve-svg">
          <path d="M0 0C0 0 65 40 195 40C325 40 390 0 390 0V40H0V0Z" fill="#FFFFFF" />
        </svg>
      </div>
    </div>

    {/* ========== 模块 3：底部品牌标识区（白色背景） ========== */}
    <div className="af-logo-section">
      {/* 顶部蓝色圆角曲线 */}
      <div className="af-curve af-curve--logo-top">
        <svg viewBox="0 0 390 40" preserveAspectRatio="none" className="af-curve-svg">
          <path d="M0 40C0 40 65 0 195 0C325 0 390 40 390 40V0H0V40Z" fill="#FFFFFF" />
        </svg>
      </div>

      <div className="af-logo-wrap">
        <div className="af-logo-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="22" stroke="#0A2463" strokeWidth="2" fill="none" />
            <circle cx="24" cy="24" r="16" stroke="#0A2463" strokeWidth="1" fill="none" strokeDasharray="3 3" />
            <text x="24" y="29" textAnchor="middle" fontSize="18" fontWeight="700" fill="#0A2463">兰</text>
          </svg>
        </div>
        <div className="af-logo-text">
          <span className="af-logo-cn">兰峤</span>
          <span className="af-logo-en">LANQIAO</span>
        </div>
      </div>
    </div>
  </footer>
);

export default AppFooter;
