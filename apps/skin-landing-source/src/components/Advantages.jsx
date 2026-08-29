import React from 'react';
import { CameraIcon, AIIcon, ReportIcon, ChatIcon } from './Icons';

const steps = [
  { id: 1, icon: CameraIcon, title: '智能检测', desc: '多角度面部高清图像采集，AI精准定位皮肤问题区域' },
  { id: 2, icon: AIIcon, title: 'AI分析', desc: '深度学习算法分析皮肤状态，Glogau分级专业评估' },
  { id: 3, icon: ReportIcon, title: '专业报告', desc: '生成详细皮肤分析报告，包含各项指标及改善建议' },
  { id: 4, icon: ChatIcon, title: '在线问诊', desc: '直接连线三甲专家，获取个性化诊疗方案和用药指导' },
];

const Advantages = ({ onNavigate }) => (
  <div className="advantages-section">
    <span className="section-badge">服务流程</span>
    <div className="advantages-title">AI智能检测 · 专业诊疗服务</div>
    <div className="advantages-subtitle">从检测到治疗，一站式皮肤健康管理</div>
    <div className="advantages-grid">
      {steps.map(step => {
        const Icon = step.icon;
        return (
          <div key={step.id} className="advantage-card" onClick={() => step.id === 1 ? onNavigate('detect') : null}>
            <div className="advantage-card-icon">
              <Icon />
            </div>
            <div className="advantage-card-title">{step.title}</div>
            <div className="advantage-card-desc">{step.desc}</div>
          </div>
        );
      })}
    </div>
  </div>
);

export default Advantages;
