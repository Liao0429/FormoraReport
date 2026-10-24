# FormoraReport

[**English**](README.md) | **中文**

Windows 实验报告自动填写工具 —— 导入实验报告模板、实验数据与素材（截图/源代码/SQL/日志），自动识别字段、整理内容、生成图表并插入原模板正确位置，导出规范、可编辑的 **Word** 与 **PDF**。

> **无 AI 模式为默认**：断网、无 API 密钥也能完成全部核心功能。
> **AI 模式可选**：由你主动启用，配置你自己的模型 API，所有生成内容可逐项审核。

---

## 界面效果

*液态玻璃 UI · 浅色模式*

![浅色首页](docs/screenshots/light_home.png)
![浅色字段映射](docs/screenshots/light_mapping.png)

*深色模式*

![深色首页](docs/screenshots/dark_home.png)
![深色字段映射](docs/screenshots/dark_mapping.png)

*测试模板与生成报告效果（LibreOffice 真实渲染）*

![报告模板](docs/screenshots/template_p1.png)
![生成报告第 1 页](docs/screenshots/generated_report_p1.png)
![生成报告第 2 页](docs/screenshots/generated_report_p2.png)

## 功能特性

- 📄 **DOCX 模板解析**：自动识别 `{{占位符}}`、章节、表格、图片、页眉页脚
- 🔗 **字段映射**：模板占位符 ↔ 数据列/常量/图片，自动匹配 + 手动编辑
- 📊 **实验数据处理**：读取 CSV/XLSX/TXT/Markdown/PDF，自动生成数据图表
- 🖼 **截图/图片插入**：把操作截图插入到模板「截图/图表」占位符的**正确位置**
- ⚡ **批量生成**：一个模板 + 多行数据 → 一次生成多份报告
- 👁 **预览与校验**：生成前校验缺失字段，生成后可预览、修改、重新生成
- 📤 **导出**：Word（.docx）默认；PDF 需本机 LibreOffice 或 Word（如实提示）
- 🌗 **现代化界面**：液态玻璃风格，浅色/深色主题，高 DPI 适配
- ⚡ **生成不卡界面**：AI 辅助与批量生成在后台线程执行，界面保持流畅
- 🛡 **安全增强**：输出文件版本化（不覆盖旧版）、AI 端点 SSRF 防护、生成前图片路径校验
- 🔐 **隐私优先**：默认全本地处理；AI 密钥用 Windows DPAPI 加密存储，不落明文

## 运行模式

| 能力 | 无 AI 模式（默认） | AI 模式（可选） |
|------|------------------|----------------|
| 模板解析/字段映射 | ✅ | ✅ |
| 数据处理/图表/批量/导出 | ✅ | ✅ |
| 语义理解素材、辅助整理步骤/结果/结论 | — | ✅ |
| 缺失/矛盾检查 | 基础校验 | AI 审查 |
| 断网/无密钥 | ✅ 完全可用 | — |
| 数据发送到外部 API | 从不 | 仅在你主动点击「AI 辅助填写」时 |

## Windows 系统要求

- Windows 10 / 11（64 位）
- 无需安装 Python / Node 等开发环境（发布包自带运行时）
- 可选：LibreOffice 或 Microsoft Word（用于导出 PDF）
- 可选：AI 模式需可访问的 OpenAI 兼容 API（base_url + model + key）

## 获取方式

- **发布包（EXE）**：从 [Releases](https://github.com/Liao0429/FormoraReport/releases) 下载 `FormoraReport.zip`，解压后运行 `FormoraReport.exe`。
- **从源码构建**：见下文。

## 安装与使用

1. 解压发布包，双击 `FormoraReport.exe` 启动。
2. **文档导入**：选择 `.docx` 实验报告模板（在 Word 中用 `{{字段名}}` 标记待填位置），再选择实验数据（CSV/XLSX/TXT/MD/PDF）。
3. 点击「解析模板与数据」，查看识别出的占位符、章节、表格。
4. **字段映射**：核对自动映射；文本字段直接填写，含「截图/图表」的字段点「选择图片」绑定截图；勾选「自动生成图表」。
5. 点「校验」检查缺失字段，点「生成报告」或「批量生成全部数据行」。
6. **预览**：确认内容后，在生成页/预览页点「导出 PDF」（需 LibreOffice 或 Word）。
7. 可选：在「设置 → AI 智能模式」配置 API 后，映射页点「✨ AI 辅助填写」让模型根据素材整理内容。

## 从源码构建

前置条件：Windows 上安装 **Python 3.14+**（开发与 CI 使用 3.14；3.12+ 应可兼容）。

```bash
# 1. 创建虚拟环境
uv venv .venv
source .venv/Scripts/activate    # Windows git-bash
# 或 .venv\Scripts\activate

# 2. 安装依赖
uv pip install -r requirements.txt

# 3. 运行
python main.py

# 4. 运行测试
python -m pytest tests/ -q

# 5. 打包 EXE
pyinstaller --noconfirm --clean --name FormoraReport --windowed \
  --collect-all matplotlib --collect-all docxtpl main.py
```

## 测试

运行完整测试套件：

```bash
python -m pytest tests/ -q
```

测试目录结构（全部位于 `tests/`）：

| 文件 | 范围 |
|------|------|
| `test_core.py` | 集成测试：模板解析 → 数据读取 → 映射 → 生成 → 校验，使用 `tests/samples/` 真实样例 |
| `test_config.py` | 配置默认值、持久化、DPAPI 密钥加密往返 |
| `test_models.py` | 核心数据模型单元测试（`TemplateInfo`、`DataSource`、`FieldMapping`、`ReportTask`） |
| `test_services.py` | 日志分类、历史记录、报告服务（自动图表/单份生成）的单元与集成测试 |
| `test_ai_client.py` | AI 客户端离线测试（URL 拼接、请求体、响应解析），HTTP 层用 mock，无需网络 |
| `test_ui.py` | 仅 Windows 的 UI 冒烟测试（运行 `scripts/ui_smoke_test.py` 无头模式） |

保证：

- **无网络**：所有测试离线运行，AI 客户端测试通过 mock HTTP 层完成。
- **无私有数据**：测试使用生成样例，输出写入操作系统临时目录。
- **可重复**：样例仅在缺失时重新生成，套件可反复运行。
- **Windows 相关**：DPAPI 加密与 UI 冒烟测试依赖 Windows；CI 在 `windows-latest` 上运行它们。

## 测试与已知限制

- 自动化测试：核心解析/数据/映射/生成/校验/配置加密/UI 冒烟（`tests/`）。
- PDF 文本提取只对**机器生成 PDF**可靠；扫描件需 OCR（可选增强，未默认捆绑）。
- 旧版 `.doc` 不支持，请先在 Word 中另存为 `.docx`。
- DOCX→PDF 依赖本机 LibreOffice 或 Word；两者皆无时仅导出 DOCX 并明确提示。

## 开源许可证

本项目采用 **MIT License**。第三方依赖许可证见 [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)。
涉及依赖包括：python-docx (MIT)、docxtpl (LGPL-2.1)、pdfplumber (MIT)、openpyxl (MIT)、pandas (BSD-3)、matplotlib (PSF)、PySide6 (LGPL-3)、PyInstaller (GPL-2.0 带商业例外) 等。

## 贡献

欢迎提交 Issue 与 Pull Request。请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 路线图

- OCR 增强（PaddleOCR 可选）
- 模板中心（保存/管理常用模板）
- 更丰富的 AI 结构化提取与来源追踪可视化
- 安装包（NSIS/Inno Setup）与自动更新
- 更多文档格式支持

## 隐私说明

无 AI 模式下所有文件仅在本机处理，不联网。AI 模式仅在你主动点击时发送必要内容到你配置的 API。API 密钥用 Windows DPAPI 加密存储。详见 [SECURITY.md](SECURITY.md)。