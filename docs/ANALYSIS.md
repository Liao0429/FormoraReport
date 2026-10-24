# FormoraReport 项目现状与代码结构分析

> 分析时间：2026-10-24
> 分析方法：目录遍历 + 全源码阅读 + git 历史与跟踪状态核查 + 隐私/路径扫描 + 环境验证
> 用途：作为后续重构、开源发布、维护的**直接依据**。

---

## 一、项目概览

**FormoraReport** 是一个 Windows 桌面应用：导入实验报告模板（.docx）、实验数据（CSV/XLSX/TXT/MD/PDF）与素材（截图/代码/SQL），自动识别字段、整理内容、生成图表并插入原模板正确位置，导出可编辑的 Word（.docx）与 PDF。

- **许可证**：MIT（`LICENSE`）
- **开发语言**：Python（实际运行环境 3.14.7；文档多写 3.12，见问题 5）
- **UI**：PySide6（Qt6），6 页面 + 深浅主题
- **无 AI 模式为默认**：断网、无密钥可完成全部核心功能；AI 模式可选（OpenAI 兼容 API）
- **Git**：分支 `master`，5 个提交，工作树干净
- **规模**：`src/formora` 约 45 个 `.py` 文件（含页面），源码总计约 2400 行（不含依赖）；`tests/` 约 19 个测试用例
- **测试状态**：**当前无法运行**（`.venv` 已失效，见问题 1）

### 阶段状态（来自 git 提交 + 看板）

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 环境与工具检查 | ✅ 完成 |
| P1 | GitHub 开源调研（110 仓库） | ✅ 完成 |
| P2 | 技术选型与系统架构 | ✅ 完成 |
| P3 | UI/UX 设计与交互原型 | ✅ 完成 |
| P4 | 核心功能（无 AI 模式） | ✅ 基本完成 |
| P5 | AI 智能模式 | 🚧 部分完成（来源追踪未落盘，见问题 12） |
| P6 | 自动化测试与性能基准 | ✅ 基本完成（PERF_REPORT 已产出） |
| P7 | Windows 打包 EXE | ✅ 基本完成（dist/ 已产出） |
| P8 | GitHub 开源准备 | ✅ 大部分完成（文档齐全；仍有隐私问题，见问题 2/3） |

> `docs/KANBAN.md` 仍显示 P6 进行中、P7/P8 待开始，与 git 提交内容不一致（见问题 6）。

---

## 二、技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| UI | PySide6 >=6.6 | 6 页面导航、QSS 深浅主题、高 DPI |
| DOCX 解析/生成 | python-docx + docxtpl | 占位符替换、表格/图片注入、格式保真 |
| 数据处理 | pandas + openpyxl | CSV/XLSX 读取 |
| PDF 提取 | pdfplumber | 仅机器生成 PDF 可靠 |
| 图表 | matplotlib（Agg 后端） | 折线/柱状图 → PNG |
| 图片 | Pillow | 通过 docxtpl InlineImage 注入 |
| PDF 导出 | LibreOffice 无头 / Word COM | 两者皆无则明确提示 |
| AI | OpenAI 兼容 HTTP API（urllib） | 用户自配 base_url/model/key |
| 密钥 | Windows DPAPI（ctypes，无第三方库） | 密文存 `%APPDATA%/FormoraReport/config.json` |
| 配置/历史/日志 | JSON / JSONL / logging 滚动文件 | 本地存储 |
| 打包 | PyInstaller | `FormoraReport.spec` + CI 已配置 |
| 测试 | pytest | tests/ 约 19 个用例 |
| CI | GitHub Actions（windows-latest） | push/PR 触发 test + build EXE |

---

## 三、模块图

```
main.py  ──►  src/formora/ui/app.py（QApplication 入口）
                  │
   ┌──────────────┴───────────────────────────────┐
   │  UI 层 (PySide6)                                │
   │  main_window（侧边栏导航 + 页面栈）              │
   │  pages/ home · import · mapping · generate ·     │
   │        preview · settings                       │
   │  widgets（Card/按钮/文件行）  theme（深浅 QSS）  │
   │  app_state（跨页共享任务/模板/数据/映射）         │
   └──────────────┬───────────────────────────────┘
                  │
   ┌──────────────┴───────────────────────────────┐
   │  services 应用服务层                             │
   │  config（DPAPI 密钥加密 / 配置 JSON）              │
   │  history（任务历史 JSONL）                         │
   │  logging_setup（滚动日志 + 错误分类映射）           │
   └──────────────┬───────────────────────────────┘
                  │
   ┌──────────────┴───────────────────────────────┐
   │  core 核心功能层                                 │
   │  template_parser（DOCX 占位符/循环/章节/表格）     │
   │  data_reader（CSV/XLSX/TXT/MD/PDF）              │
   │  mapper（字段↔数据列自动/手动映射）               │
   │  chart（matplotlib 折线/柱状图）                   │
   │  generator（docxtpl 渲染 + 图片注入）             │
   │  validator（缺失/空值校验）                       │
   │  pdf_exporter（LibreOffice/Word COM → PDF）      │
   │  models（TableInfo/TemplateInfo/FieldMapping/…） │
   │  errors（用户/格式/外部依赖/程序缺陷分类）         │
   └──────────────┬───────────────────────────────┘
                  │
   ┌──────────────┴───────────────────────────────┐
   │  ai 可选层（仅用户启用时导入）                     │
   │  client（OpenAI 兼容 /chat/completions）          │
   │     extract_fields（素材→字段）                   │
   │     review_report（缺失/矛盾审查）                │
   └───────────────────────────────────────────────┘
```

### 核心数据流（无 AI 模式）

```
导入模板(.docx) ──► template_parser.parse_template ──► TemplateInfo(占位符/章节/表格/图片)
导入数据 ──► data_reader.read_data ──► DataSource(列/行/文本)
        │
        ▼
mapper.auto_map ──► FieldMapping[]（数据列/常量/文本/图片）
        │
        ▼
mapping_page 收集值 → generator.generate_report(docxtpl 填充 + InlineImage 图表)
        │
        ▼
校验(validator) → 输出 .docx → preview 读取文本 → pdf_exporter 导出 PDF
```

---

## 四、功能现状

### 已实现（可验证）

- ✅ DOCX 模板解析：`{{占位符}}`、`{% for %}` 循环块、章节识别、表格/图片/页眉页脚检测
- ✅ 数据读取：CSV（多编码尝试）、XLSX、TXT/MD、PDF（pdfplumber）
- ✅ 字段映射：自动映射（精确/别名/包含匹配）+ 手动编辑（数据列/常量/图片三类来源）
- ✅ 图表生成：折线图、柱状图 → PNG
- ✅ 报告生成：docxtpl 占位符替换、图片 InlineImage 注入到原位置、循环表格渲染
- ✅ 校验：缺失字段、空值提示（error/warning/info）
- ✅ 批量生成：一个模板 + 多行数据 → 每行一份 DOCX
- ✅ 预览：读取生成 DOCX 的段落/表格文本
- ✅ PDF 导出：LibreOffice 无头或 Word COM，均无则明确提示
- ✅ 图片绑定：字段名含「截图/图/图表/chart」自动按图片处理
- ✅ 自动图表插入：表格型数据自动生成图表并注入「图表」占位符
- ✅ AI 辅助填写（可选）：OpenAI 兼容 API，结构化 JSON，隐私确认弹窗
- ✅ DPAPI 密钥加密存储、深浅主题、输出目录配置
- ✅ 历史记录（JSONL）、滚动日志
- ✅ CI（GitHub Actions）+ PyInstaller 打包配置 + 开源规范文件齐全

### 未完成 / 与架构承诺有差距

- ⚠️ **来源追踪未真正落地**：架构（`docs/ARCHITECTURE.md`）承诺每个 AI 生成值带 `source`/`confidence` 并做来源追踪可视化；当前 `ai/client.py` 只返回 `source` 字段，UI 仅展示「待确认」标记，**没有把 source 持久化或可视化**。
- ⚠️ **AI 审查接口 `review_report` 已实现但未接入 UI**（设置页/映射页只用了 `extract_fields`）。
- ⚠️ **模板中心/模板管理未实现**（路线图中的「模板中心」仍是规划）。
- ⚠️ **OCR 增强（PaddleOCR）、docling 结构化** 仅停留在调研/规划，未集成（符合「可选增强」定位）。
- ⚠️ **安装包（NSIS/Inno）与自动更新** 未实现（路线图待办）。

---

## 五、问题清单

### P0 —— 阻断 / 隐私（开源与运行前必须处理）

1. **`.venv` 已失效，项目当前无法运行测试**
   - `pyvenv.cfg` 的 `home` 指向 `%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-...`，该 uv 托管解释器已不存在（项目从 G: 迁到 H: 后失效）。
   - `python -m pytest tests/` 报 `uv trampoline failed to spawn Python child process ... entity not found`。
   - **修复**：在 H:\FormoraReport 重建虚拟环境（`uv venv .venv` 或 `python -m venv .venv`），再 `pip install -r requirements.txt`，然后重跑测试。

2. **`reports/github_raw/*.json` 与 `reports/readmes/*.md` 被 git 跟踪，含第三方原始内容**
   - 这些文件是 GitHub API 原始抓取结果，包含**第三方仓库的完整 README 正文**（其中有 SQL 注入/渗透测试命令、LinkedIn 链接、仓库 ID 等）。
   - 作为开源仓库，这带来三类风险：a) 可能含敏感/冒犯性内容；b) 复制第三方 README 存在许可证义务；c) 与 `docs/ARCHITECTURE.md`「仓库不含无关数据」的承诺相悖，且增加仓库体积。
   - **修复**：开源前删除 `reports/github_raw/`、`reports/readmes/` 与 `reports/github_candidates_raw.csv` 的跟踪（`git rm -r --cached`，保留本地文件），仅保留聚合后的 `reports/RESEARCH_REPORT.md`。如需存档原始数据，移到仓库外。已由 PRIVACY_AUDIT.md 落实。

3. **`docs/DECISIONS.md` 出现个人称呼「项目负责人」**
   - 第 41 行「先与项目负责人确认」。这是用户个人身份信息，开源前应改为通用表述（如「项目负责人」）。

### P1 —— 可维护性 / 一致性

4. **5 个被跟踪文件硬编码旧盘符 `G:\FormoraReport`**
   - `docs/KANBAN.md`、`scripts/demo_cli.py`（docstring）、`scripts/github_research.py`、`scripts/github_aggregate.py`、`scripts/github_curated.py`。
   - 项目已位于 H:，这些硬编码路径一旦再移动/换机必然再次失效。
   - **修复**：全部改为基于 `Path(__file__).parent.parent` 的相对路径（如 `scripts/github_research.py` 的 `OUT_DIR` 改为 `Path(__file__).resolve().parent.parent / "reports/github_raw"`）。

5. **Python 版本文档不一致**
   - `README.md`/`docs/ARCHITECTURE.md`/`docs/ENV_REPORT.md` 写 **Python 3.12**；但 `pyvenv.cfg` 与 `reports/PERF_REPORT.md` 均为 **3.14.7**。
   - **修复**：统一文档版本说明（建议以 CI 固定 3.12 为准，或明确当前开发用 3.14，发布用 3.12）。

6. **`docs/KANBAN.md` 阶段状态过时**
   - git 最新提交已包含 P6 性能基准、P7 打包 EXE、P8 开源规范，但看板仍标 P6 进行中、P7/P8 待开始。
   - **修复**：更新看板状态，避免误导后续开发者。

7. **调研脚本功能重复**
   - `scripts/github_aggregate.py` 与 `scripts/github_curated.py` 逻辑高度重叠（都是把 `github_raw/*.json` 汇总为 CSV/打印）。
   - **修复**：合并为一个脚本；若按问题 2 删除原始 JSON，这两个脚本也应一并删除。

### P2 —— 代码质量 / 结构

8. **`mapping_page.py` 职责过重（486 行，接近 500 行红线）**
   - 单文件承担：映射表格构建、类型切换、图片选择、校验、单份生成、批量生成、AI 辅助、自动图表。事件回调环环相扣，难以单测。
   - **建议**：把「生成/批量生成」抽到 `services/report_service.py`，「AI 辅助」抽到 `services/ai_assist.py`，页面只保留 UI 交互与状态同步。

9. **`settings_page.py` 的 `_test_ai` 绕过 Config 构造临时对象**
   - `tmp = _C.__new__(_C)` + 手工填 `data` dict 很脆弱，且测试连接逻辑与 `ai/client.py` 重复。
   - **建议**：在 `ai/client.py` 提供 `test_connection(base_url, model, key) -> None`，设置页直接调用。

10. **`template_parser.py:61` 引用未导入的 `BugError` —— 潜在运行时 NameError**
    - 文件头只 `from .errors import DocumentFormatError, UserError`，但在 python-docx 缺失的兜底分支 `raise BugError(...)`。一旦 python-docx 未安装，会抛 `NameError` 而非友好提示——恰好在最需要友好报错的路径上失败。
    - **修复**：`from .errors import BugError`（或改用 `UserError`/`ExternalDependencyError`）。
    - 附带：`data_reader.py` 在 pandas/pdfplumber 缺失时抛 `UserError`，语义上更接近依赖错误，建议统一为 `ExternalDependencyError` 或 `BugError`。

11. **`generator.py` 重复解析模板**
    - `generate_report` 内部再次调用 `parse_template` 做占位符校验，而 UI 在导入页已解析过 `TemplateInfo`。批量生成时每份都会重复解析，增加耗时（PERF 中单文档 165ms 有一部分来自重复解析）。
    - **建议**：`generate_report` 增加可选 `template_info: TemplateInfo | None` 参数，调用方传入缓存。

12. **AI「来源追踪」未落盘（见「未完成」）**
    - `ai/client.py` 返回的 `source`/`needs_confirmation` 只用于界面提示，未保存到历史记录或报告中。
    - **建议**：把 AI 生成的 `source` 写入 `ReportTask.logs` 或 `FieldMapping`（新增字段），并在预览页展示。

13. **`validate_context` 对非核心占位符仅给 info 级提示**
    - 核心字段（实验名称/目的/…）检查合理；但对任意占位符只提示 info，用户可能忽略。可在 UI 中区分「缺失必填」与「可选为空」。

---

## 六、优化优先级与重构建议

| 优先级 | 事项 | 对应问题 | 预期收益 |
|------|------|----------|----------|
| **P0-1** | 重建 `.venv` 并跑通 19 个测试 | 1 | 恢复可验证的开发/CI 基础 |
| **P0-2** | 开源前 `git rm` 原始抓取物（github_raw/readmes），只留聚合报告 | 2 | 隐私/合规/体积 |
| **P0-3** | 替换 `docs/DECISIONS.md` 中的个人称呼 | 3 | 隐私 |
| **P0-4** | 修复 `template_parser` 未导入 `BugError` 的 NameError | 10 | 消除潜在崩溃路径 |
| **P1-1** | 5 个文件的 `G:\` 硬编码改为相对路径 | 4 | 可移植性 |
| **P1-2** | 统一 Python 版本说明、更新 KANBAN 状态 | 5, 6 | 文档一致性 |
| **P1-3** | 合并/删除重复的调研汇总脚本 | 7 | 精简仓库 |
| **P2-1** | 拆分 `mapping_page.py`（生成/AI 抽到 services） | 8 | 可测性、可维护性 |
| **P2-2** | 抽取 `test_connection` 到 `ai/client.py` | 9 | 消除重复与脆弱对象构造 |
| **P2-3** | `generate_report` 支持传入已解析 `TemplateInfo` | 11 | 性能（批量尤其明显） |
| **P2-4** | AI source 持久化 + 预览展示 | 12 | 兑现「来源追踪」承诺 |
| **P2-5** | 校验分级提示优化 | 13 | 用户体验 |

### 重构落地顺序建议（供后续任务拆解）

1. 先做 P0 四项（重建环境、清仓库、隐私、修 NameError），用 `python -m pytest tests/ -q` 作为验收。
2. 再做 P1 三项（路径、文档、脚本精简），提交前 `git diff --stat` 复核。
3. P2 结构优化按「抽服务 → 加测试 → 验证无回归」逐个进行，每个改动保持现有 19 个测试通过。

---

*本文件由自动分析生成；所有「问题」均基于实际代码/仓库状态，未作虚构。*