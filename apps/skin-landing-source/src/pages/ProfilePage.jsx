import React from 'react';
import { BackIcon, ArrowIcon } from '../components/Icons';
import TabBar from '../components/TabBar';

/**
 * 个人中心页
 * 展示用户信息和设置选项
 */
const ProfilePage = ({ onNavigate }) => {
  const handleTabChange = (tabId) => {
    if (tabId === 'profile') return;
    onNavigate(tabId);
  };

  const menuItems = [
    {
      id: 'newDetection',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M19 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3Z"
            stroke="#1B3A5C"
            strokeWidth="2"
          />
          <path d="M12 8V16M8 12H16" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ),
      title: '新建检测'
    },
    {
      id: 'about',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2L15 8L22 9L17 14L18 21L12 18L6 21L7 14L2 9L9 8L12 2Z"
            stroke="#1B3A5C"
            strokeWidth="2"
          />
        </svg>
      ),
      title: '关于我们'
    },
    {
      id: 'privacy',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="11" width="18" height="11" rx="2" stroke="#1B3A5C" strokeWidth="2" />
          <path
            d="M7 11V7C7 4.239 9.239 2 12 2C14.761 2 17 4.239 17 7V11"
            stroke="#1B3A5C"
            strokeWidth="2"
          />
        </svg>
      ),
      title: '隐私政策'
    },
    {
      id: 'ritanai',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="#1B3A5C" strokeWidth="2" />
          <path d="M12 6V12L16 14" stroke="#1B3A5C" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ),
      title: '日坛AI提供技术支持',
      isExternal: true
    }
  ];

  return (
    <div className="page profile-page">
      {/* 页面头部 */}
      <div className="page-header">
        <div className="back-btn" onClick={() => onNavigate('home')}>
          <BackIcon />
        </div>
        <span className="page-title">个人中心</span>
        <div style={{ width: 40 }}></div>
      </div>

      {/* 用户信息 */}
      <div className="profile-content">
        <div className="card user-card">
          <div className="user-avatar-large">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
              <circle cx="40" cy="40" r="36" fill="#F5F5F5" stroke="#E0E0E0" strokeWidth="2" />
              <circle cx="40" cy="30" r="14" fill="#BDBDBD" />
              <path d="M16 64C16 52.954 25.954 44 40 44C54.046 44 64 52.954 64 64" fill="#BDBDBD" />
            </svg>
          </div>
          <div className="user-info">
            <span className="user-name">兰峤用户</span>
            <span className="user-id">ID: LJQ20260426</span>
          </div>
        </div>

        {/* 统计数据 */}
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-value">5</span>
            <span className="stat-label">检测次数</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">78</span>
            <span className="stat-label">最新评分</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">30</span>
            <span className="stat-label">连续天数</span>
          </div>
        </div>

        {/* 菜单列表 */}
        <div className="card menu-section">
          {menuItems.map(item => (
            <div
              key={item.id}
              className="menu-item"
              onClick={() => {
                if (item.isExternal) {
                  window.open('http://ritanai.com/', '_blank');
                } else {
                  // 其他菜单项的处理逻辑
                }
              }}
            >
              <div className="menu-left">
                {item.icon}
                <span>{item.title}</span>
              </div>
              <ArrowIcon />
            </div>
          ))}
        </div>
      </div>

      {/* 底部导航 */}
      <TabBar activeTab="profile" onTabChange={handleTabChange} />
    </div>
  );
};

export default ProfilePage;
