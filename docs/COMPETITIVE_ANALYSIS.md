# FormoraReport 市场与竞品调研报告

> 调研方法：GitHub Search API（`search/repositories`，按 star 排序）+ 具体仓库 API + README 精读。
> 关键词：`lab report generator`、`experiment report`、`docx template fill`、`report generator python`、
> `docx template engine`、`word report generator`、`lab report automation`、`docxtpl`、`实验室报告生成` 等。
> 数据获取时间：2026-10-24（star 数为 GitHub API 实时值）。

---

## 1. FormoraReport 定位速览（对比基线）

- **形态**：Windows 桌面应用（PySide6 GUI），无 Python 环境也可运行（PyInstaller 打包 EXE）。
- **核心链路**：导入 DOCX 模板（`{{占位符}}`）→ 导入实验数据（CSV/XLSX/TXT/MD/PDF）→ 自动检测字段/章节/表格/图片 →
  字段映射（自动 + 手动）→ 生成 matplotlib 图表 → docxtpl 渲染 → 输出 Word / PDF（PDF 依赖本机 LibreOffice 或 Word）。
- **特色**：批量生成（一行数据一份报告）、缺失字段校验、预览/编辑/重新生成、玻璃拟态 UI、默认离线无 AI、可选
  OpenAI 兼容 API（BYOK，DPAPI 加密）。
- **技术栈**：Python 3.14、python-docx、docxtpl、openpyxl、pandas、pdfplumber、matplotlib、Pillow、PySide6。

---

## 2. 最相关竞品（4 组）与对比表

### 2.1 对比表

| 项目 | ⭐ Star | 定位 | 技术栈 | 许可 |
|---|---|---|---|---|
| **open-xml-templating/docxtemplater** | 3642 | 通用 DOCX/PPTX/XLSX 模板引擎（Node + 浏览器） | JavaScript | MIT 核心 + 商业 Pro（GitHub 标 NOASSERTION，双轨） |
| **elapouya/python-docx-template（docxtpl）** | 2726 | python-docx + Jinja2 模板引擎（FormoraReport 底层） | Python | LGPL-2.1 |
| **carboneio/carbone** | 2128 | 模板 + JSON 数据 → PDF/DOCX/XLSX 报告生成器（含文档转换、多语言） | JavaScript / Node | 开源社区版 + 商业 EE（GitHub 标 NOASSERTION） |
| **中文高校实验报告 AI 生成集群**（同赛道） | — | 实验报告自动生成（Skill / Agent / 桌面排版） | Python / Skill / Streamlit | 见下文各仓库 |
| └ S1xycat/lab-report-writer | 94 | 实验材料 → 完整实验报告的 Codex Skill（模板感知、证据驱动） | Python Skill | Apache-2.0 |
| └ L123121/Lab_Report_Skill | 30 | 计算机实验报告 Skill（代码/终端截图、DOCX 格式保护） | Python Skill | 未声明 |
| └ Adaoer/Nuist-engineering-lab-report | 29 | 中文工科实验报告 Codex Skill（强证据边界） | Python Skill | 未声明 |
| └ yydonk/report_agent | 17 | AI 实验报告 Agent（Streamlit 界面） | Python / Streamlit | 未声明 |
| └ KuruPeko/Nuist_repot_writer | 18 | 南信大实验报告一键生成排版软件（Windows 桌面） | Python / Edge / DSH | MIT |
| **otterview-labs/DocuGen** | 23 | 自托管文档工作台：知识库 + Word 模板变量填充 + AI 写作 | Python / Node / React | Apache-2.0 |

**其他备选/参考**（技术方案，非直接竞品）：

| 项目 | ⭐ Star | 定位 | 技术栈 | 许可 |
|---|---|---|---|---|
| python-openxml/python-docx | 5750 | Word 文档创建/修改底层库 | Python | MIT |
| mini-software/MiniWord | 831 | .NET Word 模板导出引擎（无 COM） | C# / .NET | Apache-2.0 |
| UNIT6-open/TemplateEngine.Docx | 419 | .NET 智能 docx 模板引擎 | C# / .NET | 未声明（NOASSERTION） |
| egonl/SharpDocx | 379 | .NET 轻量 Word 模板引擎 | C# / .NET | MIT |
| thombergs/docx-stamper | 221 | Java docx 模板引擎 | Java | MIT |
| mpastell/Pweave | 443 | Python 科学报告生成 / 文学编程 | Python | NOASSERTION |
| 111112200/LabReport-Insight | 41 | 实验报告语义查重/互查平台（差异化方向） | Python | MIT |
| thetahealth/mirobody | 1389 | 自托管健康数据引擎（医学检验报告） | Python | Apache-2.0 |

---

## 3. 各竞品功能/设计亮点提炼（2.1 升级参考）

### 3.1 docxtemplater（JS 生态标杆）
- **富模板语法**：插值、循环 `{#list}{/}`、条件、区块、图片替换、字段格式化；支持在 DOCX 内嵌 XML 微语法。
- **浏览器端渲染**：无需本机 Office，可直接在浏览器生成/预览文档，适合在线文档产品。
- **模块化 + 商业 Pro 插件**：表格数据绑定到模板字段、动态表格、超链接、Smart 字段、PDF 转换（LibreOffice）。
- **模板调试工具**：官方 Demo 与可视化调试，降低模板编写门槛。

### 3.2 docxtpl（FormoraReport 底层，LGPL-2.1）
- **完整 Jinja2 语法**：循环、条件、过滤器、`RichText`、子文档、页眉/页脚变量、`InlineImage` 动态插图。
- 这些能力 FormoraReport 底层已具备，但 **GUI 尚未充分暴露**（如"数据行循环生成表格行/多图"）。

### 3.3 Carbone（理念最接近的"数据→报告生成器"）
- **所见即所得模板**：直接在文档里写 `{d.companyName}`，模板即模板语言，数据以 JSON 注入。
- **数据格式化**：内置日期/数字 formatter，支持自定义 JS formatter。
- **内置文档转换**：LibreOffice 转 PDF/DOCX/XLSX，支持批量。
- **多语言模板**：一套模板 + 自动翻译文件 → 多语言报告（本地化）。
- **部署形态**：REST API + Docker，适合服务化/批量调用。

### 3.4 中文高校实验报告 AI 生成集群（最直接同赛道）
这是与 FormoraReport 用户场景最重叠的一类（高校理工科实验报告），虽形态多为 CLI/Skill/Web 而非桌面 GUI，但其**产品化思路**极具参考价值：

- **角色化材料文件夹范式（lab-report-writer）**：用固定子文件夹组织输入——
  `实验任务书 / 实验所需文件 / 实验报告模板 / 成品实验报告 / 实验相关课件 / 实验原始数据.md / 个人信息.md / 评分标准.md / 输出文件要求.md / 目标写作风格.md`。
  让"任务要求、模板、样例、真实数据、评分点、输出规格、文风"成为结构化输入，显著提升生成可控性。
- **证据边界原则（nuist-engineering-lab-report、Lab_Report_Skill）**：
  - 只写材料能支持的内容，**不编造数据**；缺失信息保守处理，不补造步骤/参数/仪器型号/个人信息。
  - **实验结果与结果分析严格分节**。
  - **图片就近放置**：截图/曲线/波形插到对应文字段落附近（图文同版），而非统一放文末。
- **自动生成截图（Lab_Report_Skill）**：代码截图（语法高亮）、终端截图（PTY/ConPTY 保真、ANSI 颜色、列宽）、
  批量截图（`report-shot.py`），失败时明确返回非零状态与 `partial/error` 标记；无法真实捕获时降级为真实计算结果渲染。
- **DOCX 格式保护（Lab_Report_Skill）**：对原模板做格式基线快照（`docx_format_guard.py`），
  生成后校验受保护部件/格式节点未被破坏、只改目标内容、**不覆盖原文件**，交付新 `.docx`。
- **评分标准映射（lab-report-writer）**：读取 `评分标准.md`，将报告章节对应到评分点，按分值规划详略。
- **公式处理（lab-report-writer）**：LaTeX 公式优先转 Word 原生公式（OMML），不稳定则渲染透明 PNG 插图；
  生成后检查文档中是否残留 `$$...$$`、`\frac` 等标记。
- **封面信息块 + 图注自动编号（report_agent）**：姓名/学号/课程/教师/日期自动填入；图片下方自动生成"图1/图2"。
- **生成参数个性化（report_agent）**：目标字数（1000–10000）、专业术语密度（低/中/高）、章节字数权重、
  文风配置——这些是"AI 写作可控性"的常见需求。
- **工作区/历史回放/一键安装自检（Nuist_repot_writer）**：任务、材料、日志、产物全保留可回放；一键安装/自检/卸载；
  界面显示 token 用量；DOCX 转 PDF 调用本机 Word。
- **模板变量提取与知识库来源（DocuGen）**：识别 `{{变量}}` 与 `【变量】`，跨 run 占位符替换、合并单元格、
  页眉/页脚（含首页/偶数页）保留；资料列表 + 原文并排、关键词高亮、来源跳转；**失败可见**（无命中明确报错，不返回示例内容）。

---

## 4. FormoraReport 缺失、但竞品普遍具备的能力

按"普遍性 × 对 2.1 的价值"排序：

1. **占位符识别单一**：目前主要面向 `{{}}`（docxtpl）占位符。竞品普遍支持更多风格（`【变量】`、`{d.field}`）、
   跨 run（被 Word 拆分到多个 run 的变量）识别、合并单元格与页眉/页脚/首页/偶数页变量。
   → **2.1 建议**：增加 `【变量】` 等兼容解析 + 跨 run 合并识别；映射页支持页眉/页脚/表格单元格。

2. **证据边界与"防编造"机制缺失**：竞品（尤其 AI 赛道）普遍强调"只写材料支持的内容、不编造数据、结果与分析分节、
   缺失信息保守占位"。FormoraReport 的 AI 模式目前是自由起草，缺少这些约束。
   → **2.1 建议**：为 AI Assist 增加证据边界提示词模板 + "结果/分析分节"、"缺失字段保守置空/标注"选项。

3. **自动截图/证据生成缺失**：竞品已能自动生成代码截图（语法高亮）、终端截图（ConPTY 保真）、批量截图，
   甚至本地复现运行后截图。FormoraReport 目前只能手动绑定已有截图。
   → **2.1 建议**：内置轻量"代码/终端截图"工具，或至少提供批量截图脚本入口。

4. **DOCX 格式保护/校验缺失**：竞品生成后会校验"原模板格式未被破坏、只改目标内容、不覆盖原文件"。
   → **2.1 建议**：生成前对模板做格式快照，生成后校验并提示差异；默认输出新文件（当前已是），
   增加"格式完整性校验"报告。

5. **内置文档转换与批量 PDF**：Carbone 内置 LibreOffice 转换，docxtemplater Pro 也提供 PDF。FormoraReport 的
   PDF 导出依赖用户本机 LibreOffice/Word，且缺少"批量转 PDF"。
   → **2.1 建议**：打包引导安装/自动探测 LibreOffice；批量生成时提供"全部转 PDF"。

6. **材料角色化输入范式**：竞品用"任务书/模板/样例/原始数据/评分标准/输出要求/文风"等角色化输入驱动生成，
   比单一"CSV+XLSX"数据更贴近实验报告场景。
   → **2.1 建议**：支持把"实验指导书、评分标准、输出要求"作为辅助材料导入，并让 AI 参考。

7. **本地化/多语言**：Carbone 支持一套模板多语言。FormoraReport 目前 UI 中英双语但报告模板无多语言机制。
   → 可作为远期方向。

8. **来源记录与失败可见**：DocuGen 提供来源高亮/跳转；report_agent 暴露中间 JSON 产物；Nuist 提供日志/token 用量/回放。
   → **2.1 建议**：AI 起草时记录"每个章节取材自哪些材料"，并在预览页展示；AI 调用失败时明确报错而非静默。

9. **公式处理**：AI 报告常含公式，竞品已做 LaTeX→OMML/PNG 与残留检查。
   → **2.1 建议**：AI 模式增加"公式优先转 Word 原生公式，失败渲染透明 PNG，并检查残留"。

10. **图注自动编号 / 封面信息块**：竞品普遍自动生成"图1/图2"编号与封面信息块。
    → **2.1 建议**：映射页增加"自动图注编号"选项；支持从数据/常量填充姓名、学号、日期等封面字段。

---

## 5. 给 2.1 的优先级建议

| 优先级 | 能力 | 依据 |
|---|---|---|
| P0 | 占位符兼容（`【变量】`、跨 run、页眉/页脚/单元格） | 模板兼容性是刚需，竞品普遍具备 |
| P0 | DOCX 格式保护/校验 | 用户信任关键；竞品普遍强调 |
| P0 | 证据边界 + 缺失字段保守处理（AI 模式） | 学术诚信场景刚需，直接提升可用性 |
| P1 | 内置/引导 LibreOffice 探测 + 批量转 PDF | 补齐 PDF 链路短板 |
| P1 | 材料角色化导入（任务书/评分标准/输出要求/文风） | 复用竞品被验证的输入范式 |
| P1 | 自动图注编号 + 封面信息块填充 | 低实现成本、高频需求 |
| P2 | 自动截图（代码/终端）、来源记录、公式处理、多语言 | 差异化与远期 |

---

## 附：数据来源与说明

- GitHub API：`https://api.github.com/search/repositories`（各关键词）、`https://api.github.com/repos/<owner>/repo`。
- README 精读来源：docxtemplater、python-docx-template、carbone、S1xycat/lab-report-writer、
  L123121/Lab_Report_Skill、Adaoer/Nuist-engineering-lab-report、yydonk/report_agent、
  KuruPeko/Nuist_repot_writer、otterview-labs/DocuGen。
- 未认证 API 有 60 次/小时限流，本次查询已做间隔与缓存。
- star/许可字段以查询时刻 GitHub 为准；`NOASSERTION` 表示 GitHub 未识别出标准开源许可，实际以仓库 LICENSE 文件为准。
- 本报告仅作调研参考，未修改任何 FormoraReport 代码。