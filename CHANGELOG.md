# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 与语义化版本（SemVer）。

## [2.11.0] - 2026-10-25

### Fixed（100-Agent 大规模评审后的手动接管修复）

- **API 磁盘清理**：`_prune_expired` 清理内存记录时同步删除对应磁盘文件，修复长期运行磁盘无限增长
- **外部依赖错误留痕**：`_handle_error` 对 `ExternalDependencyError` 记录 `logger.warning`
- **异常增加 `user_message` 属性**：`FormoraError` 提供 `user_message`（默认等于 str），供 UI 统一展示友好消息，避免泄露内部路径
- **配置损坏备份与健壮性**：`config._load` 解析失败或非 dict 时先备份 `config.json.bak` 再回退默认，并记录日志
- **历史记录轮转**：`history` 超过 2000 条或 5MB 自动轮转，损坏行记录日志
- **主题对比度**：浅色提示文字 `_L_TEXT_HINT` 从 `#7a8a9c` 加深到 `#5f6f82`（对比度 ≥4.5:1，满足可访问性）
- **Card.layout 改名**：`widgets.Card` 的 `self.layout` → `self._layout`，避免遮蔽 `QWidget.layout()`
- **生成页残留输出**：`generate_page.refresh` 在无输出时清空上一次的输出路径与日志，避免界面与行为矛盾

### 兼容性

- **289 项自动化测试通过**。

## [2.10.0] - 2026-10-25

### Fixed（第三轮多 Agent 评审：图表 / AI UX / 跨平台测试）

- **图表 x 轴类型检测**：x 值若全部为数值则保留数值轴（`_normalize_x_values`），修复不等间隔时间点被等距扭曲、时间序列失真的问题；非数值仍转字符串作类别轴
- **AI 测试连接不再阻塞 UI**：设置页「测试连接」改用后台 QThread 执行（原同步调用最长冻结 20 秒），期间按钮显示「测试中…」并禁用
- **DPAPI 测试跨平台兼容**：`test_config_defaults_and_roundtrip` 加 `skipif(非 Windows)`，为 Linux/macOS CI 铺路

### 兼容性

- **289 项自动化测试通过**。
- 行为变化：设置页「测试连接」改为异步；图表数值 x 轴不再强制转字符串。

## [2.9.0] - 2026-10-25

### Fixed（第二批 10 个多 Agent 评审：数据导入 / 模板解析 / AI 集成高危项）

**📊 数据导入兼容性**
- **分隔符自动嗅探**：CSV 用 `sep=None` 让 pandas 识别逗号/分号/制表符分隔，修复分号/tab 文件被读成单列的问题
- **新增 .tsv 支持**：`.tsv`（tab 分隔）现在可正常导入
- **日期/数值序列化**：Excel 日期列（Timestamp）、numpy 标量统一转成 Python 原生可序列化类型，修复 API/AI 场景 JSON 序列化崩溃
- **列名冲突处理**：strip 后重复的列名追加 `_2/_3` 序号，不再静默覆盖丢数据；空表头列名改为「未命名列」
- **空文件友好提示**：空 CSV 明确提示「文件内容为空」，不再误报"文件可能损坏"

**📄 模板解析**
- **CORE_FIELDS「结论」恒缺失修复**：章节检测把「结论/总结/心得体会」归一为 canonical「实验结论」，`missing_core_fields` 改用双向别名判断——模板已有实验结论不再误报缺「结论」

**🤖 AI 集成**
- **JSON 宽松解析**：新增 `_parse_model_json`，剥离 Markdown 代码围栏、提取首个 JSON 对象/数组，兼容 `reasoning_content` 为空的模型；模型返回数组时自动包装为 `{"fields": [...]}`

### 兼容性

- **289 项自动化测试通过**（新增 5 项数据导入兼容性回归测试）。
- 行为变化：CSV 分隔符自动嗅探、重复列名自动加序号（`项目` → `项目_2`）。

## [2.8.0] - 2026-10-25

### Fixed（API 层安全与健壮性——20 个多 Agent 全方位评审）

**🔴 安全加固（API 层）**
- **可选 API Key 鉴权**：配置 `FORMORA_API_KEY` 后，所有受保护端点要求 `Authorization: Bearer <token>`；`/api/health` 保持公开供探活
- **上传大小限制**：`_save_upload` 流式计数，超限返回 413，防止磁盘/内存耗尽 DoS
- **文件 TTL + 容量清理**：`_FILES`/`_TASKS` 带时间戳，过期自动淘汰；启动时清理工作目录残留，杜绝无限增长
- **错误消息脱敏**：不再回显内部绝对路径，按 `FormoraError` 子类映射状态码（UserError→400 / DocumentFormatError→422 / ExternalDependencyError→503 / 其他→500），完整异常只记服务端日志
- **DOCX 魔数校验**：上传模板校验 ZIP 签名（`PK`），防止任意文件伪装 `.docx`
- **图片上传端点**：新增 `POST /api/image/upload`（PNG/JPG/WebP/GIF），补齐小程序截图/图表占位符流程

**🐛 真实 bug 修复**
- **PDF 转换端点必然 404**：`convert_pdf` 原只查 `_FILES`（上传文件），生成结果在 `_TASKS`——现已改为用 `task_id` 查 `_TASKS`，生成后可立即转 PDF
- **下载 MIME/文件名错误**：`download_report` 按任务类型（docx/pdf）返回正确 Content-Type 与文件名，修复 `wx.openDocument` 打不开 PDF 的问题
- **列映射静默填空**：生成前校验 `source_column` 是否存在于数据列，缺失返回 400 并列出缺失列
- **空数据文件**：显式传数据文件但无行且含 column 映射时返回 400，不再静默生成空报告

**🧹 代码规范（全仓库 ruff 规范化）**
- `ruff check --fix` 清理 23 处（冗余 noqa、import 排序）
- `ruff format` 规范化 75 个文件（docstring 空行、长行折行、去 BOM 等）
- 手动补充：`config.py` 深拷贝改用 `copy.deepcopy`、`ensure_dirs` 补返回注解、`report_reader` 补 docstring

### Added（API 测试大幅补强）
- 新增 PDF 转换（生成后转 PDF、MIME 校验）、自动映射、图片上传、空文件/伪 docx、404 族、列缺失、鉴权等 16 项测试

### 兼容性

- 桌面端功能完全不变；**284 项自动化测试通过**（新增 16 项 API 测试）。
- API 层行为变化：`POST /api/report/pdf` 请求体由 `docx_file_id` 改为 `task_id`（配合 bug 修复）。

## [2.7.0] - 2026-10-25

### Added（阶段2：FastAPI 后端 API 层——为微信小程序/App 铺路）

- **REST API 服务**：新增 `src/formora/api.py`（FastAPI），复用 core 层纯 Python 引擎（模板解析/数据读取/自动映射/报告生成/PDF 转换/文本抽取），不依赖 Qt，与桌面端共享同一套逻辑
- **端点**：
  - `GET /api/health` 健康检查（返回版本）
  - `POST /api/template/parse` 上传 DOCX 模板 → 占位符/章节/图片位
  - `POST /api/data/read` 上传数据文件 → 列/预览行/行数
  - `POST /api/mapping/auto` 自动映射
  - `POST /api/report/generate` 生成 DOCX → task_id + 下载 URL
  - `GET /api/report/{task_id}/download` 下载报告
  - `POST /api/report/pdf` DOCX → PDF
  - `POST /api/report/{task_id}/text` 抽取报告文本（供 AI 审查/预览）
- **启动入口**：`api_server.py`（`python api_server.py --port 8000`），自带交互文档 `/docs`
- **依赖**：新增 `requirements-api.txt`（fastapi/uvicorn/python-multipart，可选，不污染桌面端核心）
- **测试**：新增 `tests/test_api.py`（TestClient，9 项：健康/模板/数据/生成/下载/文本/边界）

### 兼容性

- 桌面端功能完全不变；**268 项自动化测试通过**（新增 9 项 API 测试）。
- API 已实测端到端：上传模板+数据 → 生成 → 下载（35765 字节合法 DOCX）→ 文本抽取全通。

## [2.6.0] - 2026-10-25

### Changed（阶段1跨平台化：让核心流程在 macOS/Linux 可跑通）

- **LibreOffice 候选路径补全**：`pdf_exporter` 在原有 Windows 路径基础上，新增 macOS（`/Applications/LibreOffice.app/...`）与 Linux（`/usr/bin/soffice`、`/usr/lib/libreoffice/...`、`/snap/bin/soffice`）候选，服务端/Linux 桌面可直接无头转 PDF
- **平台目录规范**：`config.py` 在非 Windows 遵循 XDG（`~/.config/FormoraReport`），文档目录自动探测真实 Documents/文档目录；Windows 行为完全不变
- **无边框边缘缩放的平台守卫**：`main_window.nativeEvent` 增加 `_IS_WINDOWS` 前置判断，非 Windows 直接走系统默认，不再每次 try-import

### 兼容性

- Windows 行为不变；**259 项自动化测试通过**（新增跨平台候选/目录/守卫，未改既有断言）。

## [2.5.0] - 2026-10-25

### Added（第五轮作者视角多 Agent 评审：代码规范 / 跨平台 / 可移植性 / 测试质量）

- **服务层解耦**：新增 `services/report_reader.py`（报告文本抽取）、`services/ai_workflow.py`（AI 结果落地映射），核心业务逻辑从 Qt 页面抽成纯函数，为后续后端 API / 移动端复用铺路
- **批量导出复用**：`report_service.batch_export_pdf()` 把批量转 PDF 编排上提服务层，UI 只负责调用与弹窗
- **测试基础设施**：新增 `tests/conftest.py`（公共 fixture）、`pytest.ini`、`.coveragerc`、`requirements-dev.txt`（pytest-cov/ruff/mypy）、`tests/README.md`
- **跨平台文档**：新增 `docs/cross-platform-migration.md`，给出 FastAPI + uni-app（微信小程序/APK/iOS）分阶段改造路线图

### Fixed（跨平台与可移植性）

- **非 Windows 无法启动**：`config.py` 顶层 `import ctypes.wintypes` 改为函数内延迟导入 + `_IS_WINDOWS` 判断，macOS/Linux 不再 import 即崩
- **打开输出文件夹跨平台崩溃**：`os.startfile`/`explorer` 改为 `QDesktopServices.openUrl`，非 Windows 平台不再抛 `FileNotFoundError`
- **中文字体候选补 Linux**：`chart.py` 字体候选追加 `Noto Sans CJK SC`/`WenQuanYi Zen Hei`，Linux 服务端图表不再豆腐块
- **版本号漂移**：`__version__` 由 2.1.0 修正为 2.5.0（与 CHANGELOG 对齐）

### Changed（代码规范）

- `CORE_FIELDS` 核心字段列表提取到 `models.py` 模块级常量，validator 复用，消除重复定义漂移风险
- `preview_page`/`mapping_page`/`generate_page` 的重复逻辑改为调用服务层纯函数
- CI 改用 `requirements-dev.txt` 并加入覆盖率检查（`--cov-fail-under=85`）

### 兼容性

- 核心 API 不变；**259 项自动化测试通过**（新增约 170 项：report_reader、ai_workflow、pdf_exporter、validator/模型补充、SSRF 安全、边界路径等），总覆盖率 91%。

## [2.4.0] - 2026-10-25

### Added（第四轮用户视角多 Agent 评审：提交体验 / 模板兼容 / 数据可视化）
- **数值格式化**：报告正文与表格循环中的数字更美观——`85.0` 显示为 `85`、`1e-05` 显示为 `0.00001`、日期去掉时间戳（`2026-10-25`）、百分比字符串保持原样
- **多系列折线图**：`generate_multi_line_chart` 支持多列数值各画一条线并显示图例（如通道A/通道B）
- **批量导出 PDF**：生成页新增「批量导出 PDF」按钮，把批次目录下所有 DOCX 串行转换为 PDF（复用 LibreOffice 互斥锁，单份失败不中断整体）
- **多占位符写法检测**：除 `{{字段}}` 外，`${字段}` 与 `【字段】` 也能被识别进映射表（适配不同老师的模板习惯）

### Fixed
- **表格内循环体字段误检**：`{% for %}` 循环出现在表格单元格内时，`{{ row['项目'] }}` 不再误进顶层待填字段（此前仅修正了正文段落，表格分支遗漏）
- **表格循环中 None 渲染为字面量 "None"**：`data_rows` 注入前统一格式化，None → 空串、数值/日期美化（正文占位符此前已修复，表格循环遗漏）

### Changed
- `mapper.resolve_values` 改用 `_format_value` 格式化列值
- `report_service` 注入 `data_rows` 前用 `_format_rows` 格式化整行
- `template_parser` 表格/页眉页脚扫描统一走 `_find_placeholders`（多写法）

### 兼容性
- 核心 API 不变；**89 项自动化测试通过**（新增 14 项：数值格式化、多系列图表、多占位符检测、data_rows 格式化）。

## [2.3.0] - 2026-10-25

### Fixed（第三轮用户视角多 Agent 评审：新手 / 工作流 / 打包 / AI UX）

**🔴 打包阻断（实测修复）**
- **发布版 exe 无法启动**：`FormoraReport.spec` 缺 `pathex=['src']` 且未显式收集应用包，导致 `No module named 'formora'`。已修复 spec（pathex + hiddenimports + 整包 formora 目录）、`main.py` 支持 frozen 路径；实测 exe 正常启动
- **openpyxl 未打包**：`.xlsx` 读取在发布版必挂，已 `collect_all('openpyxl')`
- **pywin32 未打包**：Word COM PDF 导出依赖缺失，已安装并随包
- **示例模板/数据未随包**：`tests/samples` 已作为资源打入 `_internal/samples`，`使用示例模板体验` 按钮在打包版可用
- **`FormoraReport.spec` 入库**：此前被 `.gitignore` 忽略，构建配方不再丢失；CI 改用 spec 打包
- 清理 `dist/` 下过期的 Setup-1.2.0 / Setup-2.0.0 安装包

**🔴 新手体验**
- **解析结果去黑话**：占位符/循环块/表头等代码风文案改为大白话，并提示「下一步：字段映射」
- **导入页占位符引导**：模板选择框下提示「用 {{实验名称}} 标记待填位置」
- **校验结果中文分级**：`[error]/[warning]/[info]` 改为「⚠️ 必须处理 / ⚠️ 建议补充 / ℹ️ 提示」
- **校验误报修复**：勾选「自动生成图表」后不再报「图片字段未选择图片」
- **首页副标题简化**：改为「导入模板 → 填写字段 → 一键生成」

**🟠 工作流正确性**
- **行切换刷新值列**：映射页切换数据行时，值列同步刷新（此前永远显示第 1 行）
- **循环体字段不再误识别**：`{{ row['项目'] }}` 这类循环引用不再进入顶层待填字段
- **单份/批量 data_rows 语义统一**：单份当前行也只注入当前行数据
- **百分比/文本数字列出图**：`85%`、`"12.5"` 等能正确识别为数值列
- **时间序列轴选择修复**：含「时间/日期/序号」的列优先作 x 轴，不再画反
- **页眉/页脚表格占位符扫描**：递归扫描页眉页脚内表格单元格

**🟠 AI 体验**
- **AI 审查线程化**：不再阻塞 UI 主线程（此前同步调用冻结 60s）
- **AI 审查结果不覆盖预览**：结果追加到预览文本，并保留报告内容
- **AI 填充覆盖确认**：会覆盖已手动映射字段时先弹确认框
- **「待确认」校验提醒**：AI 标记待确认的字段在校验时提示人工核对
- **状态栏同步 AI 配置**：启用 AI 后状态栏显示「AI 模式已启用 · 模型名」

**🟡 新增**
- `docs/WORKFLOW_ISSUES_EXPERT_REVIEW.md`：高频场景工作流问题清单

### 兼容性
- 核心 API 不变；**75 项自动化测试通过**（新增百分比出图、时间序列轴、循环字段识别、data_rows 统一等 6 项）。

## [2.2.0] - 2026-10-24

### Fixed（多 Agent 深度评审第二轮：批量语义 / None 输出 / 崩溃路径）
- **批量生成每份报告只含当前行数据**：此前批量生成的每份报告循环块都注入全部数据行，导致 N 份报告内容雷同；现在 `data_rows` 只注入当前行，真正实现「一个模板 + 多行数据 → 每行一份独立报告」
- **消灭图片字段输出 `None` 字面量**：图片字段未绑定图片或图表生成失败时，渲染上下文会残留 `None` 被 docxtpl 输出为字符串 "None"；现在未覆盖的图片字段会从上下文移除，占位符保持原样空白
- **批量/单份生成逻辑统一**：批量路径此前自建映射解析（漏掉 text 类型），现在复用与单份一致的 `mapper.resolve_values`，所有字段类型行为一致
- **占位符识别兼容更多命名**：`{{学生 姓名}}`、`{{chart-1}}`、`{{实验名称(一)}}` 等含空格/连字符/括号的占位符现在能正确识别
- **AI 响应结构校验**：模型返回非 JSON 对象时给出友好错误，不再抛 AttributeError 崩溃
- **图表异常不再静默**：自动图表生成失败会记录日志与任务日志，不再让用户误以为图表已插入
- **matplotlib Figure 泄漏修复**：`savefig` 失败也会 `finally` 关闭 Figure，避免内存累积
- **文件名净化**：任务名含 `:?*<>|` 等非法字符时自动过滤，不再触发 OSError
- **`.xls` 明确不支持并友好提示**：提示另存为 .xlsx，避免 xlrd 缺失导致的误导性错误
- **配置原子写**：`config.json` 先写临时文件再替换，崩溃/断电不再损坏配置
- **隐私文案修正**：明确说明密钥会作为认证凭据随请求发送到所配置 API（此前文案声称"不会上传"，与事实不符）
- **AI 审查独立隐私确认**：首次审查会提示报告全文将发送到所配置 API

### Changed
- 更新全部真实界面截图（浅色/深色共 12 张）与一键填充后的示例实验报告截图，均为真实运行产物
- 新增 `scripts/capture_real_screenshots.py`（真实窗口抓取截图）

### 兼容性
- 核心 API 不变；**69 项自动化测试通过**（新增批量语义、text 类型渲染测试）。

## [2.1.0] - 2026-10-24

### Added
- **后台线程化**：AI 辅助填写与批量生成移到后台 QThread，不再阻塞 UI 主线程；执行期间操作按钮自动禁用，完成后信号回主线程刷新
- **图片字段校验**：图片为空或路径不存在时在校验阶段明确报错（error 级），避免报告静默缺图
- **版本化输出**：单份输出文件名与批量输出目录追加时间戳，重复生成不再覆盖旧版，杜绝误覆盖丢失报告
- **SSRF 防护**：AI API base_url 强制 https（本地回环代理除外），拒绝内网/保留段地址（169.254.x / 10.x / 192.168.x / 172.16-31.x / 100.64+ / 元数据地址），防止密钥与素材被发往任意目标
- **全局异常钩子**：未捕获异常写日志并弹窗提示，避免静默退出
- **无边框窗口边缘缩放**：处理 WM_NCHITTEST，支持 8 向拖拽缩放窗口
- **减少动态效果接入**：读取 Windows「在 Windows 中显示动画」设置，开启后自动关闭应用内动画（可访问性）
- **窗口按钮无障碍**：最小化/最大化/关闭按钮增加 accessibleName 与 tooltip
- **LibreOffice 转换互斥锁**：并发 PDF 转换串行化，避免抢占 profile 互相失败
- **空输出目录兜底**：输出目录为空时回退到默认 Documents 目录，不再写入当前工作目录
- **版本号统一**：`src/formora/__init__.py` 从 0.1.0 修正为 2.1.0
- **pywin32 依赖**：requirements 增加 Windows 平台 Word COM PDF 导出所需依赖
- **竞品调研报告**：`docs/COMPETITIVE_ANALYSIS.md`

### Changed
- **字段映射不再丢失**：`mapping_page.refresh()` 只在首次进入且无映射时自动匹配；已编辑的映射、截图、AI 结果在切换页面后全部保留；新增「重新自动匹配」按钮供主动重置
- **单份/批量生成统一**：单份生成前也收集最新映射；校验同时检查映射级与上下文级问题
- **自动图表开关生效**：UI 复选框状态传入生成函数，取消勾选后不再强制生成图表
- **图表/图片字段智能识别**：去掉裸字「图」误判（地图/图纸/图标/图形等不再被当作图片）；图表占位符支持「实验结果图表」「曲线图」等包含匹配
- **AI 审查覆盖表格**：审查文本包含 Word 表格内容，不再漏掉表格中的关键数据

### Fixed
- 设置页「测试连接」因缺少 import 崩溃的问题
- 批量生成引用未定义变量 `output_dir` 导致的 NameError

### 兼容性
- 核心 API 不变；67 项自动化测试通过（含 7 项新增 2.1 测试）。

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
