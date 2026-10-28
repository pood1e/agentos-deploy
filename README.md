# AgentOS 参考部署

Ansible collection `agentos.platform`，在支持 KVM 的 Ubuntu 主机安装单节点 K3s、Agent Substrate、kagent、agentgateway 与 [AgentOS 平台](https://github.com/pood1e/agentos-platform) Chart，并接入目标环境。
每个版本固定一个已签名的平台版本，见 [platform.yaml](platform.yaml)；上游版本与运行时镜像摘要见 [playbooks/deploy/vars.yaml](playbooks/deploy/vars.yaml)。

| 入口 | 作用 |
| --- | --- |
| `agentos.platform.install` | 安装或升级节点、运行时、网关、域名、语音与平台应用 |
| `agentos.platform.access` | 安装目标环境网关并发布平台连接，见[环境接入](docs/environments.md) |
| `agentos.platform.connections` | 更新平台环境连接 |
| `agentos.platform.lifecycle` | 识别需撤销目标凭据的退役身份 |
| 角色 `agentos.platform.node_dns` | 配置节点与 Pod DNS |

## 安装与升级

站点 inventory 与变量保存在仓库外，`agentos` 组包含一台主机，主机名作为 Kubernetes 节点名：

```yaml
all:
  children:
    agentos:
      hosts:
        agentos-01: {ansible_host: 192.0.2.10, ansible_user: admin}
```

从发布记录取得版本与源码提交，使用站点信任的 collection 公钥 [ci/cosign.pub](ci/cosign.pub) 校验并安装，`$REGISTRY` 为发布 collection 的注册表路径：

```sh
collection="$REGISTRY/collections/platform"
digest=$(oras resolve "$collection:$VERSION")
cosign verify --key /etc/agentos/agentos-deploy.pub --insecure-ignore-tlog \
  -a "version=$VERSION" -a "revision=$REVISION" "$collection@$digest"
oras pull "$collection@$digest" --output .cache/delivery
ansible-galaxy collection install ".cache/delivery/agentos-platform-$VERSION.tar.gz"
ansible-playbook agentos.platform.install -i <site>/inventory.yaml -e @<site>/vars.yaml
```

控制端安装 collection 根目录 `requirements.txt` 的 Python 依赖，并提供 Helm、cosign、ORAS 与 Kustomize。playbook 安装前以平台公钥 `playbooks/deploy/files/cosign.pub` 校验平台 Chart 与镜像的签名、版本和源码提交。
升级时安装新版已验签 collection 后执行同一 playbook。运行时使用官方 Chart，资源调整经 Helm 4 `postrenderer/v1` 插件与 Kustomize overlay 应用。

| 站点变量 | 内容 |
| --- | --- |
| `agentos_domain` | 控制台域名，DNS / 证书覆盖该域及通配子域 |
| `dns_zone` | Cloudflare DNS 区域，用于记录与 ACME DNS-01 |
| `app_chart`、`app_chart_repository`、`app_chart_version` | 应用 Chart，默认固定版本的平台 Chart；业务部署选择方案 Chart |
| `app_chart_revision`、`app_chart_public_key` | 应用源码提交与签名公钥，默认取固定的平台版本 |
| `app_values` | 应用 Chart 值，方案 Chart 的平台配置位于 `app_values.agentos`，字段见[平台交付文档](https://github.com/pood1e/agentos-platform/blob/main/docs/delivery.md) |
| `app_release_name`、`agentos_namespace` | release 与命名空间，均默认 `agentos` |
| `agentos_cache` | 缓存目录，默认 `$XDG_CACHE_HOME/agentos` 或 `~/.cache/agentos` |
| `node_hosts` | 可选节点 hosts 记录 `{name, address}` |
| `kagent_telemetry` | 可选 kagent 原生 `TelemetryConfig`，应用于控制面与运行时默认值 |

collection 固化 `delivery_version`、`delivery_revision` 与 `agentos_image_registry`，对应所部署的平台版本、源码提交与镜像注册表路径。

| 凭据输入 | 内容 |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` / `cloudflare_token_file` | DNS 与 ACME 凭据 |
| `model_key_file` | 首次创建 `model-credentials` 的模型 API Key |
| `identity_client_secret_file` | 站点 OIDC 机密客户端密钥，写入 `identity.secretRef` |
| `skill_repository_credential_file` | 可选 JSON，含只读 Git 仓库 `Authorization` 请求头 |
| `registry_config_file` | Docker JSON，用于制品下载、验签与镜像拉取 |

凭据文件使用 0600 权限，保存在仓库外或 `.cache/`。Helm values 通过 JSON 文件传入。
参考部署启用 K3s Traefik 的 Gateway API，创建 `agentos-public` 与域名证书，并首次生成 `<release>-sessions` 会话 Secret，升级复用。

应用部署将 Substrate 当前 live Service DNS ClusterTrustBundle 发布为平台命名空间的 `substrate-service-dns-ca` ConfigMap，供 agentgateway 直接验证 Actor JWKS HTTPS 端点。Service DNS 根轮换时执行 `agentos.platform.install --tags app` 同步信任；轮换期间保留覆盖现有服务证书的根。Actor 签名公钥由原生 JWKS 端点发布，刷新由 agentgateway 管理。

原生 kagent API 的 NetworkPolicy 允许同命名空间的业务网关、平台 API/dataplane 与 controller 访问，策略随原生 kagent release 管理。站点保留 K3s 内置的 NetworkPolicy 控制器。

```yaml
kagent_telemetry:
  traces: {endpoint: 'https://otlp.example.com:4317', protocol: grpc, timeout: 5s}
  metrics: {endpoint: 'https://otlp.example.com/v1/metrics', protocol: http/protobuf}
  logs: {endpoint: 'https://otlp.example.com/v1/logs', protocol: http/protobuf}
```

kagent 各信号按配置启用，内容与原始请求体采集默认关闭，分别由 `captureContent` / `captureRawApiBodies` 控制。

## 运行验证

部署标签 `node`、`runtime`、`model`、`ingress`、`voice`、`app` 支持分项执行，应用更新用 `--tags app`。
自管 DNS / TLS 的站点提供 Gateway 与 `agentos-ingress` Secret，跳过 `ingress`。
节点就绪后，`playbooks/deploy/validate.yaml` 进行服务端 dry-run；节点上的 `python3 playbooks/deploy/verify-runtime.py <namespace>` 验证原生沙箱执行与挂起恢复。

## 开发与发布

工具版本由 [mise.toml](mise.toml) 与锁文件固定。

```sh
mise install --locked
uv venv .cache/venv --python "$(mise which python)"
uv pip install --python .cache/venv/bin/python -r requirements.txt -r ci/requirements.txt
ansible-galaxy collection install -r ci/collections.yaml -p .cache/collections
PATH="$PWD/.cache/venv/bin:$PATH" mise exec -- ci/check.sh
```

`ci/check.sh` 执行 ansible-lint、语法检查、运行时策略与单元测试，[GitHub Verify](.github/workflows/verify.yaml) 以它作为合并门禁。
release-please 依据 Conventional Commits 维护版本 PR、`galaxy.yml` 版本、变更记录与 tag。升级平台时更新 `platform.yaml`，并同步运行时版本固定值。

构建仓库以 GitLab CI 定时快进同步 main 与 tag，校验固定平台 Chart 的签名并提取默认值后构建 collection；受保护 tag 发布 `$CI_REGISTRY_IMAGE/collections/platform:<version>`，以 `ci/cosign.pub` 对应的密钥签名，签名属性 `version` / `revision` 为 collection 版本与源码提交。CI 镜像由 [ci/images/Dockerfile](ci/images/Dockerfile) 构建。

| 构建变量 | 内容 |
| --- | --- |
| `AGENTOS_PLATFORM_REGISTRY` | 平台制品注册表路径 |
| `COSIGN_PRIVATE_KEY`、`COSIGN_PASSWORD` | 受保护的 collection 签名私钥文件与隐藏密码 |
| `AGENTOS_SOURCE_MIRROR_KEY`、`AGENTOS_SOURCE_MIRROR_HOST_KEYS` | 限定 `source-sync` 环境的同步部署密钥与主机公钥 |
| `AGENTOS_BUILDKIT_RUNNER`、`AGENTOS_BUILDKIT_IMAGE` | rootless BuildKit runner 标签与镜像摘要 |
| `AGENTOS_REGISTRY_MIRROR` | 可选 Docker Hub 镜像源 |

## 许可证

[Apache-2.0](LICENSE)
