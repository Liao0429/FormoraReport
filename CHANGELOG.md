# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 与语义化版本（SemVer）。

# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 与语义化版本（SemVer）。

## [2.0.0] - 2026-10-24

### Added
- **液态玻璃 UI（iOS Liquid Glass 风格）**：无边框窗口、自定义标题栏、半透明玻璃卡片 + 高光描边、蓝紫渐变按钮
- Windows 11 Mica 系统背景（DWM 封装，自动降级 QSS 渐变）
- 页面切换/窗口启动淡入动画（尊重系统「减少动态效果」）
- 真实界面截图脚本（`scripts/capture_screenshots.py`，隐私优先，不抓取屏幕其他窗口）

### Changed
- 版本号体系重置为 2.0.0（仓库历史重新初始化，彻底清除早期开发过程中的第三方调研数据与个人痕迹）
- 提交作者邮箱改用 GitHub noreply 匿名地址
- `ui/theme.py`、`ui/main_window.py` 重构，新增 `ui/window_effects.py`、`ui/animations.py`

### 兼容性
- 核心 API 不变；60 项自动化测试通过。

## [1.2.0] - 2026-10-24

### Added
- **液态玻璃 UI 升级**：全新 iOS Liquid Glass 风格主题（浅色/深色）
  - 无边框窗口 + 自定义标题栏（最小化/最大化/关闭，支持拖动）
  - Windows 11 Mica 系统背景（自动检测，不可用时降级为 QSS 渐变）
  - 半透明玻璃卡片 + 白色高光描边 + 大圆角（16-22px）
  - 主按钮蓝紫渐变 + 高光边，悬停提亮/按下下沉反馈
  - 页面切换淡入动画（180ms，尊重系统「减少动态效果」）
  - 窗口启动淡入动画
- `ui/window_effects.py`：DWM Mica/Acrylic/圆角/深色边框封装（ctypes，无第三方依赖）
- `ui/animations.py`：轻量动画工具（fade_in / page_transition）
- `scripts/capture_screenshots.py`：真实界面截图脚本（含 Mica 渲染）

### Changed
- `ui/theme.py`：重写为液态玻璃 QSS（颜色 token 化，浅色/深色两套）
- `ui/main_window.py`：无边框重构，新增标题栏/系统玻璃/动画集成

### 兼容性
- 全部为 UI 层改动，核心 API 不变；60 项自动化测试通过。

## [0.1.0] - 2026-10-22（规划中）
- MVP 里程碑：导入 → 映射 → 预览 → 生成 DOCX → 验证
- 基础模板管理、批量处理、历史记录、UI 动效
- Windows 打包（EXE）
- 开源仓库规范文件
