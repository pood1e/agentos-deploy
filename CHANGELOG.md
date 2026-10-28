# Changelog

## 1.1.0

- 接入 kagent 原生执行授权、持久委派凭据、目录发现和公开执行 API。
- 固定 Agentgateway 1.7 与同批 kagent `.7` 镜像、Chart 和 CRD。
- 隔离 Helm 插件并发布原生执行入口与私有身份源信任。

## 1.0.0

- 参考部署从 AgentOS 平台仓库迁出，固定平台 0.43.0。
- collection 以独立密钥签名（公钥 `ci/cosign.pub`），签名属性为 collection 版本与源码提交。
- 平台角色目录 `authorization.json` 与契约 wheel 哈希不再随 collection 发布。
- 应用升级后不再重启平台网关与重新标记 RemoteMCPServer，工具目录由 kagent 原生发现收敛：每 5 分钟刷新，标签或依赖的 Secret / ConfigMap 变更时立即刷新。
