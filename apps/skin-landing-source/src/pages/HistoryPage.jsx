import React, { useState } from 'react';
import { BackIcon } from '../components/Icons';
import { generateMockAnalysisData } from '../utils/mockData';
import TabBar from '../components/TabBar';

/**
 * 历史记录页
 * 展示历史检测记录
 */
const HistoryPage = ({ onNavigate }) => {
  const [records] = useState([
    {
      id: '1',
      type: 'aging',
      date: '2026-04-25',
      score: 78,
      summary: '轻度光老化，皮肤状态良好'
    },
    {
      id: '2',
      type: 'aging',
      date: '2026-04-20',
      score: 72,
      summary: '中度光老化，建议加强护理'
    },
    {
      id: '3',
      type: 'postSurgery',
      date: '2026-04-15',
      score: 65,
      summary: '术后恢复中，愈合进度正常'
    },
    {
      id: '4',
      type: 'aging',
      date: '2026-04-10',
      score: 75,
      summary: '皮肤状态有所改善'
    }
  ]);

  const handleTabChange = (tabId) => {
    if (tabId === 'history') return;
    onNavigate(tabId);
  };

  const handleRecordClick = (record) => {
    onNavigate('report', { analysisData: generateMockAnalysisData() });
  };

  return (
    <div className="page history-page">
      {/* 页面头部 */}
      <div className="page-header">
        <div className="back-btn" onClick={() => onNavigate('home')}>
          <BackIcon />
        </div>
        <span className="page-title">检测历史</span>
        <div style={{ width: 40 }}></div>
      </div>

      {/* 历史列表 */}
      <div className="history-content">
        <div className="records-list">
          {records.map(record => (
            <div
              key={record.id}
              className="card record-card"
              onClick={() => handleRecordClick(record)}
            >
              <div className="record-header">
                <span className={`record-type-badge ${record.type}`}>
                  {record.type === 'aging' ? '衰老评估' : '术后监测'}
                </span>
                <span className="record-date">{record.date}</span>
              </div>
              <div className="record-body">
                <div className="record-score">
                  <span className="score-value">{record.score}</span>
                  <span style={{ fontSize: 14, color: '#6B7B8D' }}>分</span>
                </div>
                <span className="record-summary">{record.summary}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 底部导航 */}
      <TabBar activeTab="history" onTabChange={handleTabChange} />
    </div>
  );
};

export default HistoryPage;
