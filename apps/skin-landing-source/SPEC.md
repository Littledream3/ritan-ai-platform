# 兰峤AI测肤 - 产品规格说明书

## 1. 产品概述

### 产品名称
兰峤AI测肤 (Lanjiao AI Skin Test)

### 产品定位
基于AI算法的面部皮肤健康检测与衰老评估平台

### 核心功能
- **功能一**：面部皮肤衰老评估 - AI智能分析皮肤状态，Glogau分级专业评估
- **功能二**：术后创面监测 - 创面愈合追踪评估

---

## 2. 功能模块

### 2.1 首页 (HomePage)
- 欢迎卡片
- 功能入口网格（皮肤检测、衰老评估、术后监测、历史报告）
- 专业保障展示
- 底部导航栏

### 2.2 拍摄引导页 (GuidePage)
- 分步骤引导（环境准备、角度调整、开始检测）
- 注意事项说明
- 隐私声明

### 2.3 图像采集页 (CapturePage)
- 多角度拍摄引导（正面、左侧45°、右侧45°）
- 实时预览
- 缩略图展示已采集图像

### 2.4 AI分析页 (AnalysisPage)
- 进度动画展示
- 分析步骤列表（图像预处理、人脸检测、皮肤分割、皱纹分析等）

### 2.5 报告页 (ReportPage)
- 综合评分展示
- 雷达图可视化
- 详细评估指标
- 个性化护肤建议
- 分享功能

### 2.6 历史记录页 (HistoryPage)
- 检测历史列表
- 分类筛选（衰老评估/术后监测）

### 2.7 个人中心 (ProfilePage)
- 用户信息
- 统计数据
- 菜单选项

---

## 3. 技术架构

### 前端框架
- React 18
- 状态管理：React useState/useContext
- 样式：CSS Variables + 内联样式

### AI算法接口（预留）
```javascript
// 皮肤分析API
POST /api/skin/analyze
Request: { images: string[] }
Response: { score, wrinkles, spots, elasticity, pores, photoaging, glogauLevel }

// 创面分析API
POST /api/wound/analyze
Request: { images: string[], surgeryType: string }
Response: { healingRate, woundArea, recommendation }
```

---

## 4. Glogau光老化分级标准

| 级别 | 描述 | 特征 |
|------|------|------|
| Ⅰ级 | 轻度光老化 | 无明显皱纹，轻度色素改变 |
| Ⅱ级 | 中度光老化 | 早期皱纹，轻中度色斑 |
| Ⅲ级 | 重度光老化 | 中度皱纹，明显色斑 |
| Ⅳ级 | 严重光老化 | 严重皱纹，皮肤弹性差 |

---

## 5. 设计规范

### 颜色系统
```css
--primary-color: #6B5B95;      /* 主色：紫 */
--secondary-color: #88B04B;     /* 辅助色：绿 */
--accent-color: #F7CAC9;        /* 强调色：粉 */
--bg-color: #FAF9F7;            /* 背景色 */
--text-primary: #2D2926;        /* 主文字 */
--text-secondary: #8D8078;      /* 次要文字 */
```

### 字体
- 优先使用系统字体栈
- 移动端优化：-apple-system, PingFang SC, Microsoft YaHei

### 间距系统
- 基础单位：4px
- 常用间距：8px, 12px, 16px, 24px

---

## 6. 部署说明

### 当前部署
- 独立HTML文件（CDN加载React）
- 部署地址：https://17dhy8t2fq4j.space.minimaxi.com

### 技术团队后续开发
1. 可将此代码转换为微信小程序（使用Taro/UniApp）
2. 可集成到现有官网作为Web应用
3. 可接入日坛AI平台API实现真实AI分析

---

## 7. 联系信息

- **技术支持**：日坛AI (http://ritanai.com/)
- **开发团队**：MiniMax Agent
