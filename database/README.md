# 数据库说明

GitHub 只保存数据库结构、迁移脚本和空白初始化方式。真实数据库备份放在私有的加密迁移仓库中。

主要数据服务：

- DFU 平台：PostgreSQL `dfu_v2`
- 医生采集：PostgreSQL `dfu_collection`
- 批量上传：PostgreSQL `media_drop`
- 官网平台：MySQL
- 官网缓存：Redis
- 测肤记录：SQLite

患者姓名、电话、邮箱和住院号不会进入公开可读源码。用于模型训练的数据只保留匿名编号、分级、必要的非识别性临床字段和媒体校验值。

