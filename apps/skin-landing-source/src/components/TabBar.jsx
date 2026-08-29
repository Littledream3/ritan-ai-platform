import React from 'react';
import { HomeIcon, HistoryIcon, ProfileIcon } from './Icons';

/**
 * 底部导航栏组件
 * @param {Object} props
 * @param {string} props.activeTab - 当前激活的标签
 * @param {Function} props.onTabChange - 标签切换回调
 */
const TabBar = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'home', icon: HomeIcon, label: '首页' },
    { id: 'history', icon: HistoryIcon, label: '历史' },
    { id: 'profile', icon: ProfileIcon, label: '我的' }
  ];

  return (
    <div className="tab-bar">
      {tabs.map(tab => {
        const IconComponent = tab.icon;
        return (
          <div
            key={tab.id}
            className={`tab-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <IconComponent />
            <span>{tab.label}</span>
          </div>
        );
      })}
    </div>
  );
};

export default TabBar;
