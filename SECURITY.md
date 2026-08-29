# Security Policy

## Supported version

安全修复以 `main` 分支最新版本为准。

## Reporting a vulnerability

请使用 GitHub **Private vulnerability reporting** 提交安全问题。不要在公开Issue、讨论区或Pull Request中提交密码、Token、患者信息、真实数据库内容或可识别的医疗影像。

报告建议包括：

- 受影响的文件或接口；
- 可复现步骤及影响范围；
- 已采取的临时保护措施；
- 不包含真实密钥和个人数据的最小化示例。

## Secret handling

- 生产凭据只允许通过环境变量或密钥管理服务注入。
- `.env`、数据库备份、日志、模型权重和上传媒体不得提交到Git。
- 一旦凭据可能被公开，应先撤销或轮换，再清理代码和Git历史。
- 公开前应扫描当前文件、完整历史和压缩包内容。

## Medical data

本仓库不得接收真实患者数据。测试和演示只能使用人工构造数据、公开授权数据或完成不可逆匿名化的数据。

