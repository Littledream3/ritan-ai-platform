import React from 'react';
import { ExpertIcon, ConsultationIcon, AppointmentIcon } from './Icons';

const experts = [
  {
    id: 1,
    name: '多学科专家联合会诊',
    desc: '汇聚三甲医院皮肤科、整形外科、中医科专家，为您定制个性化诊疗方案',
    icon: ExpertIcon,
  },
  {
    id: 2,
    name: '远程视频问诊服务',
    desc: '足不出户即可享受专家一对一面诊，支持图文、语音、视频多种问诊方式',
    icon: ConsultationIcon,
  },
  {
    id: 3,
    name: '术后跟踪管理',
    desc: '专家团队持续跟踪术后恢复情况，及时调整治疗方案，确保最佳恢复效果',
    icon: AppointmentIcon,
  },
];

const ExpertConsultation = () => (
  <div className="expert-section">
    <span className="section-badge" style={{ background: 'rgba(255,255,255,0.2)', color: 'white' }}>特色服务</span>
    <div className="expert-section-title">订正生活 · 专家会诊</div>
    <div className="expert-section-subtitle">以专业医疗团队守护您的皮肤健康</div>
    <div className="expert-cards">
      {experts.map(item => {
        const Icon = item.icon;
        return (
          <div key={item.id} className="expert-card">
            <div className="expert-card-icon">
              <Icon />
            </div>
            <div className="expert-card-info">
              <div className="expert-card-name">{item.name}</div>
              <div className="expert-card-desc">{item.desc}</div>
            </div>
            <div className="expert-card-arrow">›</div>
          </div>
        );
      })}
    </div>
  </div>
);

export default ExpertConsultation;
