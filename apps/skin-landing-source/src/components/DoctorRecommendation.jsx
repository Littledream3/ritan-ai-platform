import React from 'react';
import { DoctorAvatar1, DoctorAvatar2, DoctorAvatar3, StarIcon } from './Icons';

const doctors = [
  {
    id: 1,
    name: '张明华 主任医师',
    badge: '特邀专家',
    badgeClass: 'recommend-badge-expert',
    specialty: '皮肤科 · 痤疮与面部年轻化',
    desc: '从事皮肤科临床工作30余年，擅长中西医结合治疗各类皮肤问题',
    plan: '痤疮综合治疗方案',
    Avatar: DoctorAvatar1,
  },
  {
    id: 2,
    name: '李雅文 副主任医师',
    badge: '金牌医生',
    badgeClass: 'recommend-badge-expert',
    specialty: '医学美容科 · 激光美容',
    desc: '擅长色素性疾病、血管性疾病的激光治疗及面部年轻化综合设计',
    plan: '色斑淡化定制方案',
    Avatar: DoctorAvatar2,
  },
  {
    id: 3,
    name: '王志强 主任医师',
    badge: '学科带头人',
    badgeClass: 'recommend-badge-expert',
    specialty: '皮肤外科 · 疤痕修复',
    desc: '在皮肤肿瘤、疤痕修复及创面愈合领域具有丰富的临床经验',
    plan: '疤痕修复综合方案',
    Avatar: DoctorAvatar3,
  },
];

const DoctorRecommendation = ({ onNavigate }) => (
  <div className="doctor-recommend-section">
    <span className="section-badge">专家推荐</span>
    <div className="doctor-recommend-title">方案与医生推荐</div>
    <div className="doctor-recommend-subtitle">特邀专家为您规划诊断结果</div>
    <div className="recommend-cards">
      {doctors.map(doc => {
        const { Avatar } = doc;
        return (
          <div key={doc.id} className="recommend-card">
            <div className="recommend-avatar">
              <Avatar />
            </div>
            <div className="recommend-info">
              <div className="recommend-name">
                {doc.name}
                <span style={{ marginLeft: 6 }}>
                  <StarIcon />
                  <StarIcon />
                  <StarIcon />
                  <StarIcon />
                  <StarIcon />
                </span>
              </div>
              <span className={`recommend-badge ${doc.badgeClass}`}>{doc.badge}</span>
              <div className="recommend-specialty">{doc.specialty}</div>
              <div className="recommend-desc">{doc.desc}</div>
              <span className="recommend-plan">📋 {doc.plan}</span>
            </div>
            <div className="recommend-actions">
              <button className="recommend-btn recommend-btn-primary" onClick={() => onNavigate('detect')}>
                预约咨询
              </button>
              <button className="recommend-btn recommend-btn-outline" onClick={() => onNavigate('detect')}>
                查看方案
              </button>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

export default DoctorRecommendation;
