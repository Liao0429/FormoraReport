# FormoraReport 跨平台/移动端扩展评估

> 评估视角：跨平台 / 移动端架构专家
> 当前版本：2.4.0（PySide6 桌面应用，Windows 优先）
> 目标：评估能否/如何扩展到 Android(APK)、iOS、微信小程序

---

## 0. 结论先行

- **核心逻辑与 UI 已基本解耦**：`core/` 与 `services/` 全部为纯 Python，**0 处 Qt 依赖**（74 处 Qt 引用全部落在 `ui/` 目录 11 个文件内）。
- **后端 API 化条件成熟**：建议用 FastAPI 把 `core/` + `services/` 包装成 REST 服务，微信小程序/移动端作为客户端调用。
- **不要在手机端内嵌 Python 核心**：依赖链太重（pandas、matplotlib、pdfplumber、docxtpl/lxml、openpyxl、Pillow），Android（Chaquopy）勉强、iOS（BeeWare）极痛苦，且 docx 渲染在端侧毫无必要。**正确形态是「小程序/App 前端 + 服务器端 Python 引擎 + 可选移动端壳」**。
- **主要阻塞点是平台耦合，集中在两个文件**：`services/config.py`（Windows DPAPI + `APPDATA`/`USERPROFILE`）和 `core/pdf_exporter.py`（Word COM + Windows 版 LibreOffice 路径）。此外 `core/chart.py` 的中文字体候选是 Windows 字体。

---

## 1. 已与 UI 解耦、可直接复用到后端/移动端的核心逻辑

| 模块 | 依赖 | 平台耦合 | 可复用性 |
|---|---|---|---|
| `core/models.py` | 仅 stdlib | 无 | ✅ 直接复用（服务端 DTO 可基于此） |
| `core/errors.py` | 仅 stdlib | 无 | ✅ 直接复用（异常→HTTP 状态映射） |
| `core/template_parser.py` | python-docx, re | 无 | ✅ 直接复用（服务端解析模板） |
| `core/mapper.py` | 仅 stdlib | 无 | ✅ 直接复用（自动映射纯算法） |
| `core/validator.py` | 仅 stdlib | 无 | ✅ 直接复用（校验纯算法） |
| `core/data_reader.py` | pandas, pdfplumber, openpyxl | 无（路径来自调用方） | ✅ 直接复用（服务端读 CSV/XLSX/TXT/MD/PDF） |
| `core/generator.py` | docxtpl, python-docx | 无 | ✅ 直接复用（服务端渲染 DOCX，核心价值） |
| `core/chart.py` | matplotlib(Agg) | ⚠️ 中文字体为 Windows 字体（Microsoft YaHei/SimHei/SimSun） | ✅ 逻辑可复用；服务端需装 Noto Sans CJK 或打包字体 |
| `ai/client.py` | urllib 标准库 | 无（纯 HTTP） | ✅ 直接复用（OpenAI 兼容客户端，含 SSRF 防护） |
| `services/report_service.py` | 上述 core + history | 无 Qt；路径处理跨平台安全 | ✅ 逻辑复用；但函数签名接收 `state` 对象（见 §4） |
| `services/history.py` | stdlib, JSONL | 无（路径来自 config） | ✅ 复用，但多用户时建议换 DB |
| `services/logging_setup.py` | stdlib logging | 无 | ✅ 复用 |

**关键结论**：`report_service.py` 文件头自述「所有函数为纯逻辑（不含 Qt 依赖）」属实——全文无任何 Qt import。UI 页面（如 `mapping_page.py`）通过 `from formora.services import report_service` 调用纯函数，方向正确。

---

## 2. 仍耦合在 PySide6（UI 层）里的逻辑

74 处 Qt 引用全部在 `ui/`，其中真正「业务编排」而非纯控件代码的，是以下三处：

1. **`ui/pages/mapping_page.py` — AI 辅助编排（`_ai_assist` / `_on_ai_done`）**
   - 内含完整业务流程：隐私确认 → 收集映射 → 构造 fields 列表 → 取素材文本 → 调 `client.extract_fields` → 把 AI 结果写回 mapping（改 `source_type=constant`、记 `source`/`needs_confirmation`）→ 记日志 → 刷新表格。
   - 这段「AI 结果落地到映射」的业务规则目前**只存在于 Qt 页面**，API 层无法复用。
   - 同样 `_collect_mappings()`（读表格控件回填 mapping）与 `_remap` 逻辑也耦合在页面。

2. **`ui/pages/generate_page.py` — 导出编排**
   - `_export_pdf` / `_export_batch_pdf`：从 `state.output_path` / `last_batch_dir` 遍历 DOCX、调用 `pdf_exporter`、串行转换、汇总结果。这些「导出任务编排」应上提到服务层，页面只留按钮。

3. **`ui/pages/preview_page.py` — 报告文本抽取 + AI 审查编排**
   - `refresh()` / `_ai_review()` 里的 `Document(path)` 抽取段落/表格文本、拼 `_ai_sources_text()`、调 `client.review_report`、回填 UI。**报告文本抽取逻辑应抽成纯函数**（如 `services/report_reader.py: extract_report_text(path) -> str`），供 API 预览与 AI 审查复用。

> 注意：`ui/pages/mapping_page.py` 里 18 处 Qt 引用，绝大多数是表格/下拉/复选框等控件代码，属正常 UI。真正的问题是**业务流程脚本被写死在控件回调里**。

---

## 3. 建议的跨平台产品架构

### 3.1 总体形态

```
┌────────────────────────────┐        ┌──────────────────────────────┐
│  微信小程序 / uni-app 前端   │  HTTPS │    FastAPI 后端（Python 引擎）  │
│  · 文件上传(template/data)   │───────▶│  · 模板解析 / 数据读取 / 自动映射 │
│  · 字段映射表格交互           │        │  · 报告生成(DOCX) / 批量生成(ZIP)│
│  · AI 辅助填写（透传）        │◀───────│  · PDF 导出(LibreOffice 无头)    │
│  · 在线预览(PDF/文本)         │  JSON  │  · AI 抽取 / AI 审查            │
│  · 下载 DOCX/PDF            │  +文件  │  · 任务历史                     │
└────────────────────────────┘        └──────────────────────────────┘
        │ 可选：uni-app 编译出 APK/iOS(WebView 或原生控件)
        ▼
  Android APK / iOS App（同一套前端代码）
```

### 3.2 后端分层

```
src/formora/            # 纯 Python 引擎（现状，保持）
  core/                 # 模板解析/数据读取/映射/生成/图表/校验/PDF(改)
  services/             # report_service, config(改), history, logging
  ai/client.py          # OpenAI 兼容客户端（复用）
  api/                  # ← 新增 FastAPI 层（建议新增，独立包 src/formora_api 更干净）
    routers/
      templates.py      # POST /templates/parse  → TemplateInfo
      data.py           # POST /data/read       → DataSource
      mappings.py       # POST /mappings/auto    → [FieldMapping]
      ai.py             # POST /ai/extract, /ai/review
      reports.py        # POST /reports/generate → docx 二进制
                        # POST /reports/batch    → zip
                        # POST /reports/{id}/pdf → pdf 二进制
      jobs.py           # 异步任务（可选）
    dependencies.py     # 鉴权(JWT/API Key)、文件存储(S3/本地)、任务持久化
    schemas.py          # Pydantic 请求/响应模型（可复用 core.models 字段）
```

关键点：
- **REST 以「文件上传 → 解析 → 映射 → 生成 → 下载」为资源流**，与桌面端流程一一对应，前端天然好接。
- **文件/任务持久化**：桌面端用本地路径，服务端要改为「对象存储/服务端目录 + 任务 ID」。历史记录不应存客户端绝对路径。
- **PDF 转换**：服务端安装 headless LibreOffice，去掉 `win32com` 分支；`pdf_exporter.find_libreoffice()` 改 `shutil.which` 优先（Linux 通用），Windows 候选路径保留。
- **鉴权与密钥**：AI API Key 存服务端（每用户配置，经 `SecretStore` 抽象），前端只传「是否启用 AI + 配置 ID」，**绝不把密钥下发到小程序**。
- **图表中文字体**：Docker 镜像装 `fonts-noto-cjk`，并把 `chart.py` 字体候选改为运行时探测（`fc-list` 或 `matplotlib.font_manager` 搜索 Noto）。

### 3.3 前端选型

- **首选：uni-app（Vue3）**。一次编写 → 编译到微信小程序 + H5 + App(Android/iOS)。后端纯 HTTP，前端不碰 Python。
- 小程序文件选择：`wx.chooseMessageFile` / `uni.chooseFile` → `uni.uploadFile` 上传到后端。
- DOCX 无法在小程序内原生预览：**服务端统一转 PDF**，前端用 `web-view` 或 PDF 组件展示；文本预览走 `extract_report_text` 接口。
- APK/iOS：用 uni-app 编译成 App，或包一层 WebView(TWA/Capacitor) 指向同一套 H5。**不建议内嵌 Python**。

### 3.4 关于「在手机上内嵌 Python」的可行性

| 方案 | Android | iOS | 结论 |
|---|---|---|---|
| Chaquopy（Android 内嵌 CPython） | 可行但重：pandas/matplotlib/lxml 需交叉编译，APK 体积大 | 不支持 | 仅在强离线需求时考虑，且要砍掉 pandas/pdfplumber |
| BeeWare / PyObjC | 可跑但依赖轮子难 | 极痛苦 | 不推荐 |
| Kivy / Toga | 可跑但 UI 生态弱 | 一般 | 不推荐 |

**推荐**：核心价值（docx 渲染、格式保留）应放在服务器，端侧只做交互与展示。若未来有离线刚需，再评估把「模板渲染子集」用 Chaquopy 单独打包。

---

## 4. 当前代码里阻碍复用的耦合点清单

### 硬阻塞（不改就无法上服务器/跨平台）

1. **`services/config.py` — Windows DPAPI 硬编码 + 环境变量**
   - 行 18-22：`APPDATA`、`USERPROFILE` 环境变量拼路径；`ctypes.windll` + `CryptProtectData`/`CryptUnprotectData` 加密 API Key。
   - **问题**：Linux 服务器上 `ctypes.windll` 直接抛异常；API Key 无法解密。
   - **改法**：引入 `SecretStore` 抽象——Windows 用 DPAPI，非 Windows 用 `keyring` 或环境变量注入；路径改用 `platformdirs`（`user_config_dir` / `user_data_dir`），不依赖 Windows 专属环境变量。

2. **`core/pdf_exporter.py` — Word COM + Windows 专属路径**
   - 行 19-21 硬编码 `C:\Program Files\LibreOffice\...`；行 38-40、86-98 用 `win32com` 调 Word COM。
   - **问题**：Linux 服务器无 Word COM，Windows 候选路径全失效。
   - **改法**：`find_libreoffice()` 以 `shutil.which("soffice")` 为第一路径（Linux 通用）；`win32com` 分支保留为 Windows 桌面端备选，服务端只用 LibreOffice 无头。**服务端 Docker 必须装 LibreOffice**。

3. **`core/chart.py` — 中文字体候选为 Windows 字体**
   - 行 18：`Microsoft YaHei / SimHei / SimSun / Arial Unicode MS`。
   - **问题**：Linux 无这些字体，图表中文会豆腐块。
   - **改法**：候选列表加 `Noto Sans CJK SC`，并做运行时字体探测（`font_manager.findfont` 循环），Docker 装 `fonts-noto-cjk`。

### 中低风险（需重构，不阻塞 API 化）

4. **`report_service.py` 函数签名接收可变 `state`（AppState）对象**
   - 如 `materials_text(state)`、`resolve_context(state, ...)`、`generate_single(state, ...)`。
   - `AppState` 本身是纯 dataclass（无 Qt），不算硬阻塞；但 API 层需要**独立的请求/响应 DTO**，不应依赖 UI 共享状态对象。
   - **改法**：新增 `services/workflow.py`，提供显式参数版本（如 `generate(template: TemplateInfo, mappings, data, config, options) -> ReportResult`），UI 与 API 都调用它；`report_service` 里的 `state` 版保留给桌面端，或逐步迁移。

5. **AI 辅助编排只存在于 `mapping_page.py`（Qt 回调）**
   - `_ai_assist` 里「隐私确认 → 构造 fields → 调 AI → 写回 mapping」这段业务在 API 层无法复用。
   - **改法**：抽成 `services/ai_workflow.py: ai_assist(mappings, materials_text, fields, config) -> (mappings, applied, confirmed)`，UI 与 API 共用。

6. **预览/审查的报告文本抽取逻辑在 `preview_page.py` 里**
   - **改法**：抽成 `services/report_reader.py: extract_report_text(docx_path) -> str`（含表格拼接、图片数量提示），API 的预览与 AI 审查接口复用。

7. **`services/history.py` 记录本地绝对路径**
   - `record_task` 存 `template_path`/`output_path` 绝对路径。多用户服务端应存「任务 ID + 相对路径/对象 key」，否则路径泄漏且无法追溯。
   - **改法**：API 层提供独立的任务持久化（DB），桌面端保留 JSONL。

8. **`ui/pages/import_page.py` 用 `QFileDialog` 选文件**
   - 属正常 UI 行为，无需改动；API 层对应「multipart 文件上传」。

### 非问题（勿过度设计）

- `ui/theme.py`、`animations.py`、`window_effects.py`、`widgets.py`：纯 Qt 视觉层，与业务无关，直接丢弃即可。
- `core/errors.py` 异常层级完善，API 层映射成 HTTP 状态码即可（UserError→400，DocumentFormatError→422，ExternalDependencyError→503，其他→500）。

---

## 5. 分阶段改造路线图

### 阶段 0：解耦冲刺（立即做，1-2 周，纯重构，风险低）
- [ ] 抽取 `services/report_reader.py: extract_report_text()`，替换 `preview_page` 内文本抽取逻辑。
- [ ] 抽取 `services/ai_workflow.py: ai_assist()`，替换 `mapping_page._ai_assist` 的业务部分。
- [ ] 抽取 `services/export_workflow.py: export_pdf / export_batch_pdf`，替换 `generate_page` 内编排。
- [ ] 为上述抽取写单元测试（现有 `tests/` 已覆盖 core/service，沿用风格）。
- **验收**：UI 层零业务脚本，所有流程可被纯 Python 调用，`pytest` 全绿。

### 阶段 1：平台无关化（1-2 周）
- [ ] `config.py` 引入 `platformdirs` + `SecretStore` 抽象（Windows DPAPI / 其他平台 keyring 或 env）。
- [ ] `chart.py` 字体候选跨平台化 + 探测逻辑。
- [ ] `pdf_exporter.py` 改为 `which("soffice")` 优先，保留 Windows 备选。
- **验收**：核心包在 Linux + macOS 可 `pip install` 并跑通「解析→映射→生成→PDF」全流程。

### 阶段 2：后端 API 化（2-4 周）
- [ ] 新增 `src/formora_api`（或独立仓库）：FastAPI + Pydantic，复用 core/services。
- [ ] 路由：`/templates/parse`、`/data/read`、`/mappings/auto`、`/ai/extract`、`/ai/review`、`/reports/generate`、`/reports/batch`、`/reports/{id}/pdf`、`/history`。
- [ ] 文件存储抽象（本地目录 → S3/OSS 可替换）+ 任务 DB（SQLite 起步，后续 Postgres）。
- [ ] 鉴权：API Key / JWT；AI 密钥服务端保管。
- [ ] Dockerfile：`python:3.12-slim` + `libreoffice` + `fonts-noto-cjk` + 应用。
- **验收**：`curl` 可完整跑通「上传模板→上传数据→生成→下载 docx/pdf」。

### 阶段 3：微信小程序前端（3-6 周）
- [ ] 用 **uni-app（Vue3）** 搭建项目，页面：任务列表 / 模板上传 / 数据上传 / 映射编辑（表格）/ 生成 / 预览 / 历史。
- [ ] `wx.chooseMessageFile` + `uni.uploadFile`；映射表组件复用现有交互心智。
- [ ] 预览：服务端渲染 PDF，`web-view` 展示；文本预览走 `extract_report_text`。
- [ ] AI 辅助：前端仅做「启用开关 + 隐私确认」，请求转发到后端 `/ai/*`，密钥不下发。
- **验收**：小程序端完成「导入→映射→生成→下载/预览」闭环。

### 阶段 4：可选移动端 App（3-6 周）
- [ ] 用 uni-app 编译 Android APK / iOS App（同一套代码），或 WebView 壳（TWA/Capacitor）指向 H5。
- [ ] 若坚持端侧离线：仅评估 Android + Chaquopy 内嵌「模板渲染子集」（需裁剪 pandas/pdfplumber），iOS 不做。
- **验收**：App 可上传文件、映射、生成、下载。

---

## 6. 附：依赖体积与服务端部署提示

- 服务端 Python 依赖：`python-docx docxtpl openpyxl pandas pdfplumber matplotlib Pillow` + `fastapi uvicorn python-multipart`。约几百 MB（含 pandas/matplotlib），Docker 镜像需分层缓存。
- `pdfplumber` 依赖 `pdfminer.six` + `cryptography`，Linux 有预编译轮子，问题不大。
- 若服务端不想装 `matplotlib`，可把图表生成改为前端/服务端 SVG 方案（`chart.py` 是独立模块，替换成本低）；但保留 matplotlib 最简单。