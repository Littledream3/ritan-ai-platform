# 兰峤AI测肤

专业皮肤检测与衰老评估小程序

## 项目结构

```
lanjiao-skin/
├── index.html              # 入口HTML文件
├── package.json            # 项目配置
├── vite.config.js          # Vite配置
├── SPEC.md                 # 产品规格说明书
├── README.md               # 项目说明
└── src/
    ├── main.jsx            # React入口
    ├── App.jsx             # 主应用组件
    ├── styles/
    │   └── globals.css     # 全局样式
    ├── components/
    │   ├── index.js        # 组件导出
    │   ├── Icons.jsx       # SVG图标组件
    │   ├── PoweredByFooter.jsx  # 日坛AI技术支持组件
    │   ├── RadarChart.jsx  # 雷达图组件
    │   ├── ScoreCircle.jsx # 评分圆环组件
    │   └── TabBar.jsx      # 底部导航栏组件
    ├── pages/
    │   ├── index.js        # 页面导出
    │   ├── HomePage.jsx    # 首页
    │   ├── GuidePage.jsx   # 拍摄引导页
    │   ├── CapturePage.jsx # 图像采集页
    │   ├── AnalysisPage.jsx # AI分析页
    │   ├── ReportPage.jsx  # 报告页
    │   ├── HistoryPage.jsx  # 历史记录页
    │   └── ProfilePage.jsx # 个人中心页
    └── utils/
        ├── constants.js    # 常量配置
        └── mockData.js     # 模拟数据
```

## 技术栈

- React 18
- Vite 5
- CSS Variables

## 开发

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build

# 预览构建结果
npm run preview
```

## 功能模块

### 1. 皮肤检测
- 面部图像采集（正面、左右45°）
- AI智能分析
- Glogau分级评估

### 2. 衰老评估
- 皱纹分析
- 色斑检测
- 弹性评估
- 毛孔状况

### 3. 术后监测
- 创面愈合追踪
- 修复效果评估

### 4. 历史报告
- 检测历史记录
- 趋势分析

## API预留

技术团队需要接入真实AI分析API时，修改以下文件：

- `src/utils/mockData.js` - 替换为真实API调用
- `src/utils/constants.js` - 配置API地址

示例API：
```javascript
POST /api/skin/analyze
Request: { images: string[] }
Response: { score, wrinkles, spots, elasticity, pores, photoaging, glogauLevel }
```

## 部署

```bash
# 构建生产版本
npm run build

# 构建产物在 dist/ 目录
```

## 联系方式

- 技术支持：日坛AI (http://ritanai.com/)
