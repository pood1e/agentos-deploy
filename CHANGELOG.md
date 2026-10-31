# Changelog

## [2.0.3](https://github.com/pood1e/agentos-deploy/compare/v2.0.2...v2.0.3) (2026-10-31)


### Bug Fixes

* **runtime:** budget native PostgreSQL resources and connections ([95a4cf5](https://github.com/pood1e/agentos-deploy/commit/95a4cf5247e0518ad7bce5e36245165a6f141db8))

## [2.0.2](https://github.com/pood1e/agentos-deploy/compare/v2.0.1...v2.0.2) (2026-10-29)


### Bug Fixes

* **runtime:** pin native machine grant renewal ([#12](https://github.com/pood1e/agentos-deploy/issues/12)) ([42a728e](https://github.com/pood1e/agentos-deploy/commit/42a728e115a004b0fcd272cf942516a6629e8b83))

## [2.0.1](https://github.com/pood1e/agentos-deploy/compare/v2.0.0...v2.0.1) (2026-10-29)


### Bug Fixes

* **runtime:** enforce Claude MCP selections without controller discovery ([#10](https://github.com/pood1e/agentos-deploy/issues/10)) ([33bb776](https://github.com/pood1e/agentos-deploy/commit/33bb7762b11ca2a51f66d9105e126b1deef24ad2))

## [2.0.0](https://github.com/pood1e/agentos-deploy/compare/v1.0.0...v2.0.0) (2026-10-29)


### ⚠ BREAKING CHANGES

* **runtime:** return site execution authorization to native kagent ([#4](https://github.com/pood1e/agentos-deploy/issues/4))

### Features

* **runtime:** return site execution authorization to native kagent ([#4](https://github.com/pood1e/agentos-deploy/issues/4)) ([aec5632](https://github.com/pood1e/agentos-deploy/commit/aec5632e8a0bb9f8c2e4e60ce0bdf092586f1258))
* **runtime:** 发布 Substrate Service DNS 信任根 ([#2](https://github.com/pood1e/agentos-deploy/issues/2)) ([1f047da](https://github.com/pood1e/agentos-deploy/commit/1f047da632dcbe128d3b88bcc3470a146ec072c5))


### Bug Fixes

* **runtime:** scope asset upload and optional telemetry configuration ([#9](https://github.com/pood1e/agentos-deploy/issues/9)) ([2e9ce47](https://github.com/pood1e/agentos-deploy/commit/2e9ce47b0ab6a53f0d77d7c9197b49f0c20f8996))
* **security:** restrict native kagent API ingress ([#6](https://github.com/pood1e/agentos-deploy/issues/6)) ([059c8bb](https://github.com/pood1e/agentos-deploy/commit/059c8bb92ee58a3e4ee897d0038b5b661e882a8f))

## 1.0.0

- 参考部署从 AgentOS 平台仓库迁出，固定平台 0.43.0。
- collection 以独立密钥签名（公钥 `ci/cosign.pub`），签名属性为 collection 版本与源码提交。
- 平台角色目录 `authorization.json` 与契约 wheel 哈希不再随 collection 发布。
- 应用升级后不再重启平台网关与重新标记 RemoteMCPServer，工具目录由 kagent 原生发现收敛：每 5 分钟刷新，标签或依赖的 Secret / ConfigMap 变更时立即刷新。
