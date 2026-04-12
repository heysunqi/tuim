# Tuim

> k9s 风格的 TUI 远程连接管理器，在终端中统一管理 SSH、RDP、VNC、Telnet 和 Kubernetes 连接。

![项目预览图](.github/assets/screenshot.png "Tuim 界面预览")

## 为什么选择 Tuim

- **一站式管理** — 五种协议统一到一个终端界面，告别在多个工具之间切换
- **零 GUI 依赖** — 纯终端 TUI，通过 SSH 远程操作服务器时也能使用，适合 headless 环境和跳板机场景
- **k9s 级 K8s 体验** — 内置资源浏览器，覆盖 Pods、Deployments、Services 等 20+ 种资源类型，支持实时搜索、describe、edit、logs，切换 namespace 时自动保留当前资源视图
- **vim 键位驱动** — `j/k` 导航、`:` 命令、`/` 搜索，全程键盘操作，无需鼠标
- **内置终端仿真** — 基于 pyte 的完整 VT100 终端，支持 256 色/24 位真彩色、光标定位、5000 行回滚历史，可运行 vim、htop 等全屏应用
- **自动健康检查** — 后台异步并发探活所有连接，实时展示 Online/Offline 状态
- **Shell 容错** — K8s exec 失败时自动弹出 Shell 选择器，提供 bash/sh/ash/zsh 备选方案
- **中英双语** — 根据系统 locale 自动切换中文/英文界面

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| TUI 框架 | [Textual](https://github.com/Textualize/textual) >=0.80 | 现代异步 TUI 框架，提供组件化 UI、CSS 样式、事件系统 |
| 终端仿真 | [pyte](https://github.com/selectel/pyte) >=0.8 | VT100/xterm 终端仿真，HistoryScreen 支持回滚缓冲区 |
| SSH 协议 | [asyncssh](https://github.com/ronf/asyncssh) >=2.14 | 原生 asyncio SSH 客户端，支持 PTY、密钥认证、终端 resize |
| Telnet 协议 | [telnetlib3](https://github.com/jquast/telnetlib3) >=2.0 | 原生 asyncio Telnet 客户端 |
| K8s 交互 | kubectl + `os.fork()` + PTY | 无需 K8s Python SDK，通过 fork 子进程 + 伪终端直接驱动 kubectl exec |
| RDP / VNC | 系统原生客户端 | macOS: `open rdp://`/`vnc://`；Linux: xfreerdp/rdesktop、vncviewer |
| 配置格式 | [PyYAML](https://pyyaml.org/) >=6.0 | YAML 配置文件读写 |
| 构建系统 | [Hatchling](https://hatch.pypa.io/) | PEP 517 构建后端，src-layout 布局 |
| 打包分发 | [PyInstaller](https://pyinstaller.org/) | 单文件二进制打包，支持 Docker 跨平台构建 |

**运行环境**: Python >=3.14 | macOS / Linux

## 架构概览

```
┌─────────────────────────────────────────────────┐
│                   TuimApp                        │
│  on_key() ──> 模式分发 ──> 命令/搜索/导航         │
├─────────────┬──────────────┬────────────────────┤
│  列表模式    │  K8s 浏览器   │  终端模式           │
│ ConnectionT. │ K8sResource  │ TerminalView       │
│  DataTable   │  View        │ pyte.HistoryScreen │
├─────────────┴──────────────┴────────────────────┤
│               SessionManager                     │
│        (单活会话，协议路由，回调分发)               │
├──────┬───────┬───────┬──────┬───────────────────┤
│ SSH  │ Telnet│  K8s  │ RDP  │  VNC              │
│asyncs│telnet │fork + │外部   │ 外部              │
│sh    │lib3   │PTY    │客户端 │ 客户端            │
└──────┴───────┴───────┴──────┴───────────────────┘
```

- **三模式 UI** — `ContentSwitcher` 管理列表、K8s 浏览器、终端三个视图，`on_key()` 按当前模式分发按键事件
- **协议处理器** — `ProtocolHandler` 抽象基类定义 `connect/disconnect/send_input/check_health` 接口；交互式协议 (SSH/Telnet/K8s) 通过回调流式输出到终端，非交互式协议 (RDP/VNC) 拉起系统客户端
- **SessionManager** — 单一活跃会话，根据 `Connection.protocol` 创建对应 handler 并路由 I/O 回调
- **HealthChecker** — `asyncio.gather()` 并发检查所有连接，SSH/RDP/VNC/Telnet 使用 TCP 探活，K8s 使用 `kubectl cluster-info` 或 `kubectl get pod`
- **Modal 屏幕** — 新增/编辑连接、删除确认、帮助、K8s 资源选择、Shell 选择器均为 `ModalScreen` 子类，通过 `dismiss()` 返回结果

## 快速开始

### 安装

```bash
# 使用 pip 安装（推荐）
pip install tuim

# 从源码安装（开发模式）
pip install -e ".[dev]"
```

### 运行

```bash
# 使用默认配置文件 (~/.config/tuim/connections.yaml)
tuim

# 使用自定义配置文件
tuim --config /path/to/connections.yaml

# 直接运行 Python 模块
python -m tuim
```

首次运行会自动在 `~/.config/tuim/` 下生成示例配置文件。

## 配置

Tuim 使用 YAML 格式的配置文件，默认位于 `~/.config/tuim/connections.yaml`。

```yaml
version: 1
settings:
  health_check_interval: 30  # 健康检查间隔（秒）

connections:
  # SSH 连接
  - name: web-server-01
    protocol: ssh
    host: 192.168.1.101
    port: 22
    description: "Web Server - Ubuntu 22.04"
    ssh:
      username: admin
      private_key_path: ~/.ssh/id_rsa

  # K8s 集群浏览器（pod 留空进入资源浏览模式）
  - name: k8s-cluster
    protocol: k8s
    host: ""
    port: 0
    description: "Kubernetes Cluster Browser"
    k8s:
      kubeconfig: ~/.kube/config
      context: ""
      namespace: default

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
      container: main
      command: /bin/bash

  # RDP 连接
  - name: win-admin-01
    protocol: rdp
    host: 192.168.1.200
    port: 3389
    description: "Windows Admin Desktop"
    rdp:
      username: administrator
      domain: CORP

  # VNC 连接
  - name: vnc-workstation
    protocol: vnc
    host: 192.168.1.150
    port: 5900
    description: "Graphics Workstation"

  # Telnet 连接
  - name: legacy-router
    protocol: telnet
    host: 192.168.0.1
    port: 23
    description: "Legacy Router Management"
    telnet:
      username: admin
```

### 支持的协议

| 协议 | 实现方式 | 交互式 | 默认端口 |
|------|----------|--------|----------|
| SSH | asyncssh 异步 PTY 会话 | 是 | 22 |
| RDP | 系统 RDP 客户端 (xfreerdp / macOS Remote Desktop) | 否 | 3389 |
| VNC | 系统 VNC 客户端 (vncviewer / macOS Screen Sharing) | 否 | 5900 |
| Telnet | telnetlib3 异步流 | 是 | 23 |
| K8s | kubectl exec via fork + PTY | 是 | — |

## 快捷键

### 列表模式

| 快捷键 | 功能 |
|--------|------|
| `j` / `k` 或 `↑` / `↓` | 上下导航 |
| `Enter` | 连接到选中项 |
| `a` | 新增连接 |
| `e` | 编辑选中连接 |
| `d` | 删除连接 |
| `:` | 进入命令模式 |
| `/` | 搜索过滤 |
| `:q` | 退出应用 |

### K8s 资源浏览器

| 快捷键 | 功能 |
|--------|------|
| `j` / `k` 或 `↑` / `↓` | 上下导航 |
| `Enter` | 进入 Pod Shell 或切换 Namespace |
| `d` | 描述资源 (kubectl get -o yaml) |
| `e` | 编辑资源 (kubectl edit) |
| `l` | 查看日志 (kubectl logs -f，仅 Pod) |
| `r` | 刷新资源列表 |
| `/` | 搜索过滤 |
| `:` | 命令模式 |

### K8s 命令

| 命令 | 资源类型 |
|------|----------|
| `:pod` `:po` | Pods |
| `:deploy` | Deployments |
| `:svc` `:service` | Services |
| `:ds` `:daemonset` | DaemonSets |
| `:sts` `:statefulset` | StatefulSets |
| `:job` | Jobs |
| `:cj` `:cronjob` | CronJobs |
| `:rs` `:replicaset` | ReplicaSets |
| `:ing` `:ingress` | Ingresses |
| `:ep` `:endpoint` | Endpoints |
| `:cm` `:configmap` | ConfigMaps |
| `:secret` | Secrets |
| `:pv` `:persistentvolume` | PersistentVolumes |
| `:pvc` | PersistentVolumeClaims |
| `:sc` `:storageclass` | StorageClasses |
| `:ns` `:namespace` | 列出 Namespaces |
| `:ns <name>` | 切换 Namespace（保留当前资源类型） |
| `:node` | Nodes |
| `:ev` `:event` | Events |
| `:hpa` | HorizontalPodAutoscalers |
| `:netpol` `:netpolicy` | NetworkPolicies |
| `:rq` `:resourcequota` | ResourceQuotas |
| `:pdb` `:poddisruptionbudget` | PodDisruptionBudgets |
| `:q` | 返回列表 |
| `:q!` | 退出应用 |

### 终端模式

| 快捷键 | 功能 |
|--------|------|
| 所有按键 | 转发到远程终端 |
| `Shift+↑` / `Shift+↓` | 逐行滚动历史 |
| `Shift+PageUp` / `Shift+PageDown` | 翻页滚动 |
| 断开后任意键 | 返回上级视图 |

## 开发

### 环境要求

- Python >=3.14
- pip

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/ -v
```

### Textual 开发控制台

```bash
textual console
textual run --dev src/tuim/__main__.py
```

### 构建二进制

```bash
make build           # 本地平台构建
make build-docker    # Docker 容器构建
make build-amd64     # Linux AMD64 构建
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

---

**Tuim** — k9s 风格的 TUI 远程连接管理器 | Built with Textual + asyncssh + pyte
