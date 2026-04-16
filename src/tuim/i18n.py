"""Internationalization support for Tuim.

Provides a simple t(key, **kwargs) translation function with
Chinese (zh) and English (en) dictionaries.  Language is
auto-detected from LC_ALL / LANG environment variables,
defaulting to Chinese.
"""
import os


def _detect_language():
    # type: () -> str
    lang = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    if not lang:
        return "zh"
    if lang.lower().startswith("zh"):
        return "zh"
    return "en"


_lang = _detect_language()

_ZH = {
    # -- header shortcuts --
    "nav": "导航",
    "connect": "连接",
    "disconnect_btn": "断开",
    "add": "新增",
    "edit": "编辑",
    "delete_btn": "删除",
    "search": "搜索",
    "quit": "退出",
    "exec": "Exec",
    "pods": "Pods",
    "services": "服务",
    "deployments": "部署",
    "daemonsets": "守护进程集",
    "statefulsets": "有状态副本集",
    "namespaces": "命名空间",
    "back": "返回",
    "quit_force": "退出",
    "describe": "Describe",
    "k8s_edit": "编辑",
    "logs": "日志",
    "k8s_help": "帮助",
    "refresh": "刷新",
    # -- new resources --
    "jobs": "任务",
    "cronjobs": "定时任务",
    "replicasets": "副本集",
    "ingresses": "入口",
    "endpoints": "端点",
    "networkpolicies": "网络策略",
    "configmaps": "配置映射",
    "secrets": "密钥",
    "persistentvolumes": "持久卷",
    "persistentvolumeclaims": "持久卷声明",
    "storageclasses": "存储类",
    "nodes": "节点",
    "events": "事件",
    "resourcequotas": "资源配额",
    "horizontalpodautoscalers": "自动扩缩",
    "limitranges": "限制范围",
    "poddisruptionbudgets": "中断预算",
    # -- k8s help --
    "title_k8s_help": "K8s 资源命令",
    "k8s_help_hint": "按任意键关闭",
    "switch_namespace": "切换命名空间",
    # -- mode --
    "mode_list": "列表模式",
    "mode_k8s": "K8s 资源浏览",
    "mode_terminal": "终端模式",
    # -- app messages --
    "connecting_to": "正在连接 {name} ({proto})...",
    "connection_failed": "连接失败: {error}",
    "connection_launched": "已通过外部客户端启动连接。",
    "will_return": "会话结束后将返回列表。",
    "disconnecting": "正在断开连接...",
    "connection_closed": "[连接已关闭]",
    "press_any_key_return": "[按任意键或 Ctrl+C 返回...]",
    "exec_into_pod": "正在进入 Pod {name}...",
    "exec_failed": "Exec 失败: {error}",
    "k8s_describing": "正在获取 {name} 的 YAML...",
    "k8s_editing": "正在编辑 {name}...",
    "k8s_tailing_logs": "正在查看 {name} 的日志...",
    "retrying_exec": "正在使用 {shell} 重试进入 Pod {name}...",
    # -- time --
    "time_never": "从未",
    "time_just_now": "刚刚",
    "time_min_ago": "{n} 分钟前",
    "time_hr_ago": "{n} 小时前",
    "time_day_ago": "{n} 天前",
    "time_days_ago": "{n} 天前",
    # -- columns --
    "col_status": "状态",
    "col_name": "名称",
    "col_host": "主机",
    "col_protocol": "协议",
    "col_port": "端口",
    "col_description": "描述",
    "col_last_connected": "最近连接",
    # -- scrollback --
    "scrollback_indicator": "回滚: -{n} 行",
    # -- argparse --
    "app_description": "Tuim - TUI 远程连接管理器",
    "config_help": "连接配置 YAML 文件路径",
    # -- add_connection screen --
    "title_add_connection": "新增连接",
    "title_edit_connection": "编辑连接",
    "label_name": "名称 *",
    "placeholder_name": "我的服务器",
    "label_host": "主机 *",
    "placeholder_host": "192.168.1.100 或主机名",
    "label_protocol": "协议",
    "label_port": "端口",
    "label_description": "描述",
    "placeholder_description": "可选描述",
    "label_username": "用户名",
    "label_password": "密码",
    "label_private_key": "私钥路径",
    "placeholder_key_auth": "(留空则使用密钥认证)",
    "label_domain": "域",
    "label_context": "Context",
    "placeholder_context": "kubectl context（留空 = 当前）",
    "label_namespace": "命名空间",
    "label_pod": "Pod",
    "label_container": "容器",
    "placeholder_container": "（可选，留空 = 默认）",
    "label_command": "命令",
    "btn_cancel": "取消",
    "btn_save": "保存",
    "err_name_required": "名称为必填项。",
    "err_select_protocol": "请选择协议。",
    "err_invalid_protocol": "选择的协议无效。",
    "err_host_required": "{proto} 连接需要主机。",
    "err_port_number": "端口必须是数字。",
    # -- k8s token auth --
    "label_kubeconfig": "Kubeconfig 路径",
    "label_token": "Token",
    "placeholder_token": "Bearer Token（留空则使用 kubeconfig）",
    "label_skip_tls": "跳过 TLS 验证",
    "label_host_k8s": "主机 (API Server)",
    "err_k8s_token_needs_host": "使用 Token 认证时必须填写 API Server 地址。",
    # -- delete_confirm screen --
    "title_delete": "删除连接？",
    "msg_delete_confirm": "确定要删除 '{name}' 吗？\n此操作无法撤销。",
    "btn_delete": "删除",
    # -- help screen --
    "title_help": "键盘快捷键",
    "help_navigate": "导航连接",
    "help_connect": "连接到选中项",
    "help_disconnect": "断开 / 返回列表",
    "help_add": "新增连接",
    "help_edit": "编辑选中连接",
    "help_delete": "删除连接",
    "help_show_help": "显示此帮助",
    "help_quit": "退出应用",
    "btn_close": "关闭",
    # -- shell_picker screen --
    "title_shell_not_found": "Shell 未找到",
    "msg_shell_failed": "默认 shell 启动失败。\n选择一个替代 shell 尝试：",
    "placeholder_custom_shell": "自定义 shell 路径...",
    "btn_try": "尝试",
    # -- k8s_picker screen --
    "title_k8s_picker": "Kubernetes 资源选择器",
    "label_loading": "加载中...",
    "prompt_select_context": "选择一个 context...",
    "prompt_select_namespace": "选择一个命名空间...",
    "prompt_select_pod": "选择一个 Pod...",
    "label_container_optional": "容器（可选）",
    "prompt_select_container": "选择一个容器...",
    "btn_confirm": "确认",
    "status_fetching_contexts": "正在获取 context...",
    "status_fetching_namespaces": "正在获取命名空间...",
    "status_fetching_pods": "正在获取 Pod...",
    "status_fetching_containers": "正在获取容器...",
    "err_kubectl_not_found": "kubectl 未安装或不在 PATH 中。",
    "err_get_contexts": "获取 context 失败: {error}",
    "err_no_contexts": "未找到 kubectl context。",
    "err_get_namespaces": "获取命名空间失败: {error}",
    "err_get_pods": "获取 Pod 失败: {error}",
    "err_no_pods": "命名空间 '{ns}' 中未找到 Pod。",
    "err_get_containers": "获取容器失败: {error}",
    "err_select_context": "请选择一个 context。",
    "err_select_namespace": "请选择一个命名空间。",
    "err_select_pod": "请选择一个 Pod。",
    # -- protocols/ssh --
    "ssh_connected": "已连接到 {host}:{port}\r\n",
    "ssh_failed": "SSH 连接失败 ({host}:{port}): {error}",
    # -- protocols/telnet --
    "telnet_connected": "已通过 Telnet 连接到 {host}:{port}\r\n",
    "telnet_failed": "Telnet 连接失败 ({host}:{port}): {error}",
    # -- protocols/rdp --
    "rdp_no_client": "未找到 RDP 客户端。请安装 xfreerdp 或 rdesktop。",
    "rdp_unsupported": "不支持的 RDP 平台: {system}",
    "rdp_launched": "已启动外部 RDP 客户端连接 {host}:{port}\r\n",
    "rdp_launch_failed": "启动 RDP 客户端失败: {error}",
    # -- protocols/vnc --
    "vnc_no_client": "未找到 VNC 客户端。请安装 vncviewer（如 tigervnc-viewer）。",
    "vnc_unsupported": "不支持的 VNC 平台: {system}",
    "vnc_launched": "已启动外部 VNC 客户端连接 {host}:{port}\r\n",
    "vnc_launch_failed": "启动 VNC 客户端失败: {error}",
    # -- protocols/k8s --
    "k8s_kubectl_not_found": "kubectl 未在 PATH 中找到",
    "k8s_connected": "已连接到 Pod {label}\r\n",
    "k8s_exec_failed": "K8s exec 失败: {error}",
    "k8s_connect_failed": "无法连接 K8s 集群: {error}",
    "k8s_connect_timeout": "连接 K8s 集群超时，请检查网络或集群配置。",
    # -- session_manager --
    "err_unsupported_protocol": "不支持的协议: {proto}",
    # -- models --
    "k8s_default_context": "(默认)",
    # -- k8s keyboard shortcuts (for k8s help screen) --
    "k8s_key_nav": "上下导航",
    "k8s_key_enter": "Exec 进入 Pod / 切换命名空间",
    "k8s_key_describe": "查看 YAML",
    "k8s_key_edit": "编辑资源",
    "k8s_key_logs": "查看日志 (仅 Pod)",
    "k8s_key_refresh": "刷新列表",
    "k8s_key_search": "搜索过滤",
    "k8s_key_section": "快捷键",
    "help_search": "搜索过滤",
    "help_help": "帮助",
    # -- sftp / file transfer --
    "sftp_title": "SFTP 文件传输",
    "sftp_local": "本地",
    "sftp_remote": "远程",
    "sftp_connecting": "正在建立 SFTP 连接...",
    "sftp_connected": "SFTP 已连接",
    "sftp_connect_failed": "SFTP 连接失败: {error}",
    "sftp_ssh_only": "文件传输仅支持 SSH 连接",
    "sftp_uploading": "正在上传: {name}",
    "sftp_downloading": "正在下载: {name}",
    "sftp_upload_done": "上传完成: {name}",
    "sftp_download_done": "下载完成: {name}",
    "sftp_transfer_failed": "传输失败: {error}",
    "sftp_in_progress": "传输中，请等待...",
    "sftp_nav_hint": "↑↓导航  Enter进入  Tab切换  →上传  ←下载  q关闭",
    "sftp_shortcuts": "文件传输",
    "sftp_col_name": "文件名",
    "sftp_col_size": "大小",
    "sftp_col_modified": "修改时间",
    "sftp_empty_dir": "(空目录)",
    "sftp_dir_label": "<DIR>",
    "help_file_transfer": "文件传输 (SSH)",
    # -- sftp confirm dialog --
    "sftp_confirm_upload_title": "确认上传",
    "sftp_confirm_upload_msg": "上传文件 {filename} 到 {directory}?",
    "sftp_confirm_download_title": "确认下载",
    "sftp_confirm_download_msg": "即将下载 {filename} 到 {directory}",
    "sftp_confirm_download_exists_msg": "检测到文件存在\n即将下载 {filename} 到 {directory}",
    "sftp_btn_yes": "是",
    "sftp_btn_no": "否",
    "sftp_btn_overwrite": "覆盖下载",
    "sftp_btn_rename": "重命名下载",
    # -- sftp header shortcuts --
    "sftp_key_enter": "进入",
    "sftp_key_switch": "切换",
    "sftp_key_upload": "上传",
    "sftp_key_download": "下载",
    "sftp_key_hidden": "隐藏文件",
    "sftp_key_close": "关闭",
    "sftp_key_mkdir": "新建文件夹",
    "sftp_mkdir_title": "新建文件夹",
    "sftp_mkdir_placeholder": "请输入文件夹名称",
    "sftp_mkdir_done": "已创建文件夹: {name}",
    "sftp_mkdir_failed": "创建文件夹失败: {error}",
    # -- ssh jump host --
    "label_jump_host": "跳板机地址",
    "placeholder_jump_host": "跳板机地址（可选）",
    "label_jump_port": "跳板机端口",
    "label_jump_username": "跳板机用户名",
    "label_jump_password": "跳板机密码",
    "label_jump_private_key": "跳板机私钥路径",
    "ssh_jump_connecting": "正在通过跳板机 {jump} 连接...",
}

_EN = {
    # -- header shortcuts --
    "nav": "Navigate",
    "connect": "Connect",
    "disconnect_btn": "Disconnect",
    "add": "Add",
    "edit": "Edit",
    "delete_btn": "Delete",
    "search": "Search",
    "quit": "Quit",
    "exec": "Exec",
    "pods": "Pods",
    "services": "Services",
    "deployments": "Deploy",
    "daemonsets": "DaemonSet",
    "statefulsets": "StatefulSet",
    "namespaces": "Namespace",
    "back": "Back",
    "quit_force": "Quit",
    "describe": "Describe",
    "k8s_edit": "Edit",
    "logs": "Logs",
    "k8s_help": "Help",
    "refresh": "Refresh",
    # -- new resources --
    "jobs": "Jobs",
    "cronjobs": "CronJobs",
    "replicasets": "ReplicaSets",
    "ingresses": "Ingresses",
    "endpoints": "Endpoints",
    "networkpolicies": "NetworkPolicies",
    "configmaps": "ConfigMaps",
    "secrets": "Secrets",
    "persistentvolumes": "PersistentVolumes",
    "persistentvolumeclaims": "PersistentVolumeClaims",
    "storageclasses": "StorageClasses",
    "nodes": "Nodes",
    "events": "Events",
    "resourcequotas": "ResourceQuotas",
    "horizontalpodautoscalers": "HPA",
    "limitranges": "LimitRanges",
    "poddisruptionbudgets": "PodDisruptionBudgets",
    # -- k8s help --
    "title_k8s_help": "K8s Resource Commands",
    "k8s_help_hint": "Press any key to close",
    "switch_namespace": "Switch namespace",
    # -- mode --
    "mode_list": "List Mode",
    "mode_k8s": "K8s Browser",
    "mode_terminal": "Terminal Mode",
    # -- app messages --
    "connecting_to": "Connecting to {name} ({proto})...",
    "connection_failed": "Connection failed: {error}",
    "connection_launched": "Connection launched via external client.",
    "will_return": "Will return to list when session ends.",
    "disconnecting": "Disconnecting...",
    "connection_closed": "[Connection closed]",
    "press_any_key_return": "[Press any key or Ctrl+C to return...]",
    "exec_into_pod": "Exec into pod {name}...",
    "exec_failed": "Exec failed: {error}",
    "k8s_describing": "Fetching YAML for {name}...",
    "k8s_editing": "Editing {name}...",
    "k8s_tailing_logs": "Tailing logs for {name}...",
    "retrying_exec": "Retrying exec into pod {name} with {shell}...",
    # -- time --
    "time_never": "Never",
    "time_just_now": "Just now",
    "time_min_ago": "{n} min ago",
    "time_hr_ago": "{n} hr ago",
    "time_day_ago": "{n} day ago",
    "time_days_ago": "{n} days ago",
    # -- columns --
    "col_status": "Status",
    "col_name": "Name",
    "col_host": "Host",
    "col_protocol": "Protocol",
    "col_port": "Port",
    "col_description": "Description",
    "col_last_connected": "Last Connected",
    # -- scrollback --
    "scrollback_indicator": "scrollback: -{n} lines",
    # -- argparse --
    "app_description": "Tuim - TUI Remote Connection Manager",
    "config_help": "Path to connections YAML config file",
    # -- add_connection screen --
    "title_add_connection": "Add Connection",
    "title_edit_connection": "Edit Connection",
    "label_name": "Name *",
    "placeholder_name": "My Server",
    "placeholder_host": "192.168.1.100 or hostname",
    "label_host": "Host *",
    "label_protocol": "Protocol",
    "label_port": "Port",
    "label_description": "Description",
    "placeholder_description": "Optional description",
    "label_username": "Username",
    "label_password": "Password",
    "label_private_key": "Private Key Path",
    "placeholder_key_auth": "(leave blank for key auth)",
    "label_domain": "Domain",
    "label_context": "Context",
    "placeholder_context": "kubectl context (blank = current)",
    "label_namespace": "Namespace",
    "label_pod": "Pod",
    "label_container": "Container",
    "placeholder_container": "(optional, blank = default)",
    "label_command": "Command",
    "btn_cancel": "Cancel",
    "btn_save": "Save",
    "err_name_required": "Name is required.",
    "err_select_protocol": "Please select a protocol.",
    "err_invalid_protocol": "Invalid protocol selected.",
    "err_host_required": "Host is required for {proto} connections.",
    "err_port_number": "Port must be a number.",
    # -- k8s token auth --
    "label_kubeconfig": "Kubeconfig Path",
    "label_token": "Token",
    "placeholder_token": "Bearer token (blank = use kubeconfig)",
    "label_skip_tls": "Skip TLS Verify",
    "label_host_k8s": "Host (API Server)",
    "err_k8s_token_needs_host": "Host is required when using token authentication.",
    # -- delete_confirm screen --
    "title_delete": "Delete Connection?",
    "msg_delete_confirm": "Are you sure you want to delete '{name}'?\nThis action cannot be undone.",
    "btn_delete": "Delete",
    # -- help screen --
    "title_help": "Keyboard Shortcuts",
    "help_navigate": "Navigate connections",
    "help_connect": "Connect to selected",
    "help_disconnect": "Disconnect / Back to list",
    "help_add": "Add new connection",
    "help_edit": "Edit selected connection",
    "help_delete": "Delete connection",
    "help_show_help": "Show this help",
    "help_quit": "Quit application",
    "btn_close": "Close",
    # -- shell_picker screen --
    "title_shell_not_found": "Shell Not Found",
    "msg_shell_failed": "The default shell failed to start.\nChoose an alternative shell to try:",
    "placeholder_custom_shell": "Custom shell path...",
    "btn_try": "Try",
    # -- k8s_picker screen --
    "title_k8s_picker": "Kubernetes Resource Picker",
    "label_loading": "Loading...",
    "prompt_select_context": "Select a context...",
    "prompt_select_namespace": "Select a namespace...",
    "prompt_select_pod": "Select a pod...",
    "label_container_optional": "Container (optional)",
    "prompt_select_container": "Select a container...",
    "btn_confirm": "Confirm",
    "status_fetching_contexts": "Fetching contexts...",
    "status_fetching_namespaces": "Fetching namespaces...",
    "status_fetching_pods": "Fetching pods...",
    "status_fetching_containers": "Fetching containers...",
    "err_kubectl_not_found": "kubectl is not installed or not in PATH.",
    "err_get_contexts": "Failed to get contexts: {error}",
    "err_no_contexts": "No kubectl contexts found.",
    "err_get_namespaces": "Failed to get namespaces: {error}",
    "err_get_pods": "Failed to get pods: {error}",
    "err_no_pods": "No pods found in namespace '{ns}'.",
    "err_get_containers": "Failed to get containers: {error}",
    "err_select_context": "Please select a context.",
    "err_select_namespace": "Please select a namespace.",
    "err_select_pod": "Please select a pod.",
    # -- protocols/ssh --
    "ssh_connected": "Connected to {host}:{port}\r\n",
    "ssh_failed": "SSH connection failed ({host}:{port}): {error}",
    # -- protocols/telnet --
    "telnet_connected": "Connected to {host}:{port} via Telnet\r\n",
    "telnet_failed": "Telnet connection failed ({host}:{port}): {error}",
    # -- protocols/rdp --
    "rdp_no_client": "No RDP client found. Install xfreerdp or rdesktop.",
    "rdp_unsupported": "Unsupported platform for RDP: {system}",
    "rdp_launched": "Launched external RDP client for {host}:{port}\r\n",
    "rdp_launch_failed": "Failed to launch RDP client: {error}",
    # -- protocols/vnc --
    "vnc_no_client": "No VNC client found. Install vncviewer (e.g. tigervnc-viewer).",
    "vnc_unsupported": "Unsupported platform for VNC: {system}",
    "vnc_launched": "Launched external VNC client for {host}:{port}\r\n",
    "vnc_launch_failed": "Failed to launch VNC client: {error}",
    # -- protocols/k8s --
    "k8s_kubectl_not_found": "kubectl not found in PATH",
    "k8s_connected": "Connected to pod {label}\r\n",
    "k8s_exec_failed": "K8s exec failed: {error}",
    "k8s_connect_failed": "Failed to connect to K8s cluster: {error}",
    "k8s_connect_timeout": "K8s cluster connection timed out. Check network or cluster config.",
    # -- session_manager --
    "err_unsupported_protocol": "Unsupported protocol: {proto}",
    # -- models --
    "k8s_default_context": "(default)",
    # -- k8s keyboard shortcuts (for k8s help screen) --
    "k8s_key_nav": "Navigate up/down",
    "k8s_key_enter": "Exec into Pod / Switch namespace",
    "k8s_key_describe": "View YAML",
    "k8s_key_edit": "Edit resource",
    "k8s_key_logs": "View logs (Pods only)",
    "k8s_key_refresh": "Refresh list",
    "k8s_key_search": "Search filter",
    "k8s_key_section": "Shortcuts",
    "help_search": "Search filter",
    "help_help": "Help",
    # -- sftp / file transfer --
    "sftp_title": "SFTP File Transfer",
    "sftp_local": "Local",
    "sftp_remote": "Remote",
    "sftp_connecting": "Connecting SFTP...",
    "sftp_connected": "SFTP connected",
    "sftp_connect_failed": "SFTP failed: {error}",
    "sftp_ssh_only": "File transfer requires SSH",
    "sftp_uploading": "Uploading: {name}",
    "sftp_downloading": "Downloading: {name}",
    "sftp_upload_done": "Upload done: {name}",
    "sftp_download_done": "Download done: {name}",
    "sftp_transfer_failed": "Transfer failed: {error}",
    "sftp_in_progress": "Transfer in progress...",
    "sftp_nav_hint": "↑↓Nav  Enter=Open  Tab=Switch  →Upload  ←Download  q=Close",
    "sftp_shortcuts": "File Transfer",
    "sftp_col_name": "Name",
    "sftp_col_size": "Size",
    "sftp_col_modified": "Modified",
    "sftp_empty_dir": "(empty)",
    "sftp_dir_label": "<DIR>",
    "help_file_transfer": "File Transfer (SSH)",
    # -- sftp confirm dialog --
    "sftp_confirm_upload_title": "Confirm Upload",
    "sftp_confirm_upload_msg": "Upload {filename} to {directory}?",
    "sftp_confirm_download_title": "Confirm Download",
    "sftp_confirm_download_msg": "Download {filename} to {directory}",
    "sftp_confirm_download_exists_msg": "File already exists\nDownload {filename} to {directory}",
    "sftp_btn_yes": "Yes",
    "sftp_btn_no": "No",
    "sftp_btn_overwrite": "Overwrite",
    "sftp_btn_rename": "Rename & Download",
    # -- sftp header shortcuts --
    "sftp_key_enter": "Enter",
    "sftp_key_switch": "Switch",
    "sftp_key_upload": "Upload",
    "sftp_key_download": "Download",
    "sftp_key_hidden": "Hidden",
    "sftp_key_close": "Close",
    "sftp_key_mkdir": "New Folder",
    "sftp_mkdir_title": "New Folder",
    "sftp_mkdir_placeholder": "Enter folder name",
    "sftp_mkdir_done": "Folder created: {name}",
    "sftp_mkdir_failed": "Failed to create folder: {error}",
    # -- ssh jump host --
    "label_jump_host": "Jump Host",
    "placeholder_jump_host": "Jump host (optional)",
    "label_jump_port": "Jump Port",
    "label_jump_username": "Jump Username",
    "label_jump_password": "Jump Password",
    "label_jump_private_key": "Jump Private Key",
    "ssh_jump_connecting": "Connecting via jump host {jump}...",
}

_TRANSLATIONS = {"zh": _ZH, "en": _EN}


def set_language(lang):
    # type: (str) -> None
    """Override the detected language (for testing)."""
    global _lang
    _lang = lang


def get_language():
    # type: () -> str
    """Return the current language code."""
    return _lang


def t(key, **kwargs):
    # type: (str, **str) -> str
    """Translate a key to the current language, with optional format args."""
    table = _TRANSLATIONS.get(_lang, _ZH)
    text = table.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def t_en(key, **kwargs):
    # type: (str, **str) -> str
    """Translate a key to English (for K8s mode)."""
    text = _EN.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


# Ensure both dictionaries have the same keys
assert set(_ZH.keys()) == set(_EN.keys()), (
    "i18n key mismatch: zh_only={}, en_only={}".format(
        set(_ZH.keys()) - set(_EN.keys()),
        set(_EN.keys()) - set(_ZH.keys()),
    )
)
