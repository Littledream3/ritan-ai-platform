import React, { useState, useCallback } from 'react';
import HomePage from './pages/HomePage';
import GuidePage from './pages/GuidePage';
import CapturePage from './pages/CapturePage';
import AnalysisPage from './pages/AnalysisPage';
import ReportPage from './pages/ReportPage';
import HistoryPage from './pages/HistoryPage';
import ProfilePage from './pages/ProfilePage';
import DetectEntryPage from './pages/DetectEntryPage';
import PoweredByFooter from './components/PoweredByFooter';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [pageData, setPageData] = useState(null);

  const handleNavigate = useCallback((page, data) => {
    setCurrentPage(page);
    if (data) setPageData(data);
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage onNavigate={handleNavigate} />;
      case 'detect':
        return <DetectEntryPage onNavigate={handleNavigate} />;
      case 'guide':
        return <GuidePage onNavigate={handleNavigate} />;
      case 'capture':
        return <CapturePage onNavigate={handleNavigate} />;
      case 'analysis':
        return <AnalysisPage onNavigate={handleNavigate} />;
      case 'report':
        return <ReportPage onNavigate={handleNavigate} data={pageData} />;
      case 'history':
        return <HistoryPage onNavigate={handleNavigate} />;
      case 'profile':
        return <ProfilePage onNavigate={handleNavigate} />;
      default:
        return <HomePage onNavigate={handleNavigate} />;
    }
  };

  return (
    <div className="app-wrapper">
      {renderPage()}
      {/* 首页已有 AppFooter，其他页面显示技术支持 */}
      {currentPage !== 'home' && currentPage !== 'detect' && <PoweredByFooter />}
    </div>
  );
}

export default App;
