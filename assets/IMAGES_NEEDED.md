# README 图片占位符

此文件列出了 README.md 中需要替换的图片。请准备以下截图并替换到对应位置。

## 需要的图片

### 1. 主界面预览图
- **文件路径**: `.github/assets/screenshot.png`
- **内容**: Tuim 主界面截图，显示连接列表
- **建议尺寸**: 1200x800 或类似比例
- **位置**: README.md 开头

### 建议添加的其他图片

如果需要更详细的文档，可以考虑添加以下图片：

```
.github/assets/
├── screenshot.png           # 主界面预览
├── k8s-browser.png         # K8s 资源浏览器界面
├── terminal-mode.png       # 终端模式界面
├── connection-edit.png     # 连接编辑界面
├── k8s-help.png           # K8s 命令帮助界面
└── search-filter.png       # 搜索过滤功能演示
```

## 截图建议

1. **主界面截图**: 显示连接列表，包含不同协议的连接项
2. **K8s 浏览器**: 显示 Pod 列表或 Deployment 列表
3. **终端模式**: 显示 SSH 会话中的命令输出
4. **编辑界面**: 显示新增/编辑连接的表单
5. **帮助界面**: 显示 K8s 命令帮助弹窗

## 添加图片后的 README 更新

在 README.md 中添加更多图片示例：

```markdown
### K8s 资源浏览器
![K8s 资源浏览器](.github/assets/k8s-browser.png "K8s 资源浏览器界面")

### 终端模式
![终端模式](.github/assets/terminal-mode.png "SSH 终端界面")

### 连接编辑
![连接编辑](.github/assets/connection-edit.png "编辑连接表单")
```