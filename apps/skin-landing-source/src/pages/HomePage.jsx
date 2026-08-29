import React from 'react';
import { HomeIcon, HistoryIcon, ProfileIcon } from '../components/Icons';

import DoctorCarousel from '../components/DoctorCarousel';
import CaseDisplay from '../components/CaseDisplay';
import Statistics from '../components/Statistics';
import SkinAgingSection from '../components/SkinAgingSection';
import AntiAgingPlanSection from '../components/AntiAgingPlanSection';
import AppFooter from '../components/AppFooter';
import FloatingCta from '../components/FloatingCta';
import { DOCTOR_IMG_1, DOCTOR_IMG_2, DOCTOR_IMG_3 } from '../utils/constants';

/**
 * 首页 — 兰峤医疗品牌风格
 * 区块顺序：brand hero → 医生卡片网格 → 医生轮播 → 统计数据 → 服务优势
 *          → 案例展示 → 专家会诊 → 医生推荐 → 底部 → TabBar
 */
const HomePage = ({ onNavigate }) => (
  <div className="page lq-home-page">

    {/* ===== 区块1: BRAND HERO ===== */}
    <div className="lq-hero">
      {/* 背景虚幻装饰 */}
      <div className="lq-hero-aura"></div>
      <div className="lq-hero-blob lq-hero-blob--1"></div>
      <div className="lq-hero-blob lq-hero-blob--2"></div>
      <div className="lq-hero-blob lq-hero-blob--3"></div>
      <div className="lq-hero-blob lq-hero-blob--4"></div>

      <div className="lq-hero-brand-row">
        <span className="lq-hero-brand-name">兰峤医疗</span>
      </div>
      <div className="lq-hero-tagline">「互联网问诊」皮肤品牌</div>
      <div className="lq-hero-divider"></div>
      <div className="lq-hero-tags-box">
        <span className="lq-hero-tag-cell lq-hero-tag-cell--ai">AI专业诊断</span>
        <span className="lq-hero-tags-sep">|</span>
        <span className="lq-hero-tag-cell lq-hero-tag-cell--skin">皮肤精准评估</span>
      </div>

      {/* AI Face scan image */}
      <div className="lq-face-wrap">
        {/* 人像背后装饰 */}
        <div className="lq-face-aura"></div>
        <div className="lq-face-ring lq-face-ring--outer"></div>
        <div className="lq-face-ring lq-face-ring--inner"></div>
        <div className="lq-face-sparkle lq-face-sparkle--1"></div>
        <div className="lq-face-sparkle lq-face-sparkle--2"></div>
        <div className="lq-face-sparkle lq-face-sparkle--3"></div>
        <div className="lq-face-sparkle lq-face-sparkle--4"></div>
        <div className="lq-face-sparkle lq-face-sparkle--5"></div>
        <div className="lq-face-sparkle lq-face-sparkle--6"></div>
        {/* 漂浮粒子 */}
        <div className="lq-face-particle lq-face-particle--1"></div>
        <div className="lq-face-particle lq-face-particle--2"></div>
        {/* 底部光点 */}
        <div className="lq-face-glow-dot lq-face-glow-dot--1"></div>
        <div className="lq-face-glow-dot lq-face-glow-dot--2"></div>
        <div className="lq-face-glow-dot lq-face-glow-dot--3"></div>
        <img src={DOCTOR_IMG_1} alt="AI皮肤检测" className="lq-face-img" />
        <div className="lq-face-glow"></div>
      </div>

      {/* Main CTA Button */}
      <button className="lq-main-cta" onClick={() => onNavigate('detect')}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{ marginRight: 8 }}>
          <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2"/>
          <path d="M10 8L16 12L10 16V8Z" fill="white"/>
        </svg>
        马上诊断
      </button>
    </div>

    {/* ===== 区块2: DOCTOR CARDS (2列网格) ===== */}
    <div className="lq-doctors-section">
      {/* Doctor 1 - 皮肤专家 */}
      <div className="lq-doctor-card">
        <div className="lq-doctor-card-bg-deco"></div>
        <div className="lq-doctor-card-accent"></div>
        <img src={DOCTOR_IMG_2} alt="皮肤专家" className="lq-doctor-img" />
        <div className="lq-doctor-info">
          <div className="lq-doctor-info-aura"></div>
          <div className="lq-doctor-info-ring"></div>
          <div className="lq-doctor-label">皮肤专家在线</div>
          <div className="lq-doctor-deco">
            <div className="lq-doctor-deco-line"></div>
            <div className="lq-doctor-deco-dot lq-doctor-deco-dot--1"></div>
            <div className="lq-doctor-deco-dot lq-doctor-deco-dot--2"></div>
            <div className="lq-doctor-deco-dot lq-doctor-deco-dot--3"></div>
          </div>
          <button className="lq-doctor-btn lq-btn-blue" onClick={() => onNavigate('detect')}>去咨询</button>
        </div>
      </div>

      {/* Doctor 2 - 三甲皮肤科医生 */}
      <div className="lq-doctor-card">
        <div className="lq-doctor-card-bg-deco"></div>
        <div className="lq-doctor-card-accent"></div>
        <img src={DOCTOR_IMG_3} alt="三甲皮肤科医生" className="lq-doctor-img" />
        <div className="lq-doctor-info">
          <div className="lq-doctor-info-aura"></div>
          <div className="lq-doctor-info-ring"></div>
          <div className="lq-doctor-label">三甲皮肤科医生</div>
          <div className="lq-doctor-deco">
            <div className="lq-doctor-deco-line"></div>
            <div className="lq-doctor-deco-dot lq-doctor-deco-dot--1"></div>
            <div className="lq-doctor-deco-dot lq-doctor-deco-dot--2"></div>
            <div className="lq-doctor-deco-dot lq-doctor-deco-dot--3"></div>
          </div>
          <button className="lq-doctor-btn lq-btn-outline" onClick={() => onNavigate('detect')}>预约问诊</button>
        </div>
      </div>

      {/* 动态向下箭头 */}
      <div className="lq-doctors-arrow-wrap">
        <div className="lq-doctors-arrow lq-doctors-arrow--1">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M6 9L12 15L18 9" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className="lq-doctors-arrow lq-doctors-arrow--2">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M6 9L12 15L18 9" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>
    </div>

    {/* ===== 蓝色模块：医生轮播 + 案例展示 ===== */}
    <div className="blue-module">
      <DoctorCarousel onNavigate={onNavigate} />
      <CaseDisplay onNavigate={onNavigate}/>
      <div className="blue-module-curve"></div>
    </div>

    {/* ===== 区块5: 数据统计 ===== */}
    <Statistics/>

    {/* ===== 区块6: 皮肤衰老分级诊断模块 ===== */}
    <SkinAgingSection onNavigate={onNavigate}/>

    {/* ===== 区块7: 依据诊断结果出具抗衰方案 ===== */}
    <AntiAgingPlanSection onNavigate={onNavigate}/>

    {/* ===== 区块8: 底部 ===== */}
    <AppFooter/>

    {/* ===== 底部悬浮跳转按钮 ===== */}
    <FloatingCta />

    {/* ===== 底部导航栏 ===== */}
    <div className="tab-bar">
      <div className="tab-item active">
        <HomeIcon/><span>首页</span>
      </div>
      <div className="tab-item" onClick={() => onNavigate('history')}>
        <HistoryIcon/><span>历史</span>
      </div>
      <div className="tab-item" onClick={() => onNavigate('profile')}>
        <ProfileIcon/><span>我的</span>
      </div>
    </div>
  </div>
);

export default HomePage;
