# Trelay

> 一个 k9s 风格的 TUI 远程连接管理器，支持 SSH、RDP、VNC、Telnet 和 Kubernetes。

![项目预览图](.github/assets/screenshot.png "Trelay 界面预览")

## 功能特性

- 多协议支持 - SSH、RDP、VNC、Telnet、Kubernetes
- 现代 TUI 界面 - 基于 Textual 框架
- k9s 风格导航 - vim 风格快捷键
- 自动健康检查 - 定期检查连接状态
- 连接历史记录 - 显示最近连接时间
- 终端回滚 - 最多 5000 行历史
- K8s 资源浏览器 - 内置 Kubernetes 资源管理
- 中文界面 - 完整的中文 UI 和翻译支持

## 快速开始

### 安装

```bash
# 使用 pip 安装（推荐）
pip install trelay

# 从源码安装（开发模式）
pip install -e ".[dev]"

# 使用 requirements 文件安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 批量安装所有依赖
pip install -r requirements.txt -r requirements-dev.txt
```

### 运行

```bash
# 使用默认配置文件 (~/.config/trelay/connections.yaml)
trelay

# 使用自定义配置文件
trelay --config /path/to/connections.yaml

# 直接运行 Python 模块
python -m trelay
```

## 配置

Trelay 使用 YAML 格式的配置文件，默认位于 `~/.config/trelay/connections.yaml`。

### 配置文件示例

```yaml
version: 1
settings:
  health_check_interval: 30  # 健康检查间隔（秒）

connections:
  # SSH 连接示例
  - name: web-server-01
    protocol: ssh
    host: 192.168.1.101
    port: 22
    description: "Web Server - Ubuntu 22.04"
    ssh:
      username: admin
      private_key_path: ~/.ssh/id_rsa

  # K8s 集群浏览器（无 Pod）
  - name: k8s-cluster
    protocol: k8s
    host: ""
    port: 0
    description: "Kubernetes Cluster Browser"
    k8s:
      kubeconfig: ~/.kube/config
      context: ""
      namespace: default
      command: ""      # 留空进入资源浏览器模式
      pod: ""         # 留空进入资源浏览器模式
      container: ""   # 可选容器

  # K8s 直接连接到 Pod
  - name: k8s-app-pod
    protocol: k8s
    host: ""
    port: 0
    description: "Production App Pod"
    k8s:
      kubeconfig: ~/.kube/config
      context: prod-cluster
      namespace: default
      pod: my-app-pod
      container: main     # 可选，留空使用默认
      command: /bin/bash  # 默认 /bin/sh

  # RDP 连接
  - name: win-admin-01
    protocol: rdp
    host: 192.168.1.200
    port: 3389
    description: "Windows Admin Desktop"
    rdp:
      username: administrator
      password: ""
      domain: CORP

  # VNC 连接
  - name: vnc-workstation
    protocol: vnc
    host: 192.168.1.150
    port: 5900
    description: "Graphics Workstation"
    vnc:
      password: ""

  # Telnet 连接
  - name: legacy-router
    protocol: telnet
    host: 192.168.0.1
    port: 23
    description: "Legacy Router Management"
    telnet:
      username: admin
      password: ""
```

### 支持的协议

| 协议 | 说明 | 交互式 | 默认端口 |
|--------|------|--------|----------|
| SSH | 异步 SSH PTY 会话 | 是 | 22 |
| RDP | 外部 RDP 客户端 | 否 | 3389 |
| VNC | 外部 VNC 客户端 | 否 | 5900 |
| Telnet | 异步 Telnet 流 | 否 | 23 |
| K8s | kubectl exec PTY | 是 | 0 |

## 快捷键

### 列表模式

| 快捷键 | 功能 |
|--------|------|
| `↑` / `↓` 或 `k` / `j` | 上下导航 |
| `Enter` | 连接到选中项 |
| `Esc` | 断开连接 / 返回列表 |
| `a` | 新增连接 |
| `e` | 编辑选中连接 |
| `d` | 删除连接 |
| `:` 或 `/` | 命令模式（`:q` 退出，`/?` 帮助） |

### K8s 资源浏览器模式

| 快捷键 | 功能 |
|--------|------|
| `↑` / `↓` 或 `k` / `j` | 上下导航 |
| `Enter` | 进入 Pod 或切换命名空间 |
| `r` | **刷新资源列表**（保持搜索过滤） |
| `d` | 描述资源（kubectl get -o yaml） |
| `e` | 编辑资源（kubectl edit） |
| `l` | 查看日志（kubectl logs -f，仅 Pod） |
| `:` | 命令模式 |
| `?` | 显示 K8s 命令帮助 |

### K8s 命令

| 命令 | 功能 |
|--------|------|
| `:pod` / `:po` | 列出 Pods |
| `:svc` / `:service` | 列出 Services |
| `:deploy` | 列出 Deployments |
| `:ds` / `:daemonset` | 列出 DaemonSets |
| `:sts` / `:statefulset` | 列出 StatefulSets |
| `:job` | 列出 Jobs |
| `:cj` / `:cronjob` | 列出 CronJobs |
| `:rs` / `:replicaset` | 列出 ReplicaSets |
| `:ing` / `:ingress` | 列出 Ingresses |
| `:ep` / `:endpoint` | 列出 Endpoints |
| `:netpol` / `:netpolicy` | 列出 NetworkPolicies |
| `:cm` / `:configmap` | 列出 ConfigMaps |
| `:secret` | 列出 Secrets |
| `:pv` / `:persistentvolume` | 列出 PersistentVolumes |
| `:pvc` / `:pvc` | 列出 PersistentVolumeClaims |
| `:sc` / `:storageclass` | 列出 StorageClasses |
| `:ns` / `:namespace` | 列出或切换命名空间 |
| `:node` | 列出 Nodes |
| `:ev` / `:event` | 列出 Events |
| `:hpa` | 列出 HorizontalPodAutoscalers |
| `:rq` / `:resourcequota` | 列出 ResourceQuotas |
| `:pdb` / `:poddisruptionbudget` | 列出 PodDisruptionBudgets |
| `:ns <name>` | 切换到指定命名空间 |
| `:q` | 返回列表模式 |
| `:q!` | 退出应用 |

### 终端模式

| 快捷键 | 功能 |
|--------|------|
| 所有按键 | 转发到远程终端 |
| `Ctrl+C` | 发送中断信号 |
| `Shift+Up` / `Shift+Down` | 滚动终端历史 |
| `Shift+PageUp` / `Shift+PageDown` | 翻页滚动 |
| `Esc` | 断开连接 |
| 任意键 | 断开后返回列表 |

### 通用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+D` | 断开当前连接 |
| `:q` | 退出应用 |
| `:q!` | 强制退出应用 |

## K8s 支持的资源

### 工作负载 (Workload)
- Pods - 运行中的 Pod 实例
- Deployments - 管理无状态应用
- DaemonSets - 确保每个节点运行一个 Pod 副本
- StatefulSets - 有状态应用管理
- Jobs - 一次性任务
- CronJobs - 定时任务
- ReplicaSets - 副本集

### 服务发现 (Service)
- Services - 服务发现和负载均衡
- Ingresses - HTTP/HTTPS 路由
- Endpoints - 服务端点
- NetworkPolicies - 网络策略控制

### 存储 (Storage)
- ConfigMaps - 配置数据存储
- Secrets - 敏感数据存储
- PersistentVolumes - 块存储
- PersistentVolumeClaims - 存储声明
- StorageClasses - 存储类定义

### 集群管理 (Cluster)
- Namespaces - 命名空间隔离
- Nodes - 集群节点
- Events - 集群事件
- ResourceQuotas - 资源配额
- HorizontalPodAutoscalers - 自动扩缩容
- LimitRanges - 资源限制
- PodDisruptionBudgets - 中断预算

## 技术架构

### 核心组件

- **TrelayApp** - 主应用类，管理 UI 状态和事件流
- **ContentSwitcher** - 视图切换器（列表/K8s/终端）
- **SessionManager** - 单一会话管理器
- **ProtocolHandler** - 协议处理器抽象基类
- **K8sService** - Kubernetes 资源查询服务

### UI 框架

- **Textual** - 现代 Python TUI 框架
- **pyte** - VT100 终端仿真库
- **Rich** - 富文本渲染（Textual 内部使用）

### 协议实现

```python
class ProtocolHandler:
    async def connect(...)
    async def disconnect(...)
    async def send_input(...)
    def check_health(...)
    is_interactive: bool
```

### 数据模型

```python
class Connection:
    name: str
    protocol: Protocol (SSH/RDP/VNC/Telnet/K8S)
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    # ... 其他协议特定字段
```

## 开发

### 环境要求

- Python 3.9+
- pip

### 安装开发依赖

```bash
# 使用 pyproject.toml 安装
pip install -e ".[dev]"

# 或使用 requirements 文件安装
pip install -r requirements.txt -r requirements-dev.txt
```

### 运行测试

```bash
pytest tests/ -v
```

### 运行开发控制台

```bash
textual console
textual run --dev src/trelay/__main__.py
```

### 构建二进制

```bash
# 跨平台构建
make build

# Docker 构建
make build-docker

# Linux AMD64 构建
make build-amd64
```

## 常见问题

### 连接失败

**SSH 连接超时**
- 检查网络连接和防火墙设置
- 验证主机地址和端口正确性
- 确认 SSH 密钥路径正确

**K8s kubectl 未找到**
- 安装 kubectl 并添加到 PATH
- 或在连接配置中指定 kubectl 路径

**RDP 客户端未安装**
- macOS: 系统自带 Microsoft Remote Desktop
- Linux: 安装 xfreerdp 或 rdesktop
- 连接配置中需要设置正确的用户名和密码

### 终端问题

**终端显示异常**
- 尝试调整终端大小：`Resize` 命令
- 检查远程终端的 TERM 环境变量

**回滚历史不显示**
- 在终端中执行命令后按 `Shift+PageDown` 查看历史
- 最多保存 5000 行历史记录

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -am 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 更新日志

- [CHANGELOG.md](CHANGELOG.md) - 详细版本更新记录

## 联系方式

- GitHub Issues: [项目 Issues](https://github.com/yourusername/trelay/issues)

## 致谢

感谢所有贡献者和使用者的支持！

---

**Trelay** - k9s 风格的 TUI 远程连接管理器

Built with Python, Textual, and ❤️
