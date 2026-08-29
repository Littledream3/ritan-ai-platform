// Build standalone dist/index.html (CDN React + Babel, double-click to open)
const fs = require('fs');
const path = require('path');

// Read CSS
const css = fs.readFileSync(path.join(__dirname, 'src/styles/globals.css'), 'utf8');

// HTML template
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>兰峤AI测肤 - 专业皮肤检测与衰老评估</title>
  <meta name="description" content="兰峤AI测肤小程序，基于AI算法的面部皮肤健康检测与衰老评估平台">
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"><\/script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"><\/script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
  <style>
${css}
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel">
    const { useState, useEffect, useCallback, useRef } = React;

    // ===== Image paths (relative to dist/index.html) =====
    const DOCTOR_IMG_1 = "../picture/图片1.png";
    const DOCTOR_IMG_2 = "../picture/图片2.jpg";
    const DOCTOR_IMG_3 = "../picture/图片3.jpg";

    // ===== Constants =====
    const CAPTURE_ANGLES = [
      { id: 0, name: '正面', angle: 0 },
      { id: 1, name: '左侧45°', angle: -45 },
      { id: 2, name: '右侧45°', angle: 45 }
    ];
    const ANALYSIS_STEPS = ['图像预处理','人脸检测与对齐','皮肤区域分割','皱纹分析','色斑检测','弹性评估','综合评分生成'];

    // ===== Mock Data =====
    const GlogauLevels = [
      { level: 'Ⅰ级', description: '轻度光老化 - 无明显皱纹，轻度色素改变' },
      { level: 'Ⅱ级', description: '中度光老化 - 早期皱纹，轻中度色斑' },
      { level: 'Ⅲ级', description: '重度光老化 - 中度皱纹，明显色斑' },
      { level: 'Ⅳ级', description: '严重光老化 - 严重皱纹，皮肤弹性差' }
    ];
    const generateMockAnalysisData = () => {
      const baseScore = Math.floor(Math.random() * 30) + 60;
      const levelIndex = Math.min(3, Math.floor((100 - baseScore) / 25));
      return {
        score: baseScore,
        wrinkles: Math.floor(Math.random() * 40) + 40,
        spots: Math.floor(Math.random() * 30) + 30,
        elasticity: Math.floor(Math.random() * 40) + 50,
        pores: Math.floor(Math.random() * 30) + 40,
        photoaging: Math.floor(Math.random() * 30) + 40,
        glogauLevel: GlogauLevels[levelIndex].level,
        glogauDescription: GlogauLevels[levelIndex].description,
        recommendations: ['建议使用含有视黄醇的抗衰精华','加强防晒措施，SPF30以上','考虑进行光子嫩肤治疗','保持充足睡眠和水分摄入'],
        analysisDate: new Date().toLocaleDateString('zh-CN')
      };
    };

    // ===== Icon Components =====
    const LogoIcon = () => (
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <circle cx="20" cy="20" r="18" fill="white" fillOpacity="0.2"/>
        <circle cx="20" cy="20" r="12" fill="white"/>
        <circle cx="20" cy="20" r="6" fill="#1B3A5C"/>
      </svg>
    );
    const LogoLarge = () => (
      <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
        <circle cx="40" cy="40" r="36" fill="#1B3A5C"/>
        <circle cx="40" cy="40" r="24" fill="white" fillOpacity="0.15"/>
        <text x="40" y="46" textAnchor="middle" fontSize="28" fontWeight="bold" fill="white">兰</text>
      </svg>
    );
    const UserAvatar = () => (
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <circle cx="20" cy="20" r="18" fill="white"/>
        <circle cx="20" cy="15" r="6" fill="#1B3A5C"/>
        <path d="M8 32C8 26.477 13.373 22 20 22C26.627 22 32 26.477 32 32" fill="#1B3A5C"/>
      </svg>
    );
    const DoctorAvatar1 = () => (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="30" fill="#E8EDF2"/>
        <circle cx="32" cy="24" r="10" fill="#1B3A5C"/>
        <path d="M14 52C14 43.163 22.163 36 32 36C41.837 36 50 43.163 50 52" fill="#1B3A5C"/>
      </svg>
    );
    const DoctorAvatar2 = () => (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="30" fill="#F0E8F0"/>
        <circle cx="32" cy="24" r="10" fill="#5B3A6C"/>
        <path d="M12 54C12 44.059 20.954 36 32 36C43.046 36 52 44.059 52 54" fill="#5B3A6C"/>
      </svg>
    );
    const DoctorAvatar3 = () => (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="30" fill="#E6EEF5"/>
        <circle cx="32" cy="25" r="9" fill="#2C5F8A"/>
        <path d="M15 50C15 41.716 22.716 35 32 35C41.284 35 49 41.716 49 50" fill="#2C5F8A"/>
      </svg>
    );
    const DoctorAvatar4 = () => (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="30" fill="#F5EDF0"/>
        <circle cx="32" cy="25" r="9" fill="#8B5A7A"/>
        <path d="M13 51C13 42.164 21.507 35 32 35C42.493 35 51 42.164 51 51" fill="#8B5A7A"/>
      </svg>
    );
    const DoctorAvatar5 = () => (
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <defs><filter id="blur1"><feGaussianBlur in="SourceGraphic" stdDeviation="2"/></filter></defs>
        <circle cx="32" cy="32" r="30" fill="#E8EDF2"/>
        <circle cx="32" cy="24" r="10" fill="#666" filter="url(#blur1)"/>
        <path d="M14 52C14 43.163 22.163 36 32 36C41.837 36 50 43.163 50 52" fill="#888" filter="url(#blur1)"/>
      </svg>
    );
    const HomeIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M3 12L12 3L21 12V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    const HistoryIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
        <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const ProfileIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
        <path d="M4 20C4 16.6863 7.58172 14 12 14C16.4183 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const BackIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    const ArrowIcon = () => (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M7 5L13 10L7 15" stroke="#BDBDBD" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    const WarningIcon = () => (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/>
        <path d="M8 5V8M8 11V11.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    );
    const PrivacyIcon = () => (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="3" y="7" width="10" height="7" rx="2" stroke="#6B7B8D" strokeWidth="1.5"/>
        <path d="M5 7V5C5 3.34315 6.34315 2 8 2C9.65685 2 11 3.34315 11 5V7" stroke="#6B7B8D" strokeWidth="1.5"/>
      </svg>
    );
    const AppointmentIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
        <path d="M3 10H21" stroke="currentColor" strokeWidth="2"/>
        <path d="M8 2V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <path d="M16 2V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="12" cy="15" r="2" fill="currentColor"/>
      </svg>
    );
    const ConsultationIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
        <path d="M8 12H16M12 8V16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const ExpertIcon = () => (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="10" r="5" stroke="currentColor" strokeWidth="2"/>
        <path d="M6 28C6 22.477 10.477 18 16 18C21.523 18 26 22.477 26 28" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <path d="M16 8V2M20 4L16 8L12 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    const UsersIcon = () => (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="12" cy="10" r="4" stroke="currentColor" strokeWidth="2"/>
        <circle cx="22" cy="10" r="3" stroke="currentColor" strokeWidth="2"/>
        <path d="M4 26C4 21.582 7.582 18 12 18C16.418 18 20 21.582 20 26" stroke="currentColor" strokeWidth="2"/>
        <path d="M19 22C21.209 22 23 23.791 23 26" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const SatisfactionIcon = () => (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="2"/>
        <circle cx="12" cy="13" r="1.5" fill="currentColor"/>
        <circle cx="20" cy="13" r="1.5" fill="currentColor"/>
        <path d="M10 19C11.5 22 14 23.5 16 23.5C18 23.5 20.5 22 22 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const CityIcon = () => (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <rect x="6" y="10" width="20" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
        <path d="M10 6L16 2L22 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M12 14V18M16 14V18M20 14V18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const ShieldIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L4 6V12C4 16.418 7.582 20 12 22C16.418 20 20 16.418 20 12V6L12 2Z" stroke="currentColor" strokeWidth="2"/>
        <path d="M9 12L11 14L15 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    const CameraIcon = () => (
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <rect x="6" y="10" width="28" height="22" rx="4" stroke="#1B3A5C" strokeWidth="2"/>
        <circle cx="20" cy="21" r="6" stroke="#1B3A5C" strokeWidth="2"/>
        <circle cx="20" cy="21" r="2" fill="#1B3A5C"/>
        <path d="M12 10L14 6H26L28 10" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    const AIIcon = () => (
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <circle cx="20" cy="20" r="14" stroke="#1B3A5C" strokeWidth="2"/>
        <path d="M12 26C14 20 18 16 20 16C22 16 26 20 28 26" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="20" cy="14" r="3" fill="#1B3A5C"/>
      </svg>
    );
    const ReportIcon = () => (
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <rect x="8" y="4" width="24" height="32" rx="3" stroke="#1B3A5C" strokeWidth="2"/>
        <path d="M14 14H26M14 20H26M14 26H20" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const ChatIcon = () => (
      <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
        <rect x="6" y="8" width="28" height="20" rx="4" stroke="#1B3A5C" strokeWidth="2"/>
        <path d="M10 30L14 24H30C32.209 24 34 22.209 34 20V8" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="16" cy="18" r="1.5" fill="#1B3A5C"/>
        <circle cx="22" cy="18" r="1.5" fill="#1B3A5C"/>
        <circle cx="28" cy="18" r="1.5" fill="#1B3A5C"/>
      </svg>
    );
    const DownloadIcon = () => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M12 3V17M12 17L7 12M12 17L17 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M4 21H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    );
    const PhoneIcon = () => (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M4 3C3.45 3 3 3.45 3 4C3 11.18 8.82 17 16 17C16.55 17 17 16.55 17 16V13.5C17 12.95 16.55 12.5 16 12.5C14.76 12.5 13.55 12.3 12.43 11.93C12.33 11.9 12.22 11.88 12.12 11.88C11.86 11.88 11.61 11.98 11.41 12.17L9.21 14.37C6.38 12.93 4.06 10.62 2.62 7.79L4.82 5.59C5.1 5.31 5.18 4.92 5.07 4.57C4.7 3.45 4.5 2.25 4.5 1C4.5 0.45 4.05 0 3.5 0H1C0.45 0 0 0.45 0 1C0 10.49 8.51 19 18 19C18.55 19 19 18.55 19 18V15.5C19 14.95 18.55 14.5 18 14.5C16.75 14.5 15.55 14.3 14.43 13.93C14.33 13.9 14.22 13.88 14.12 13.88C13.86 13.88 13.61 13.98 13.41 14.17L11.21 16.37C8.38 14.93 6.06 12.62 4.62 9.79L6.82 7.59C7.1 7.31 7.18 6.92 7.07 6.57C6.7 5.45 6.5 4.25 6.5 3C6.5 2.45 6.05 2 5.5 2H4C3.45 2 3 2.45 3 3Z" fill="currentColor" transform="scale(0.9) translate(1,1)"/>
      </svg>
    );
    const StarIcon = () => (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M8 1.5L10.06 5.77L14.74 6.44L11.37 9.76L12.17 14.45L8 12.26L3.83 14.45L4.63 9.76L1.26 6.44L5.94 5.77L8 1.5Z" fill="#D4A843" stroke="#D4A843" strokeWidth="1"/>
      </svg>
    );

    // ===== ScoreCircle =====
    const ScoreCircle = ({ score, size = 140 }) => {
      const radius = (size - 20) / 2;
      const circumference = 2 * Math.PI * radius;
      const strokeDashoffset = circumference * (1 - score / 100);
      const getColor = () => { if (score >= 80) return '#4CAF50'; if (score >= 60) return '#FF9800'; return '#F44336'; };
      return (
        <svg width={size} height={size} viewBox={\`0 0 \${size} \${size}\`}>
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#E2E8F0" strokeWidth="10"/>
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={getColor()} strokeWidth="10" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} transform={\`rotate(-90 \${size/2} \${size/2})\`} style={{transition:'stroke-dashoffset 0.5s ease'}}/>
          <text x={size/2} y={size/2-10} textAnchor="middle" fontSize="36" fontWeight="bold" fill="#1A2A3A">{score}</text>
          <text x={size/2} y={size/2+15} textAnchor="middle" fontSize="14" fill="#6B7B8D">/ 100</text>
        </svg>
      );
    };

    // ===== RadarChart =====
    const RadarChart = ({ data }) => {
      const items = [{name:'皱纹',value:data.wrinkles||0},{name:'色斑',value:data.spots||0},{name:'弹性',value:data.elasticity||0},{name:'毛孔',value:data.pores||0},{name:'光老化',value:data.photoaging||0}];
      const cx=140,cy=140,mr=100;
      const points = items.map((item,i)=>{const a=(i*72-90)*Math.PI/180;const r=(item.value/100)*mr;return \`\${cx+r*Math.cos(a)},\${cy+r*Math.sin(a)}\`}).join(' ');
      return (
        <div className="radar-chart-container">
          <svg width="280" height="280" viewBox="0 0 280 280">
            {[1,2,3,4,5].map(i=><circle key={\`g\${i}\`} cx={cx} cy={cy} r={i*20} fill="none" stroke="#E2E8F0" strokeWidth="1"/>)}
            {[0,72,144,216,288].map((a,i)=>{const r=(a-90)*Math.PI/180;return <line key={\`x\${i}\`} x1={cx} y1={cy} x2={cx+mr*Math.cos(r)} y2={cy+mr*Math.sin(r)} stroke="#E2E8F0" strokeWidth="1"/>})}
            <polygon points={points} fill="rgba(27,58,92,0.3)" stroke="#1B3A5C" strokeWidth="2"/>
            {items.map((item,i)=>{const a=(i*72-90)*Math.PI/180;const r=(item.value/100)*mr;return <circle key={\`p\${i}\`} cx={cx+r*Math.cos(a)} cy={cy+r*Math.sin(a)} r="6" fill="#1B3A5C" stroke="white" strokeWidth="2"/>})}
            {items.map((item,i)=>{const a=(i*72-90)*Math.PI/180;const x=cx+(mr+30)*Math.cos(a);const y=cy+(mr+30)*Math.sin(a);return <text key={\`l\${i}\`} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fill="#6B7B8D" fontSize="12">{item.name}</text>})}
          </svg>
        </div>
      );
    };

    // ===== TabBar =====
    const TabBar = ({ activeTab, onTabChange }) => {
      const tabs = [{id:'home',icon:HomeIcon,label:'首页'},{id:'history',icon:HistoryIcon,label:'历史'},{id:'profile',icon:ProfileIcon,label:'我的'}];
      return (
        <div className="tab-bar">
          {tabs.map(tab=>{const I=tab.icon;return <div key={tab.id} className={\`tab-item \${activeTab===tab.id?'active':''}\`} onClick={()=>onTabChange(tab.id)}><I/><span>{tab.label}</span></div>})}
        </div>
      );
    };

    // ===== PoweredByFooter =====
    const PoweredByFooter = () => (
      <div className="powered-by-footer">
        <a href="http://ritanai.com/" target="_blank" rel="noreferrer" className="ritanai-link">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/><path d="M8 4V8L11 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          <span>日坛AI提供技术支持</span>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M4 2L8 6L4 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </a>
      </div>
    );

    // ===== DoctorCarousel =====
    const doctors = [
      {id:1,name:'张明华',title:'主任医师',dept:'皮肤科',Avatar:DoctorAvatar1},
      {id:2,name:'李雅文',title:'副主任医师',dept:'医学美容科',Avatar:DoctorAvatar2},
      {id:3,name:'王志强',title:'主任医师',dept:'皮肤外科',Avatar:DoctorAvatar3},
      {id:4,name:'陈婉清',title:'主治医师',dept:'中西医结合科',Avatar:DoctorAvatar4},
      {id:5,name:'刘建国',title:'特邀专家',dept:'整形外科',Avatar:DoctorAvatar5},
    ];
    const DoctorCarousel = ({ onNavigate }) => {
      const [activeIndex, setActiveIndex] = useState(0);
      const [isDragging, setIsDragging] = useState(false);
      const [dragStart, setDragStart] = useState(0);
      const [dragOffset, setDragOffset] = useState(0);
      const trackRef = useRef(null);
      const autoPlayRef = useRef(null);
      const resetAutoPlay = useCallback(() => {
        if (autoPlayRef.current) clearInterval(autoPlayRef.current);
        autoPlayRef.current = setInterval(() => setActiveIndex(prev => (prev + 1) % doctors.length), 3000);
      }, []);
      useEffect(() => { resetAutoPlay(); return () => { if (autoPlayRef.current) clearInterval(autoPlayRef.current); }; }, [resetAutoPlay]);
      const goTo = useCallback((index) => { setActiveIndex(index); resetAutoPlay(); }, [resetAutoPlay]);
      const handleMouseDown = useCallback((e) => { e.preventDefault(); setIsDragging(true); setDragStart(e.clientX); setDragOffset(0); }, []);
      const handleMouseMove = useCallback((e) => { if (!isDragging) return; setDragOffset(e.clientX - dragStart); }, [isDragging, dragStart]);
      const handleMouseUp = useCallback(() => { if (!isDragging) return; setIsDragging(false); if (dragOffset < -40) goTo((activeIndex + 1) % doctors.length); else if (dragOffset > 40) goTo((activeIndex - 1 + doctors.length) % doctors.length); setDragOffset(0); }, [isDragging, dragOffset, activeIndex, goTo]);
      const handleTouchStart = useCallback((e) => { setIsDragging(true); setDragStart(e.touches[0].clientX); setDragOffset(0); }, []);
      const handleTouchMove = useCallback((e) => { if (!isDragging) return; setDragOffset(e.touches[0].clientX - dragStart); }, [isDragging, dragStart]);
      const handleTouchEnd = useCallback(() => { if (!isDragging) return; setIsDragging(false); if (dragOffset < -40) goTo((activeIndex + 1) % doctors.length); else if (dragOffset > 40) goTo((activeIndex - 1 + doctors.length) % doctors.length); setDragOffset(0); }, [isDragging, dragOffset, activeIndex, goTo]);
      const getCardStyle = (index) => {
        const diff = index - activeIndex;
        const isActive = diff === 0;
        const dragEffect = isDragging ? dragOffset : 0;
        let translateX = 0, opacity = 0, scale = 1, zIndex = 1;
        if (isActive) { translateX = dragEffect; opacity = 1; scale = 1; zIndex = 5; }
        else if (diff === 1 || diff === -(doctors.length - 1)) { translateX = 240 + dragEffect; opacity = 0.55; scale = 0.9; zIndex = 3; }
        else if (diff === -1 || diff === (doctors.length - 1)) { translateX = -240 + dragEffect; opacity = 0.55; scale = 0.9; zIndex = 3; }
        else if (Math.abs(diff) === 2) { translateX = diff > 0 ? 280 : -280; opacity = 0; scale = 0.8; zIndex = 1; }
        else { opacity = 0; translateX = 300; zIndex = 0; }
        return {
          transform: \`translateX(\${translateX}px) scale(\${scale})\`,
          opacity, zIndex,
          boxShadow: isActive ? '0 8px 24px rgba(27,58,92,0.18)' : '0 2px 8px rgba(27,58,92,0.06)',
          transition: isDragging ? 'none' : 'all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          pointerEvents: isActive ? 'auto' : 'none'
        };
      };
      return (
        <div className="doctor-carousel-section">
          <div className="doctor-carousel-title">专业医生在线问诊</div>
          <div className="doctor-carousel-track" ref={trackRef} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}>
            <div className="doctor-carousel-viewport">
              {doctors.map((doc,i)=>{const A=doc.Avatar;return(
                <div key={doc.id} className={\`doctor-card \${i===activeIndex?'active':''}\`} style={getCardStyle(i)} onClick={()=>{ if(i===activeIndex) onNavigate('guide'); }}>
                <div className="doctor-card-avatar"><A/></div>
                <div className="doctor-card-name">{doc.name}</div>
                <div className="doctor-card-title">{doc.title}</div>
                <div className="doctor-card-dept">{doc.dept}</div>
                <button className="doctor-card-btn">立即咨询</button>
              </div>
            )})}
            </div>
          </div>
          <div className="carousel-dots">{doctors.map((_,i)=><div key={i} className={\`carousel-dot \${i===activeIndex?'active':''}\`} onClick={()=>goTo(i)}/>)}</div>
          <div className="carousel-learn-more" onClick={()=>onNavigate('guide')}>
            <span>了解更多</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      );
    };

    // ===== ExpertConsultation =====
    const experts = [
      {id:1,name:'多学科专家联合会诊',desc:'汇聚三甲医院皮肤科、整形外科、中医科专家，为您定制个性化诊疗方案',icon:ExpertIcon},
      {id:2,name:'远程视频问诊服务',desc:'足不出户即可享受专家一对一面诊，支持图文、语音、视频多种问诊方式',icon:ConsultationIcon},
      {id:3,name:'术后跟踪管理',desc:'专家团队持续跟踪术后恢复情况，及时调整治疗方案，确保最佳恢复效果',icon:AppointmentIcon},
    ];
    const ExpertConsultation = () => (
      <div className="expert-section">
        <span className="section-badge" style={{background:'rgba(255,255,255,0.2)',color:'white'}}>特色服务</span>
        <div className="expert-section-title">订正生活 · 专家会诊</div>
        <div className="expert-section-subtitle">以专业医疗团队守护您的皮肤健康</div>
        <div className="expert-cards">
          {experts.map(item=>{const I=item.icon;return(
            <div key={item.id} className="expert-card">
              <div className="expert-card-icon"><I/></div>
              <div className="expert-card-info"><div className="expert-card-name">{item.name}</div><div className="expert-card-desc">{item.desc}</div></div>
              <div className="expert-card-arrow">›</div>
            </div>
          )})}
        </div>
      </div>
    );

    // ===== CaseDisplay (Carousel) =====
    const cases = [
      {id:1,tag:'痤疮治疗',tagClass:'case-tag-acne',title:'重度痤疮综合治疗方案',desc:'经过3个月中西医结合治疗，面部痤疮明显消退，皮肤恢复光滑'},
      {id:2,tag:'色斑淡化',tagClass:'case-tag-spot',title:'黄褐斑激光联合治疗',desc:'光子嫩肤+中药调理，色斑面积减少80%，肤色均匀透亮'},
      {id:3,tag:'抗衰老',tagClass:'case-tag-aging',title:'面部年轻化综合方案',desc:'热玛吉+玻尿酸填充，面部轮廓提升，皱纹深度减少50%'},
      {id:4,tag:'疤痕修复',tagClass:'case-tag-acne',title:'痤疮疤痕综合修复方案',desc:'点阵激光+微针联合治疗，疤痕明显淡化，皮肤质地显著改善'},
      {id:5,tag:'敏感肌修复',tagClass:'case-tag-spot',title:'面部敏感肌屏障修复',desc:'舒敏治疗+医用修复产品，皮肤屏障功能恢复，泛红干痒消退'},
    ];
    const CaseDisplay = () => {
      const [activeIndex, setActiveIndex] = React.useState(0);
      const [isDragging, setIsDragging] = React.useState(false);
      const [dragStart, setDragStart] = React.useState(0);
      const [dragOffset, setDragOffset] = React.useState(0);
      const trackRef = React.useRef(null);
      const autoPlayRef = React.useRef(null);
      const resetAutoPlay = React.useCallback(() => {
        if (autoPlayRef.current) clearInterval(autoPlayRef.current);
        autoPlayRef.current = setInterval(() => { setActiveIndex(prev => (prev + 1) % cases.length); }, 3000);
      }, []);
      React.useEffect(() => { resetAutoPlay(); return () => clearInterval(autoPlayRef.current); }, [resetAutoPlay]);
      const goTo = React.useCallback((index) => { setActiveIndex(index); resetAutoPlay(); }, [resetAutoPlay]);
      const handleMouseDown = React.useCallback((e) => { e.preventDefault(); setIsDragging(true); setDragStart(e.clientX); setDragOffset(0); }, []);
      const handleMouseMove = React.useCallback((e) => { if (!isDragging) return; setDragOffset(e.clientX - dragStart); }, [isDragging, dragStart]);
      const handleMouseUp = React.useCallback(() => { if (!isDragging) return; setIsDragging(false); if (dragOffset < -40) { goTo((activeIndex + 1) % cases.length); } else if (dragOffset > 40) { goTo((activeIndex - 1 + cases.length) % cases.length); } setDragOffset(0); }, [isDragging, dragOffset, activeIndex, goTo]);
      const handleTouchStart = React.useCallback((e) => { setIsDragging(true); setDragStart(e.touches[0].clientX); setDragOffset(0); }, []);
      const handleTouchMove = React.useCallback((e) => { if (!isDragging) return; setDragOffset(e.touches[0].clientX - dragStart); }, [isDragging, dragStart]);
      const handleTouchEnd = React.useCallback(() => { if (!isDragging) return; setIsDragging(false); if (dragOffset < -40) { goTo((activeIndex + 1) % cases.length); } else if (dragOffset > 40) { goTo((activeIndex - 1 + cases.length) % cases.length); } setDragOffset(0); }, [isDragging, dragOffset, activeIndex, goTo]);
      const getCardStyle = (index) => {
        const diff = index - activeIndex, isActive = diff === 0, dragEffect = isDragging ? dragOffset : 0;
        let translateX = 0, opacity = 0, scale = 1, zIndex = 1;
        if (isActive) { translateX = dragEffect; opacity = 1; scale = 1; zIndex = 5; }
        else if (diff === 1 || diff === -(cases.length - 1)) { translateX = 270 + dragEffect; opacity = 0.55; scale = 0.9; zIndex = 3; }
        else if (diff === -1 || diff === (cases.length - 1)) { translateX = -270 + dragEffect; opacity = 0.55; scale = 0.9; zIndex = 3; }
        else if (Math.abs(diff) === 2) { translateX = diff > 0 ? 290 : -290; opacity = 0; scale = 0.8; zIndex = 1; }
        else { opacity = 0; translateX = 310; zIndex = 0; }
        return { transform: \`translateX(\${translateX}px) scale(\${scale})\`, opacity, zIndex, boxShadow: isActive ? '0 8px 24px rgba(27,58,92,0.18)' : '0 2px 8px rgba(27,58,92,0.06)', transition: isDragging ? 'none' : 'all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)', pointerEvents: isActive ? 'auto' : 'none' };
      };
      return (
        <div className="case-carousel-section">
          <div className="case-carousel-title">诊断案例展示</div>
          <div className="case-carousel-track" ref={trackRef} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}>
            <div className="case-carousel-viewport">
              {cases.map((c,index) => (
                <div key={c.id} className={\`case-carousel-card \${index===activeIndex?'active':''}\`} style={getCardStyle(index)}>
                  <div className="case-card-images">
                    <div className="case-img-half"><span className="case-img-label case-label-before">BEFORE</span>
                      <svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="38" r="22" fill="#E8C8C0"/><circle cx="34" cy="34" r="3" fill="#C0392B" opacity="0.5"/><circle cx="46" cy="34" r="3" fill="#C0392B" opacity="0.5"/><circle cx="38" cy="44" r="2" fill="#C0392B" opacity="0.4"/><circle cx="44" cy="44" r="2" fill="#C0392B" opacity="0.4"/></svg>
                    </div>
                    <div className="case-img-half"><span className="case-img-label case-label-after">AFTER</span>
                      <svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="38" r="22" fill="#F5E0D0"/><circle cx="34" cy="34" r="2.5" fill="#8D6E63" opacity="0.3"/><circle cx="46" cy="34" r="2.5" fill="#8D6E63" opacity="0.3"/><path d="M32 48C35 51 45 51 48 48" stroke="#8D6E63" strokeWidth="1.5" opacity="0.4" fill="none"/></svg>
                    </div>
                  </div>
                  <div className="case-card-body"><span className={\`case-card-tag \${c.tagClass}\`}>{c.tag}</span><div className="case-card-title">{c.title}</div><div className="case-card-desc">{c.desc}</div></div>
                </div>
              ))}
            </div>
          </div>
          <div className="carousel-dots">{cases.map((_,i)=><div key={i} className={\`carousel-dot \${i===activeIndex?'active':''}\`} onClick={()=>goTo(i)}/>)}</div>
          <div className="carousel-learn-more">
            <span>开启蜕变</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M9 18L15 12L9 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      );
    };

    // ===== Statistics =====
    const stats = [
      {id:1,value:'500+',label:'三甲专家',Icon:UsersIcon},{id:2,value:'98%',label:'好评率',Icon:SatisfactionIcon},
      {id:3,value:'200+',label:'覆盖城市',Icon:CityIcon},{id:4,value:'10年',label:'安全保障',Icon:ShieldIcon},
    ];
    const Statistics = () => (
      <div className="stats-section">
        <div className="stats-big-number">500,000+</div>
        <div className="stats-big-label">累计服务用户信赖之选</div>
        <div className="stats-grid-new">
          {stats.map(s=>{const I=s.Icon;return(<div key={s.id} className="stat-card-new"><div className="stat-card-new-icon"><I/></div><span className="stat-card-new-value">{s.value}</span><span className="stat-card-new-label">{s.label}</span></div>)})}
        </div>
      </div>
    );

    // ===== Advantages =====
    const steps = [
      {id:1,icon:CameraIcon,title:'智能检测',desc:'多角度面部高清图像采集，AI精准定位皮肤问题区域'},
      {id:2,icon:AIIcon,title:'AI分析',desc:'深度学习算法分析皮肤状态，Glogau分级专业评估'},
      {id:3,icon:ReportIcon,title:'专业报告',desc:'生成详细皮肤分析报告，包含各项指标及改善建议'},
      {id:4,icon:ChatIcon,title:'在线问诊',desc:'直接连线三甲专家，获取个性化诊疗方案和用药指导'},
    ];
    const Advantages = ({ onNavigate }) => (
      <div className="advantages-section">
        <span className="section-badge">服务流程</span>
        <div className="advantages-title">AI智能检测 · 专业诊疗服务</div>
        <div className="advantages-subtitle">从检测到治疗，一站式皮肤健康管理</div>
        <div className="advantages-grid">
          {steps.map(step=>{const I=step.icon;return(
            <div key={step.id} className="advantage-card" onClick={()=>step.id===1?onNavigate('guide'):null}>
              <div className="advantage-card-icon"><I/></div>
              <div className="advantage-card-title">{step.title}</div>
              <div className="advantage-card-desc">{step.desc}</div>
            </div>
          )})}
        </div>
      </div>
    );

    // ===== DoctorRecommendation =====
    const recDoctors = [
      {id:1,name:'张明华 主任医师',badge:'特邀专家',specialty:'皮肤科 · 痤疮与面部年轻化',desc:'从事皮肤科临床工作30余年，擅长中西医结合治疗各类皮肤问题',plan:'痤疮综合治疗方案',Avatar:DoctorAvatar1},
      {id:2,name:'李雅文 副主任医师',badge:'金牌医生',specialty:'医学美容科 · 激光美容',desc:'擅长色素性疾病、血管性疾病的激光治疗及面部年轻化综合设计',plan:'色斑淡化定制方案',Avatar:DoctorAvatar2},
      {id:3,name:'王志强 主任医师',badge:'学科带头人',specialty:'皮肤外科 · 疤痕修复',desc:'在皮肤肿瘤、疤痕修复及创面愈合领域具有丰富的临床经验',plan:'疤痕修复综合方案',Avatar:DoctorAvatar3},
    ];
    const DoctorRecommendation = ({ onNavigate }) => (
      <div className="doctor-recommend-section">
        <span className="section-badge">专家推荐</span>
        <div className="doctor-recommend-title">方案与医生推荐</div>
        <div className="doctor-recommend-subtitle">特邀专家为您规划诊断结果</div>
        <div className="recommend-cards">
          {recDoctors.map(doc=>{const A=doc.Avatar;return(
            <div key={doc.id} className="recommend-card">
              <div className="recommend-avatar"><A/></div>
              <div className="recommend-info">
                <div className="recommend-name">{doc.name}<span style={{marginLeft:6}}><StarIcon/><StarIcon/><StarIcon/><StarIcon/><StarIcon/></span></div>
                <span className="recommend-badge recommend-badge-expert">{doc.badge}</span>
                <div className="recommend-specialty">{doc.specialty}</div>
                <div className="recommend-desc">{doc.desc}</div>
                <span className="recommend-plan">{'📋 '}{doc.plan}</span>
              </div>
              <div className="recommend-actions">
                <button className="recommend-btn recommend-btn-primary" onClick={()=>onNavigate('guide')}>预约咨询</button>
                <button className="recommend-btn recommend-btn-outline" onClick={()=>onNavigate('guide')}>查看方案</button>
              </div>
            </div>
          )})}
        </div>
      </div>
    );

    // ===== AppFooter =====
    const AppFooter = () => (
      <div className="app-footer">
        <div className="footer-cta"><div className="footer-cta-title">下载兰峤医疗APP</div><div className="footer-cta-desc">专属陪诊服务，随时随地守护您的健康</div><button className="footer-download-btn"><DownloadIcon/>立即下载</button></div>
        <div className="footer-contact"><div className="footer-contact-item"><PhoneIcon/>400-888-6688</div><div className="footer-contact-item"><PhoneIcon/>在线客服</div></div>
        <hr className="footer-divider"/>
        <div className="footer-bottom">
          <div className="footer-brand"><LogoLarge/><span className="footer-brand-name">兰峤医疗</span></div>
          <div className="footer-copyright">{'© 2026 兰峤医疗科技 版权所有\n沪ICP备2023003282号-38 | 沪公网安备31010402010179号'}</div>
          <div className="footer-links"><span className="footer-link">用户协议</span><span className="footer-link">隐私政策</span><span className="footer-link">关于我们</span></div>
        </div>
      </div>
    );

    // ===== HomePage =====
    const HomePage = ({ onNavigate }) => (
      <div className="page lq-home-page">
        <div className="lq-hero">
          <div className="lq-hero-brand-row"><span className="lq-hero-brand-name">兰峤医疗</span></div>
          <div className="lq-hero-tagline">「互联网问诊」皮肤品牌</div>
          <div className="lq-hero-divider"></div>
          <div className="lq-hero-tags"><span className="lq-hero-tag">AI专业诊断</span><span className="lq-hero-tag">皮肤精准评估</span></div>
          <div className="lq-face-wrap"><img src={DOCTOR_IMG_1} alt="AI皮肤检测" className="lq-face-img"/><div className="lq-face-glow"></div></div>
          <button className="lq-main-cta" onClick={()=>onNavigate('guide')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{marginRight:8}}><circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2"/><path d="M10 8L16 12L10 16V8Z" fill="white"/></svg>
            马上诊断
          </button>
        </div>
        <div className="lq-doctors-section">
          <div className="lq-doctor-card">
            <img src={DOCTOR_IMG_2} alt="痘肌专家" className="lq-doctor-img"/>
            <div className="lq-doctor-info"><div className="lq-doctor-label">痘肌专家在线</div><div className="lq-doctor-desc">皮肤科主任医师，三甲医院<br/>15年痤疮治疗经验</div><button className="lq-doctor-btn lq-btn-blue" onClick={()=>onNavigate('guide')}>去咨询</button></div>
          </div>
          <div className="lq-doctor-card">
            <img src={DOCTOR_IMG_3} alt="三甲皮肤科医生" className="lq-doctor-img lq-doctor-img-right"/>
            <div className="lq-doctor-info"><div className="lq-doctor-label">三甲皮肤科医生</div><div className="lq-doctor-desc">副主任医师，专业医学美容<br/>精准评估皮肤衰老</div><button className="lq-doctor-btn lq-btn-outline" onClick={()=>onNavigate('guide')}>预约问诊</button></div>
          </div>
        </div>
        <DoctorCarousel onNavigate={onNavigate}/>
        <CaseDisplay/>
        <Statistics/>
        <Advantages onNavigate={onNavigate}/>
        <ExpertConsultation/>
        <DoctorRecommendation onNavigate={onNavigate}/>
        <AppFooter/>
        <div className="tab-bar">
          <div className="tab-item active"><HomeIcon/><span>首页</span></div>
          <div className="tab-item" onClick={()=>onNavigate('history')}><HistoryIcon/><span>历史</span></div>
          <div className="tab-item" onClick={()=>onNavigate('profile')}><ProfileIcon/><span>我的</span></div>
        </div>
      </div>
    );

    // ===== GuidePage =====
    const GuidePage = ({ onNavigate }) => {
      const [currentStep, setCurrentStep] = useState(0);
      const guideSteps = [
        {title:'环境准备',description:'确保在光线充足的环境下进行拍摄',icon:<svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="40" r="35" fill="#D6EAF8"/><circle cx="40" cy="35" r="15" stroke="#1B3A5C" strokeWidth="3" fill="none"/><path d="M40 50V70" stroke="#1B3A5C" strokeWidth="3" strokeLinecap="round"/></svg>},
        {title:'角度调整',description:'按照引导框调整面部角度，分别拍摄正面和左右侧45°',icon:<svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="40" r="35" fill="#E8F5E9"/><path d="M25 55L40 30L55 55" stroke="#4CAF50" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/><circle cx="40" cy="30" r="5" fill="#4CAF50"/></svg>},
        {title:'开始检测',description:'准备好后点击下方按钮开始AI皮肤检测',icon:<svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="40" r="35" fill="#E3F2FD"/><circle cx="40" cy="40" r="15" stroke="#2196F3" strokeWidth="3" fill="none"/><path d="M40 30V40L48 44" stroke="#2196F3" strokeWidth="3" strokeLinecap="round"/></svg>}
      ];
      const handleNext = () => { if (currentStep < guideSteps.length - 1) setCurrentStep(currentStep + 1); else onNavigate('capture'); };
      return (
        <div className="page guide-page">
          <div className="page-header"><div className="back-btn" onClick={()=>onNavigate('home')}><BackIcon/></div><span className="page-title">拍摄引导</span><div style={{width:40}}></div></div>
          <div className="guide-content">
            <div className="step-indicators">{guideSteps.map((_,i)=><div key={i} className={\`step-dot \${i===currentStep?'active':''} \${i<currentStep?'completed':''}\`}/>)}</div>
            <div className="step-content animate-fadeIn" key={currentStep}><div className="step-icon">{guideSteps[currentStep].icon}</div><span className="step-title">{guideSteps[currentStep].title}</span><span className="step-description">{guideSteps[currentStep].description}</span></div>
            <div className="notice-section"><span className="notice-title">注意事项</span><div className="notice-list"><div className="notice-item"><WarningIcon/><span>保持面部清洁，不要化妆</span></div><div className="notice-item"><WarningIcon/><span>头发扎起，露出完整面部</span></div></div></div>
            <div className="privacy-notice"><PrivacyIcon/><span className="privacy-text">您的图像数据将加密处理，仅用于皮肤分析</span></div>
          </div>
          <div className="guide-footer"><button className="btn btn-primary btn-large btn-block" onClick={handleNext}>{currentStep===guideSteps.length-1?'开始检测':'下一步'}</button></div>
        </div>
      );
    };

    // ===== CapturePage =====
    const CapturePage = ({ onNavigate }) => {
      const [currentAngle, setCurrentAngle] = useState(0);
      const [capturedImages, setCapturedImages] = useState([]);
      const [isCapturing, setIsCapturing] = useState(false);
      const handleCapture = async () => {
        setIsCapturing(true);
        await new Promise(r=>setTimeout(r,500));
        const mockImage = \`data:image/svg+xml,\${encodeURIComponent(\`<svg width="300" height="400" xmlns="http://www.w3.org/2000/svg"><rect width="300" height="400" fill="#1A2A3A"/><circle cx="150" cy="180" r="80" fill="#4A4543"/><text x="150" y="200" text-anchor="middle" fill="#6B7B8D" font-size="14">\${CAPTURE_ANGLES[currentAngle].name}</text></svg>\`)}\`;
        const newImages = [...capturedImages, mockImage];
        setCapturedImages(newImages);
        setIsCapturing(false);
        if (currentAngle < CAPTURE_ANGLES.length - 1) setCurrentAngle(currentAngle + 1);
      };
      const isAllCaptured = capturedImages.length === CAPTURE_ANGLES.length;
      return (
        <div className="page capture-page">
          <div className="capture-header"><div className="back-btn" onClick={()=>onNavigate('guide')}><BackIcon/></div><span className="capture-title">面部图像采集</span><div style={{width:40}}></div></div>
          <div className="capture-content">
            <div className="angle-progress">{CAPTURE_ANGLES.map((a,i)=><div key={i} className={\`angle-step \${i===currentAngle?'active':''} \${i<currentAngle||capturedImages[i]?'completed':''}\`}><div className="angle-number">{capturedImages[i]?'✓':i+1}</div><span className="angle-name">{a.name}</span></div>)}</div>
            <div className="preview-container">
              <div className="preview-frame">
                {capturedImages[currentAngle]?<img src={capturedImages[currentAngle]} className="preview-image" alt="preview"/>:<div className="preview-placeholder"><svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="40" r="30" stroke="#666" strokeWidth="3" strokeDasharray="8 4"/><circle cx="40" cy="35" r="10" stroke="#666" strokeWidth="2"/></svg><span className="placeholder-text">请拍摄{CAPTURE_ANGLES[currentAngle].name}</span></div>}
                {!capturedImages[currentAngle]&&<div className="guide-overlay"><div className="guide-box"><div className="guide-corner top-left"></div><div className="guide-corner top-right"></div><div className="guide-corner bottom-left"></div><div className="guide-corner bottom-right"></div></div></div>}
              </div>
            </div>
            {capturedImages.length>0&&<div className="thumbnails">{capturedImages.map((img,i)=><div key={i} className="thumbnail-item"><img src={img} className="thumbnail-image" alt={\`thumb-\${i}\`}/></div>)}</div>}
            <div className="capture-tip"><span className="tip-text">{capturedImages[currentAngle]?\`\${CAPTURE_ANGLES[currentAngle].name}已采集\${currentAngle<CAPTURE_ANGLES.length-1?'，请继续下一个角度':'，可以开始分析'}\`:'请将面部对准框内，保持正对镜头'}</span></div>
          </div>
          <div className="capture-footer">
            {isAllCaptured?<button className="btn btn-secondary btn-large btn-block" onClick={()=>onNavigate('analysis')}>开始AI分析</button>:
            <div className="capture-btn-container"><button className={\`capture-btn \${isCapturing?'capturing':''}\`} onClick={handleCapture} disabled={isCapturing}><div className="capture-btn-inner">{isCapturing?<div className="capture-loading"></div>:<svg width="32" height="32" viewBox="0 0 32 32" fill="none"><circle cx="16" cy="16" r="14" fill="white"/></svg>}</div></button><span className="capture-hint">点击拍照</span></div>}
          </div>
        </div>
      );
    };

    // ===== AnalysisPage =====
    const AnalysisPage = ({ onNavigate }) => {
      const [progress, setProgress] = useState(0);
      const [currentStep, setCurrentStep] = useState(0);
      useEffect(()=>{
        const totalTime = ANALYSIS_STEPS.length * 400;
        const interval = setInterval(()=>{setProgress(prev=>{if(prev>=100){clearInterval(interval);setTimeout(()=>onNavigate('report',{analysisData:generateMockAnalysisData()}),500);return 100;}return prev+1;})},totalTime/100);
        ANALYSIS_STEPS.forEach((_,i)=>setTimeout(()=>setCurrentStep(i),i*400));
        return ()=>clearInterval(interval);
      },[onNavigate]);
      return (
        <div className="page analysis-page">
          <div className="analysis-content">
            <div className="analysis-animation"><div className="analysis-circle"><svg width="140" height="140" viewBox="0 0 140 140"><circle cx="70" cy="70" r="60" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="8"/><circle cx="70" cy="70" r="60" fill="none" stroke="white" strokeWidth="8" strokeLinecap="round" strokeDasharray={\`\${2*Math.PI*60}\`} strokeDashoffset={\`\${2*Math.PI*60*(1-progress/100)}\`} transform="rotate(-90 70 70)"/><text x="70" y="65" textAnchor="middle" fontSize="36" fontWeight="bold" fill="white">{progress}%</text><text x="70" y="90" textAnchor="middle" fontSize="14" fill="rgba(255,255,255,0.7)">分析中</text></svg></div></div>
            <div className="analysis-steps">{ANALYSIS_STEPS.map((step,i)=><div key={i} className={\`analysis-step \${i<currentStep?'completed':''} \${i===currentStep?'active':''}\`}><div className="step-indicator">{i<currentStep?'✓':i===currentStep?<div className="step-spinner"></div>:'○'}</div><span className="step-name">{step}</span></div>)}</div>
          </div>
        </div>
      );
    };

    // ===== ReportPage =====
    const ReportPage = ({ onNavigate, data }) => {
      const analysisData = data?.analysisData || generateMockAnalysisData();
      const metrics = [
        {name:'皱纹分析',value:analysisData.wrinkles,color:'#1B3A5C',desc:analysisData.wrinkles>=70?'皱纹较少，皮肤平滑':analysisData.wrinkles>=50?'轻度皱纹，注意保养':'皱纹明显，建议加强护理'},
        {name:'色斑检测',value:analysisData.spots,color:'#2E86C1',desc:analysisData.spots>=70?'色斑较少，皮肤均匀':analysisData.spots>=50?'轻度色斑，需要注意':'色斑明显，建议治疗'},
        {name:'弹性评估',value:analysisData.elasticity,color:'#4DA8DA',desc:analysisData.elasticity>=70?'弹性良好，皮肤紧致':analysisData.elasticity>=50?'轻度松弛，需要护理':'弹性下降明显'},
        {name:'毛孔状况',value:analysisData.pores,color:'#FF9800',desc:analysisData.pores>=70?'毛孔细腻，皮肤光滑':analysisData.pores>=50?'毛孔轻微粗大':'毛孔粗大明显'}
      ];
      return (
        <div className="page report-page">
          <div className="page-header"><div className="back-btn" onClick={()=>onNavigate('home')}><BackIcon/></div><span className="page-title">皮肤分析报告</span><div style={{width:40}}></div></div>
          <div className="report-content">
            <div className="card animate-fadeIn"><div className="score-header"><span className="score-label">综合评分</span><span className="score-date">{analysisData.analysisDate}</span></div><div className="score-display"><div className="score-circle"><ScoreCircle score={analysisData.score}/></div><div className="score-info"><span className="glogau-level">{analysisData.glogauLevel}</span><span className="glogau-desc">{analysisData.glogauDescription}</span></div></div></div>
            <div className="card animate-fadeIn" style={{animationDelay:'0.1s'}}><span className="card-title">皮肤状态雷达图</span><RadarChart data={analysisData}/></div>
            <div className="card animate-fadeIn" style={{animationDelay:'0.2s'}}><span className="card-title">详细评估指标</span>{metrics.map((item,i)=><div key={i} className="metric-item"><div className="metric-header"><span className="metric-name">{item.name}</span><span className="metric-value">{item.value}分</span></div><div className="metric-bar"><div className="metric-fill" style={{width:\`\${item.value}%\`,backgroundColor:item.color}}/></div><span className="metric-desc">{item.desc}</span></div>)}</div>
            <div className="card animate-fadeIn" style={{animationDelay:'0.3s'}}><span className="card-title">个性化护肤建议</span>{analysisData.recommendations.map((rec,i)=><div key={i} className="recommendation-item"><div className="rec-number">{i+1}</div><span className="rec-text">{rec}</span></div>)}</div>
            <div className="report-actions"><button className="btn btn-outline" onClick={()=>onNavigate('home')}>返回首页</button><button className="btn btn-primary" onClick={()=>alert('分享功能开发中')}>分享报告</button></div>
          </div>
        </div>
      );
    };

    // ===== HistoryPage =====
    const HistoryPage = ({ onNavigate }) => {
      const [records] = useState([
        {id:'1',type:'aging',date:'2026-04-25',score:78,summary:'轻度光老化，皮肤状态良好'},
        {id:'2',type:'aging',date:'2026-04-20',score:72,summary:'中度光老化，建议加强护理'},
        {id:'3',type:'postSurgery',date:'2026-04-15',score:65,summary:'术后恢复中，愈合进度正常'},
        {id:'4',type:'aging',date:'2026-04-10',score:75,summary:'皮肤状态有所改善'}
      ]);
      const handleTabChange = (tabId) => { if (tabId==='history') return; onNavigate(tabId); };
      return (
        <div className="page history-page">
          <div className="page-header"><div className="back-btn" onClick={()=>onNavigate('home')}><BackIcon/></div><span className="page-title">检测历史</span><div style={{width:40}}></div></div>
          <div className="history-content"><div className="records-list">{records.map(record=><div key={record.id} className="card record-card" onClick={()=>onNavigate('report',{analysisData:generateMockAnalysisData()})}><div className="record-header"><span className={\`record-type-badge \${record.type}\`}>{record.type==='aging'?'衰老评估':'术后监测'}</span><span className="record-date">{record.date}</span></div><div className="record-body"><div className="record-score"><span className="score-value">{record.score}</span><span style={{fontSize:14,color:'#6B7B8D'}}>分</span></div><span className="record-summary">{record.summary}</span></div></div>)}</div></div>
          <TabBar activeTab="history" onTabChange={handleTabChange}/>
        </div>
      );
    };

    // ===== ProfilePage =====
    const ProfilePage = ({ onNavigate }) => {
      const handleTabChange = (tabId) => { if (tabId==='profile') return; onNavigate(tabId); };
      const menuItems = [
        {id:'newDetection',icon:<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M19 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3Z" stroke="#1B3A5C" strokeWidth="2"/><path d="M12 8V16M8 12H16" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/></svg>,title:'新建检测'},
        {id:'about',icon:<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 2L15 8L22 9L17 14L18 21L12 18L6 21L7 14L2 9L9 8L12 2Z" stroke="#1B3A5C" strokeWidth="2"/></svg>,title:'关于我们'},
        {id:'privacy',icon:<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="11" width="18" height="11" rx="2" stroke="#1B3A5C" strokeWidth="2"/><path d="M7 11V7C7 4.239 9.239 2 12 2C14.761 2 17 4.239 17 7V11" stroke="#1B3A5C" strokeWidth="2"/></svg>,title:'隐私政策'},
        {id:'ritanai',icon:<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="#1B3A5C" strokeWidth="2"/><path d="M12 6V12L16 14" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round"/></svg>,title:'日坛AI提供技术支持',isExternal:true}
      ];
      return (
        <div className="page profile-page">
          <div className="page-header"><div className="back-btn" onClick={()=>onNavigate('home')}><BackIcon/></div><span className="page-title">个人中心</span><div style={{width:40}}></div></div>
          <div className="profile-content">
            <div className="card user-card"><div className="user-avatar-large"><svg width="80" height="80" viewBox="0 0 80 80" fill="none"><circle cx="40" cy="40" r="36" fill="#F5F5F5" stroke="#E0E0E0" strokeWidth="2"/><circle cx="40" cy="30" r="14" fill="#BDBDBD"/><path d="M16 64C16 52.954 25.954 44 40 44C54.046 44 64 52.954 64 64" fill="#BDBDBD"/></svg></div><div className="user-info"><span className="user-name">兰峤用户</span><span className="user-id">ID: LJQ20260426</span></div></div>
            <div className="stats-grid"><div className="stat-item"><span className="stat-value">5</span><span className="stat-label">检测次数</span></div><div className="stat-item"><span className="stat-value">78</span><span className="stat-label">最新评分</span></div><div className="stat-item"><span className="stat-value">30</span><span className="stat-label">连续天数</span></div></div>
            <div className="card menu-section">{menuItems.map(item=><div key={item.id} className="menu-item" onClick={()=>{if(item.isExternal) window.open('http://ritanai.com/','_blank');}}><div className="menu-left">{item.icon}<span>{item.title}</span></div><ArrowIcon/></div>)}</div>
          </div>
          <TabBar activeTab="profile" onTabChange={handleTabChange}/>
        </div>
      );
    };

    // ===== App =====
    function App() {
      const [currentPage, setCurrentPage] = useState('home');
      const [pageData, setPageData] = useState(null);
      const handleNavigate = useCallback((page, data) => { setCurrentPage(page); if (data) setPageData(data); }, []);
      return (
        <div className="app-wrapper">
          {currentPage==='home' && <HomePage onNavigate={handleNavigate}/>}
          {currentPage==='guide' && <GuidePage onNavigate={handleNavigate}/>}
          {currentPage==='capture' && <CapturePage onNavigate={handleNavigate}/>}
          {currentPage==='analysis' && <AnalysisPage onNavigate={handleNavigate}/>}
          {currentPage==='report' && <ReportPage onNavigate={handleNavigate} data={pageData}/>}
          {currentPage==='history' && <HistoryPage onNavigate={handleNavigate}/>}
          {currentPage==='profile' && <ProfilePage onNavigate={handleNavigate}/>}
          {currentPage!=='home' && <PoweredByFooter/>}
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
  <\/script>
</body>
</html>`;

fs.writeFileSync(path.join(__dirname, 'dist/index.html'), html, 'utf8');
console.log('dist/index.html generated successfully!');
console.log('Size: ' + (Buffer.byteLength(html, 'utf8') / 1024).toFixed(1) + ' KB');
