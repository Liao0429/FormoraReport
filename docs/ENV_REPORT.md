# FormoraReport 环境检查报告（P0）

> 生成时间：2026-10-22 20:20
> 检查方式：实际命令执行（非假设）
> **后续更新（2026-10-24）**：实际开发与 CI 已改用 **Python 3.14.7**（详见 [DECISIONS.md](DECISIONS.md) D-001）。下表为本报告生成时的初版环境快照。

## 系统信息

| 项目 | 值 |
|------|-----|
| 操作系统 | Microsoft Windows 10 专业版 |
| 版本 | 10.0.19045（22H2） |
| 架构 | 64 位 |
| GPU | NVIDIA GeForce GTX 1080 Ti + GameViewer Virtual Display Adapter |
| 桌面会话 | explorer 运行中（本进程上下文 UserInteractive=False） |

## 开发工具清单

| 工具 | 版本 | 状态 | 说明 |
|------|------|------|------|
| Git | 2.55.0.windows.5 | ✅ 可用 | 已初始化仓库 |
| Python | 3.12.10 | ✅ 可用 | 位于用户目录 |
| pip | 25.0.1 | ✅ 可用 | |
| uv | 0.13.1 | ✅ 可用 | 可快速建虚拟环境/装包 |
| Node.js | v26.8.1 | ✅ 可用 | |
| npm | 11.19.0 | ✅ 可用 | |
| Codex CLI | 0.162.1 | ✅ 可用 | 已接 unisound u2-flash |
| Claude Code | 2.1.302 | ✅ 可用 | 已接 unisound u2-flash |
| .NET SDK | — | ❌ 未安装 | 若选 C# 需安装（较大依赖） |
| Rust/Cargo | — | ❌ 未安装 | 若选 Tauri 需安装（较大依赖） |

## 初步技术栈倾向（待 P1 调研后定案）

当前机器 **无 .NET SDK、无 Rust**，若选 C#/Tauri 需额外安装工具链。
Python 3.12 + PySide6 可直接使用，且 Python 文档处理生态（python-docx、openpyxl、
pdfplumber、PyMuPDF、Pillow、matplotlib、pandas）成熟，适合本地文档处理。
最终主技术栈由《技术选型报告》决定，需满足：
- Windows 10/11 首要目标
- 本地优先、离线可用
- 用户无需安装 Python/Node
- 可打包独立 EXE
- 启动快、内存低、代码结构清晰可扩展

## 缺失项与最小安装清单（若定案对应技术栈）

| 候选技术栈 | 需要安装 | 体积/成本 |
|-----------|---------|----------|
| Python+PySide6 | 无额外开发工具（PyInstaller 打包） | 低 |
| C#+.NET+WPF/WinUI3 | .NET SDK 8/9 | 中（约几百MB SDK） |
| Tauri+Web | Rust 工具链 | 中（约几百MB） |

## 结论
P0 环境检查完成。开发工具充足（Git/Python/Node/Codex/Claude Code），
可立即开展 P1 调研。最终技术栈待 P1 报告定案后记录决策。