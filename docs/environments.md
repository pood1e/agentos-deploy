# 环境接入

环境剧本在目标集群部署 HTTPS 环境网关与身份路由，在平台登记环境资源、信任根及读写工具视图。
网关、令牌交换与连接器契约见[平台环境文档](https://github.com/pood1e/agentos-platform/blob/main/docs/environments.md)。

| 剧本 | 作用 |
| --- | --- |
| `playbooks/environments/deploy.yaml` | 安装 cert-manager、agentgateway 与 `agentos-environment` Chart，发布平台连接 release |
| `playbooks/environments/connections.yaml` | 安装 `agentos-connections` Chart，统一管理平台环境 CA、准入配置、服务目录与身份视图 |
| `playbooks/environments/lifecycle.yaml` | 对比原 release 的身份范围，识别需要撤销目标凭据的身份 |

配置取自方案 Chart 的 `global.agentos`，环境治理、工具分级与身份档案只维护一份。保留身份 `catalog` 只用于服务工具发现。
方案包先配置环境 OIDC issuer、每身份客户端和目标凭据，再部署环境网关、平台应用和服务连接。平台应用挂载环境 CA，CA 须在应用就绪前发布。

## 站点变量

`environments` 组每台主机声明一套环境，`ansible_host` 为平台访问网关的地址。

| 变量 | 说明 |
| --- | --- |
| `environment_name` | 对应 `global.agentos.environments` |
| `environment_issuer` | HTTPS OIDC issuer |
| `environment_domain` | 网关 DNS 名称所属域 |
| `environment_kubeconfig` | 默认 `<agentos_cache>/environments/<name>/kubeconfig.yaml` |
| `gateway_server_name` | 默认 `<environment>-mcp.<domain>`，用于证书 SAN 与上游 SNI |
| `gateway_resource` | 默认 `https://<gateway_server_name>:31000/mcp`，作为 OAuth audience |
| `agentos_values_file` | 包含 `global.agentos` 的方案 Chart 值文件 |
| `environment_connectors` | 连接器后端定义 |
| `platform_cidr` | 允许访问环境网关的平台地址段 |
| `platform_kubeconfig` | 平台集群访问配置 |
| `registry_config_file` | 可选，镜像拉取凭据 Docker JSON |
| `environment_chart_repository`、`environment_chart_version` | 默认固定平台版本的 OCI Chart 仓库与版本 |
| `environment_state` | `present` 或 `absent`，控制所属环境 release 生命周期 |

```sh
ansible-playbook agentos.platform.access -i <site>/environments.yaml -e @<site>/environments-vars.yaml
ansible-playbook agentos.platform.connections -i <site>/environments.yaml -e @<site>/environments-vars.yaml
```

## 资源归属与生命周期

目标环境每套一个 `agentos-environment` release，拥有证书声明、网关、身份路由和网络策略。平台工作空间只有一个 `agentos-connections` release，
拥有环境 AccessPlan 和 CA 声明，统一处理环境增删。连接 release 在应用启动前发布 CA 与配置，原生 kagent 与 Substrate 基础设施须已就绪。
共享连接 release 使用完整环境 inventory；退役环境以 `environment_state: absent` 显式声明。

身份变更按以下顺序执行：

1. 方案包调用 `agentos.platform.lifecycle`，读取上一版环境 release，识别退役身份。
2. 环境通过目标系统原生 API 撤销对应 OAuth 客户端、角色、API 令牌及凭据 Secret。
3. 更新环境 release，再更新平台连接 release；控制器回收已移除的路由、工具视图与注册，Helm 回收 CA 声明。
4. 应用值和连接配置同步后，检查原生发现、OBO、角色工具范围与撤销结果。

回退使用已发布 Chart 及完整站点值，Helm 处理其管理资源。
