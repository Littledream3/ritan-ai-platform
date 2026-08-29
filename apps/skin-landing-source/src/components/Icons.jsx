import React from 'react';

// Logo图标
export const LogoIcon = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
    <circle cx="20" cy="20" r="18" fill="white" fillOpacity="0.2"/>
    <circle cx="20" cy="20" r="12" fill="white"/>
    <circle cx="20" cy="20" r="6" fill="#1B3A5C"/>
  </svg>
);

// Logo文字图标 (大号)
export const LogoLarge = () => (
  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
    <circle cx="40" cy="40" r="36" fill="#1B3A5C"/>
    <circle cx="40" cy="40" r="24" fill="white" fillOpacity="0.15"/>
    <text x="40" y="46" textAnchor="middle" fontSize="28" fontWeight="bold" fill="white">兰</text>
  </svg>
);

// 用户头像图标
export const UserAvatar = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
    <circle cx="20" cy="20" r="18" fill="white"/>
    <circle cx="20" cy="15" r="6" fill="#1B3A5C"/>
    <path d="M8 32C8 26.477 13.373 22 20 22C26.627 22 32 26.477 32 32" fill="#1B3A5C"/>
  </svg>
);

// 医生头像 (男1)
export const DoctorAvatar1 = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <circle cx="32" cy="32" r="30" fill="#E8EDF2"/>
    <circle cx="32" cy="24" r="10" fill="#1B3A5C"/>
    <path d="M14 52C14 43.163 22.163 36 32 36C41.837 36 50 43.163 50 52" fill="#1B3A5C"/>
  </svg>
);

// 医生头像 (女1)
export const DoctorAvatar2 = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <circle cx="32" cy="32" r="30" fill="#F0E8F0"/>
    <circle cx="32" cy="24" r="10" fill="#5B3A6C"/>
    <path d="M12 54C12 44.059 20.954 36 32 36C43.046 36 52 44.059 52 54" fill="#5B3A6C"/>
  </svg>
);

// 医生头像 (男2)
export const DoctorAvatar3 = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <circle cx="32" cy="32" r="30" fill="#E6EEF5"/>
    <circle cx="32" cy="25" r="9" fill="#2C5F8A"/>
    <path d="M15 50C15 41.716 22.716 35 32 35C41.284 35 49 41.716 49 50" fill="#2C5F8A"/>
  </svg>
);

// 医生头像 (女2)
export const DoctorAvatar4 = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <circle cx="32" cy="32" r="30" fill="#F5EDF0"/>
    <circle cx="32" cy="25" r="9" fill="#8B5A7A"/>
    <path d="M13 51C13 42.164 21.507 35 32 35C42.493 35 51 42.164 51 51" fill="#8B5A7A"/>
  </svg>
);

// 医生头像 (男3 - 模糊处理版)
export const DoctorAvatar5 = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
    <defs>
      <filter id="blur1">
        <feGaussianBlur in="SourceGraphic" stdDeviation="2"/>
      </filter>
    </defs>
    <circle cx="32" cy="32" r="30" fill="#E8EDF2"/>
    <circle cx="32" cy="24" r="10" fill="#666" filter="url(#blur1)"/>
    <path d="M14 52C14 43.163 22.163 36 32 36C41.837 36 50 43.163 50 52" fill="#888" filter="url(#blur1)"/>
  </svg>
);

// 大号用户头像
export const UserAvatarLarge = () => (
  <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
    <circle cx="40" cy="40" r="36" fill="#F5F5F5" stroke="#E0E0E0" strokeWidth="2"/>
    <circle cx="40" cy="30" r="14" fill="#1B3A5C"/>
    <path d="M16 64C16 52.954 25.954 44 40 44C54.046 44 64 52.954 64 64" fill="#1B3A5C"/>
  </svg>
);

// 首页图标
export const HomeIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="M3 12L12 3L21 12V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 历史图标
export const HistoryIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
    <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 个人中心图标
export const ProfileIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
    <path d="M4 20C4 16.6863 7.58172 14 12 14C16.4183 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 返回图标
export const BackIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 箭头图标
export const ArrowIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M7 5L13 10L7 15" stroke="#BDBDBD" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 勾选图标
export const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M3 8L6 11L13 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 警告图标
export const WarningIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M8 5V8M8 11V11.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

// 隐私图标
export const PrivacyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <rect x="3" y="7" width="10" height="7" rx="2" stroke="#6B7B8D" strokeWidth="1.5"/>
    <path d="M5 7V5C5 3.34315 6.34315 2 8 2C9.65685 2 11 3.34315 11 5V7" stroke="#6B7B8D" strokeWidth="1.5"/>
  </svg>
);

// 皮肤检测图标
export const SkinDetectionIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="20" fill="white" fillOpacity="0.2"/>
    <path d="M24 12V36M12 24H36" stroke="white" strokeWidth="3" strokeLinecap="round"/>
  </svg>
);

// 衰老评估图标
export const AgingIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="20" fill="white" fillOpacity="0.2"/>
    <path d="M14 34L20 26L28 30L34 18" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="34" cy="18" r="3" fill="white"/>
  </svg>
);

// 术后监测图标
export const SurgeryIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="20" fill="white" fillOpacity="0.2"/>
    <rect x="16" y="16" width="16" height="16" rx="4" stroke="white" strokeWidth="3" fill="none"/>
    <path d="M24 20V28M20 24H28" stroke="white" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 历史报告图标
export const HistoryReportIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="20" fill="white" fillOpacity="0.2"/>
    <circle cx="24" cy="26" r="10" stroke="white" strokeWidth="3" fill="none"/>
    <path d="M24 20V26L28 30" stroke="white" strokeWidth="3" strokeLinecap="round"/>
  </svg>
);

// === 新增图标 ===

// 预约咨询图标
export const AppointmentIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
    <path d="M3 10H21" stroke="currentColor" strokeWidth="2"/>
    <path d="M8 2V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <path d="M16 2V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="12" cy="15" r="2" fill="currentColor"/>
  </svg>
);

// 立即问诊图标
export const ConsultationIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
    <path d="M8 12H16M12 8V16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 专家图标
export const ExpertIcon = () => (
  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="10" r="5" stroke="currentColor" strokeWidth="2"/>
    <path d="M6 28C6 22.477 10.477 18 16 18C21.523 18 26 22.477 26 28" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    <path d="M16 8V2M20 4L16 8L12 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 案例对比图标
export const CompareIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="9" cy="12" r="7" stroke="currentColor" strokeWidth="1.5"/>
    <circle cx="16" cy="12" r="7" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2"/>
    <path d="M2 12H22" stroke="currentColor" strokeWidth="1" opacity="0.5"/>
    <text x="16" y="16" textAnchor="middle" fontSize="8" fill="currentColor">✓</text>
  </svg>
);

// 用户统计图标
export const UsersIcon = () => (
  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="12" cy="10" r="4" stroke="currentColor" strokeWidth="2"/>
    <circle cx="22" cy="10" r="3" stroke="currentColor" strokeWidth="2"/>
    <path d="M4 26C4 21.582 7.582 18 12 18C16.418 18 20 21.582 20 26" stroke="currentColor" strokeWidth="2"/>
    <path d="M19 22C21.209 22 23 23.791 23 26" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 满意度图标
export const SatisfactionIcon = () => (
  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="2"/>
    <circle cx="12" cy="13" r="1.5" fill="currentColor"/>
    <circle cx="20" cy="13" r="1.5" fill="currentColor"/>
    <path d="M10 19C11.5 22 14 23.5 16 23.5C18 23.5 20.5 22 22 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 城市覆盖图标
export const CityIcon = () => (
  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <rect x="6" y="10" width="20" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
    <path d="M10 6L16 2L22 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M12 14V18M16 14V18M20 14V18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 步骤图标 (相机/拍摄)
export const CameraIcon = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
    <rect x="6" y="10" width="28" height="22" rx="4" stroke="#1B3A5C" strokeWidth="2"/>
    <circle cx="20" cy="21" r="6" stroke="#1B3A5C" strokeWidth="2"/>
    <circle cx="20" cy="21" r="2" fill="#1B3A5C"/>
    <path d="M12 10L14 6H26L28 10" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 步骤图标 (AI分析)
export const AIIcon = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
    <circle cx="20" cy="20" r="14" stroke="#1B3A5C" strokeWidth="2"/>
    <path d="M12 26C14 20 18 16 20 16C22 16 26 20 28 26" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="20" cy="14" r="3" fill="#1B3A5C"/>
  </svg>
);

// 步骤图标 (报告)
export const ReportIcon = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
    <rect x="8" y="4" width="24" height="32" rx="3" stroke="#1B3A5C" strokeWidth="2"/>
    <path d="M14 14H26M14 20H26M14 26H20" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 步骤图标 (咨询)
export const ChatIcon = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
    <rect x="6" y="8" width="28" height="20" rx="4" stroke="#1B3A5C" strokeWidth="2"/>
    <path d="M10 30L14 24H30C32.209 24 34 22.209 34 20V8" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="16" cy="18" r="1.5" fill="#1B3A5C"/>
    <circle cx="22" cy="18" r="1.5" fill="#1B3A5C"/>
    <circle cx="28" cy="18" r="1.5" fill="#1B3A5C"/>
  </svg>
);

// 下载图标
export const DownloadIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="M12 3V17M12 17L7 12M12 17L17 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M4 21H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

// 电话图标
export const PhoneIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M4 3C3.45 3 3 3.45 3 4C3 11.18 8.82 17 16 17C16.55 17 17 16.55 17 16V13.5C17 12.95 16.55 12.5 16 12.5C14.76 12.5 13.55 12.3 12.43 11.93C12.33 11.9 12.22 11.88 12.12 11.88C11.86 11.88 11.61 11.98 11.41 12.17L9.21 14.37C6.38 12.93 4.06 10.62 2.62 7.79L4.82 5.59C5.1 5.31 5.18 4.92 5.07 4.57C4.7 3.45 4.5 2.25 4.5 1C4.5 0.45 4.05 0 3.5 0H1C0.45 0 0 0.45 0 1C0 10.49 8.51 19 18 19C18.55 19 19 18.55 19 18V15.5C19 14.95 18.55 14.5 18 14.5C16.75 14.5 15.55 14.3 14.43 13.93C14.33 13.9 14.22 13.88 14.12 13.88C13.86 13.88 13.61 13.98 13.41 14.17L11.21 16.37C8.38 14.93 6.06 12.62 4.62 9.79L6.82 7.59C7.1 7.31 7.18 6.92 7.07 6.57C6.7 5.45 6.5 4.25 6.5 3C6.5 2.45 6.05 2 5.5 2H4C3.45 2 3 2.45 3 3Z" fill="currentColor" transform="scale(0.9) translate(1, 1)"/>
  </svg>
);

// 皮肤检测功能图标 (放大镜+脸)
export const SkinCheckIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <circle cx="20" cy="20" r="8" stroke="white" strokeWidth="2.5"/>
    <path d="M26 26L34 34" stroke="white" strokeWidth="2.5" strokeLinecap="round"/>
    <circle cx="38" cy="16" r="3" stroke="white" strokeWidth="2" strokeDasharray="2 2"/>
  </svg>
);

// 医疗十字图标
export const MedicalCrossIcon = () => (
  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
    <rect x="8" y="16" width="32" height="20" rx="4" stroke="white" strokeWidth="2.5"/>
    <path d="M24 16V36" stroke="white" strokeWidth="2.5"/>
    <path d="M16 26H32" stroke="white" strokeWidth="2.5"/>
  </svg>
);

// 星星图标
export const StarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 1.5L10.06 5.77L14.74 6.44L11.37 9.76L12.17 14.45L8 12.26L3.83 14.45L4.63 9.76L1.26 6.44L5.94 5.77L8 1.5Z" fill="#D4A843" stroke="#D4A843" strokeWidth="1"/>
  </svg>
);

// 菱形装饰
export const DiamondIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path d="M6 0L12 6L6 12L0 6L6 0Z" fill="#D4A843"/>
  </svg>
);

// 盾牌图标 (安全)
export const ShieldIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path d="M12 2L4 6V12C4 16.418 7.582 20 12 22C16.418 20 20 16.418 20 12V6L12 2Z" stroke="currentColor" strokeWidth="2"/>
    <path d="M9 12L11 14L15 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
