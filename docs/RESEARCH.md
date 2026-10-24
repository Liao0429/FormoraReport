# FormoraReport 同类开源项目调研与对比报告（RESEARCH）

> 生成日期：2026-10-24

> 数据来源：GitHub Search API 多关键词检索（docx template / report generator / document generation / lab report 等 16 组查询，共收集 340 个去重候选）→ 人工筛选后对 32 个高相关仓库用 `/repos` 接口定向核实元数据（star、license、语言、最近提交）。
> 所有 star 数、许可证、最近提交时间均来自 GitHub API 实际返回；功能与架构描述基于仓库 README/description，未虚构。

---

## 一、调研项目总表（32 个已核实真实仓库）

| # | 项目 | 语言 | Star | License | 最近提交 | 定位 / 核心功能 |
|---|------|------|------|---------|---------|----------------|
| 1 | [getredash/redash](https://github.com/getredash/redash) | Python | 28849 | BSD-2-Clause | 2026-10-22 | 开源数据可视化/报表平台：连接多种数据源，编写查询，生成图表与仪表盘，支持定时刷新与分享，是「数据报告/仪表盘」方向的标杆。 |
| 2 | [Sayi/poi-tl](https://github.com/Sayi/poi-tl) | Java | 5172 | Apache-2.0 | 2026-10-13 | Java 的 Word 模板引擎（Apache POI）。在 Word 模板中写标签（文本/图片/表格/图表/条件/循环），用数据模型生成新文档，保真保留字体、颜色、布局；提供插件化自定义函数。 |
| 3 | [observablehq/framework](https://github.com/observablehq/framework) | TypeScript | 3670 | ISC | 2026-05-15 | Observable Framework：用 Markdown + 数据加载器构建数据应用、仪表盘与报告的静态站点生成器，适合发布交互式数据报告。 |
| 4 | [open-xml-templating/docxtemplater](https://github.com/open-xml-templating/docxtemplater) | JavaScript | 3642 | NOASSERTION | 2026-10-15 | JavaScript 的 DOCX/PPTX 模板生成库，用 {占位符} + 循环/条件/Angular 语法，模板可由非程序员编辑；Image/HTML/XLSX 等高级模块为付费商业模块。 |
| 5 | [elapouya/python-docx-template](https://github.com/elapouya/python-docx-template) | Python | 2726 | LGPL-2.1 | 2026-07-07 | docxtpl：把 DOCX 当 Jinja2 模板，用 {{占位符}}、{% for %} 渲染新文档，保留原格式/表格/图片/页眉页脚；本项目当前核心依赖之一。 |
| 6 | [xhtml2pdf/xhtml2pdf](https://github.com/xhtml2pdf/xhtml2pdf) | Python | 2396 | Apache-2.0 | 2026-10-21 | Python 库，基于 ReportLab 将 HTML/CSS 转为 PDF，适合把网页/富文本报告导出为 PDF。 |
| 7 | [carboneio/carbone](https://github.com/carboneio/carbone) | JavaScript | 2128 | NOASSERTION | 2026-04-07 | Carbone 报告生成平台：用模板（ODT/DOCX/XLSX/PPTX）+ JSON 数据生成 PDF/DOCX/XLSX/CSV 等；开源版可嵌入 Node.js，商用高级功能需许可，提供 Docker/REST。 |
| 8 | [Jaspersoft/jasperreports](https://github.com/Jaspersoft/jasperreports) | Java | 1372 | LGPL-3.0 | 2026-10-14 | JasperReports 免费 Java 报表库：数据（SQL/JRXML）→ 可交互的 PDF/HTML/Excel/Word 报表，是业界最经典的「数据到报告」引擎之一。 |
| 9 | [kac89/vulnrepo](https://github.com/kac89/vulnrepo) | TypeScript | 583 | Apache-2.0 | 2026-10-07 | VULNREPO：免费漏洞报告生成器与仓库，端到端加密，支持生成与存档渗透测试/安全审计报告。 |
| 10 | [mpastell/Pweave](https://github.com/mpastell/Pweave) | Python | 443 | NOASSERTION | 2023-11-03 | Pweave：Python 科学报告生成器与文学编程工具，在文档中嵌入 Python/R 代码块并渲染成 PDF/HTML/ReST 报告。 |
| 11 | [smartinmedia/Net-Core-DocX-HTML-To-PDF-Converter](https://github.com/smartinmedia/Net-Core-DocX-HTML-To-PDF-Converter) | C# | 345 | MIT | 2023-09-12 | .NET Core 库：基于 Word DOCX 或 HTML 模板创建自定义报告并导出 PDF，适合服务端报告生成。 |
| 12 | [ferdinandobons/brand-docs](https://github.com/ferdinandobons/brand-docs) | Python | 281 | MIT | 2026-07-10 | BrandDocs：给 Claude Code/Codex 等 Agent 使用的技能包，从现有 Word/PPT/Excel 模板提取「品牌档案」，再按模板保真生成同格式 on-brand 文档。 |
| 13 | [dynamicreports/dynamicreports](https://github.com/dynamicreports/dynamicreports) | Java | 246 | LGPL-3.0 | 2026-06-19 | Java 动态报告库：以编程方式在运行时设计报表（列、分组、图表、样式），无需预定义模板。 |
| 14 | [Amberg/DocxTemplater](https://github.com/Amberg/DocxTemplater) | C# | 139 | MIT | 2026-10-20 | C# 的 DOCX 模板生成库：支持占位符、循环、表格、图表、Markdown/HTML、图片嵌入，面向 .NET 文档自动化。 |
| 15 | [LogicPaper/LogicPaper](https://github.com/LogicPaper/LogicPaper) | Python | 127 | NOASSERTION | 2026-06-30 | Python 批量文档生成引擎：Excel/JSON 数据 + Jinja2 策略 + DOCX/PPTX/MD 模板，LibreOffice Headless 转 PDF；FastAPI + Redis + 异步批量。 |
| 16 | [mkdreams/MDword](https://github.com/mkdreams/MDword) | PHP | 53 | NOASSERTION | 2026-01-22 | 纯 PHP 的 Word 文档模板库：Office Word 动态数据绑定，用模板生成报告 DOCX。 |
| 17 | [Probesys/lotemplate](https://github.com/Probesys/lotemplate) | Rich Text Format | 50 | AGPL-3.0 | 2026-04-17 | LOTemplate：程序化文档生成器，从 ODT/DOCX 模板生成文档，由 Python 生成 ODF/DOCX/PDF。 |
| 18 | [Zen-Reportz/zen_knit](https://github.com/Zen-Reportz/zen_knit) | Python | 37 | MIT | 2022-04-30 | Zen-Knit：数据分析师的正式（PDF）与非正式（HTML）报告生成器，把数据分析流程输出为可读报告。 |
| 19 | [yuanfangdeshang/2025-WeChat-Annual-Chat-Report-Generator](https://github.com/yuanfangdeshang/2025-WeChat-Annual-Chat-Report-Generator) | Python | 28 | MIT | 2026-01-22 | 微信年度聊天报告生成器：读取微信聊天记录，生成带数据可视化、好友分析、年度称号的精美报告（Python）。 |
| 20 | [otterview-labs/DocuGen](https://github.com/otterview-labs/DocuGen) | Python | 23 | Apache-2.0 | 2026-10-23 | DocuGen：自托管知识库与文档生成工作台，可检索素材、填充 Word 模板、生成 DOCX（FastAPI + Vue）。 |
| 21 | [pnlng/crisscross](https://github.com/pnlng/crisscross) | Python | 21 | BSD-3-Clause | 2019-12-20 | crisscross：以 Markdown 为中心的模板引擎，用于批量离线文档生成（BSD-3）。 |
| 22 | [Papyrine/Parchment](https://github.com/Papyrine/Parchment) | C# | 18 | MIT | 2026-10-20 | Parchment：C# 的 Word (.docx) 文档生成库，支持样式化渲染（MIT）。 |
| 23 | [javadev/jasper-xml-to-pdf-generator](https://github.com/javadev/jasper-xml-to-pdf-generator) | Java | 17 | Apache-2.0 | 2026-09-28 | 命令行工具：用 JRXML 报表模板生成 DOCX/HTML/ODT/PDF/PNG/PPTX/RTF/XLS/XLSX 等多种格式文档。 |
| 24 | [WebVella/WebVella.DocumentTemplates](https://github.com/WebVella/WebVella.DocumentTemplates) | C# | 17 | NOASSERTION | 2026-02-11 | C# 文档模板生成库：为 Excel、Word、Email、HTML 与纯文本生成文档模板并渲染（MIT 兼容/自托管）。 |
| 25 | [Puershiweilke/Excel-to-Docx-Auto-Filler-Tool](https://github.com/Puershiweilke/Excel-to-Docx-Auto-Filler-Tool) | Python | 15 | 未声明 | 2024-09-20 | Python 工具：把 Excel 数据自动填入 Word 模板，批量生成格式化文档；支持自定义模板、图片链接插入、文件名模板、Tkinter GUI。 |
| 26 | [atverma/WordDocGenerator](https://github.com/atverma/WordDocGenerator) | C# | 13 | MIT | 2018-12-03 | WordDocumentGenerator：C# 工具，从模板生成 Word 文档（MIT）。 |
| 27 | [awhipp/docx-template-generator](https://github.com/awhipp/docx-template-generator) | Python | 6 | MIT | 2019-06-06 | Python 小工具：读一个 Word 模板与输入数据，批量生成多个文档（MIT）。 |
| 28 | [TechIT-Community/Report-Generator](https://github.com/TechIT-Community/Report-Generator) | Python | 5 | MIT | 2025-12-27 | 桌面应用（Python/CustomTkinter）：向导式输入项目数据，调用 Word COM 自动填充模板、插入图片、处理页眉页脚/目录，生成专业 Word 报告。 |
| 29 | [Chaitanya5068/Auto_report](https://github.com/Chaitanya5068/Auto_report) | Python | 5 | MIT | 2025-07-16 | 终端自动化报告生成器：读取 CSV/Excel/PDF/DOCX，自动摘要 + matplotlib 图表 + fpdf2 输出 PDF 报告（MIT）。 |
| 30 | [Fldicoahkiin/lab-report-autopilot](https://github.com/Fldicoahkiin/lab-report-autopilot) | Python | 1 | MIT | 2026-07-25 | 大学计算机实验报告自动填写 Agent Skill：由 Agent 实际操作实验、截图，再按学校 DOCX 模板逐页渲染检查后交付最终报告（MIT，Windows 优先）。 |
| 31 | [renmadz/project240](https://github.com/renmadz/project240) | TypeScript | 0 | 未声明 | 2026-08-01 | 学校 OJT 周报生成器（Next.js）：以学校 DOCX 为不可变模板，只重写 word/document.xml 实现字节级保真，克隆模板自带格式段落，输出 DOCX/PDF。 |
| 32 | [mmmylnikov/doc-fill-master](https://github.com/mmmylnikov/doc-fill-master) | Python | 0 | MIT | 2025-04-07 | 桌面应用（Python/GUI）：用 CSV 或界面字段填充 .docx 模板占位符并导出 PDF；多语言（MIT）。 |

---

## 二、对比分析

### 2.1 按方向分类

| 方向 | 代表项目 | 说明 |
|------|---------|------|
| **A. 模板占位符填充**（与本项目最接近） | docxtpl、docxtemplater、poi-tl、MDword、Amberg/DocxTemplater、Excel-to-Docx-Auto-Filler、project240、doc-fill-master 等 14 个 | 以 Word/DOCX 模板为壳，把数据填入占位符，保真输出。是 FormoraReport 的直接对标。 |
| **B. 数据→多格式报告引擎** | Carbone、LogicPaper、JasperReports、dynamicreports、Pweave、Auto_report | 数据（JSON/Excel/SQL）驱动生成 PDF/Word/Excel 报告，多为服务端/批量。 |
| **C. 桌面 GUI 报告工具** | TechIT Report-Generator、Excel-to-Docx、doc-fill-master、lab-report-autopilot | 面向普通用户，GUI 操作，本地处理——与 FormoraReport 形态最像。 |
| **D. 可视化 / 仪表盘报告** | redash、Observable Framework、WeChat Annual Report、vulnrepo | 面向数据展示与分享，重图表交互，轻文档保真。 |
| **E. 文档导出 / 转换** | xhtml2pdf、Net-Core-DocX-HTML-To-PDF-Converter | 把 HTML/模板转 PDF，解决「导出」链路。 |
| **F. AI / Agent 文档生成** | brand-docs、lab-report-autopilot、DocuGen | 用 LLM 理解素材并保真生成，是 AI 模式可借鉴的方向。 |

### 2.2 关键能力矩阵（最相关 12 项）

| 项目 | 模板解析 | 占位符 | 循环/条件 | 图片插入 | 图表 | 批量 | 导出PDF | 本地/离线 | GUI | AI可选 | License风险 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|------|
| **FormoraReport** | ✅ | ✅ | 基础 | ✅ | ✅(matplotlib) | ✅ | 依赖LO/Word | ✅ | ✅ PySide6 | ✅(可选) | MIT，默认无AI |
| docxtemplater | ✅ | ✅ | ✅ | 付费模块 | 付费 | ✅ | 模块 | ✅ | — | — | 核心MIT，高级模块付费 |
| docxtpl | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | — | — | LGPL-2.1 |
| poi-tl | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 插件 | ✅ | — | — | Apache-2.0 |
| Carbone | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | 可自托管 | — | — | 开源版+商用版 |
| LogicPaper | ✅ | ✅(Jinja2) | ✅ | ✅ | — | ✅异步 | ✅LibreOffice | 服务端 | Web | — | CC BY-NC(非商业) |
| Excel-to-Docx | ✅ | ✅ | — | ✅(URL) | — | ✅ | — | ✅ | ✅Tkinter | — | 未声明 |
| project240 | ✅(XML级保真) | ✅ | ✅ | ✅ | — | ✅ | ✅Gotenberg | Web | Web | — | 未声明 |
| lab-report-autopilot | ✅ | ✅ | — | ✅(截图) | — | ✅ | ✅ | ✅ | Agent | ✅ | MIT |
| TechIT Report-Generator | ✅ | ✅ | — | ✅ | — | — | ✅Word COM | ✅ | ✅CustomTkinter | — | MIT |
| brand-docs | ✅(品牌档案) | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | CLI/Agent | ✅ | MIT |
| redash | —(非文档) | — | — | — | ✅仪表盘 | ✅定时 | — | 自托管 | Web | — | BSD-2 |

### 2.3 关键结论

- **最接近的赛道是「模板填充」而非「报表引擎」**：FormoraReport 的差异化在于「原模板保真 + 图片/图表注入 + 批量 + 桌面本地 + 可选 AI」，这与 docxtpl/poi-tl/project240 更一致，而与 redash/JasperReports 这类数据报表平台定位不同。

- **PDF 导出的主流做法是外部转换器**：几乎都依赖 LibreOffice Headless（LogicPaper）、Gotenberg（project240）或 Word COM（TechIT），说明 FormoraReport 用 LibreOffice/Word 导出 PDF 的选型正确。

- **许可差异明显**：MIT/Apache-2.0 最友好；LGPL 可商用但需声明；CC BY-NC 与付费模块不可作为默认依赖。FormoraReport 以 MIT 自许可、默认无 AI，是安全的组合。

- **成熟项目都强调「保真与健壮」**：docxtemplater 靠多年修复与高质量测试立足；project240 靠只重写 document.xml 的字节级保真；poi-tl 靠插件化与条件/循环语法。这三点正是 FormoraReport 下一步最该补强的。


---

## 三、重点分析：5 个最相似项目的设计思路

按「与 FormoraReport 定位重合度」选取：同一大学实验报告自动填写（lab-report-autopilot）、Excel→Word 批量填充（Excel-to-Docx）、Excel→多格式批量引擎（LogicPaper）、成熟 Word 模板引擎（poi-tl）、行业标杆模板平台（docxtemplater）。

### 3.1 lab-report-autopilot（大学实验报告自动填写）

- 仓库：https://github.com/Fldicoahkiin/lab-report-autopilot
- 技术栈：Python + Agent Skills（Claude Code/Codex/Cursor 等）；实际执行命令/软件，截图来自真实操作；DOCX 用 python-docx 类库填写。
- 设计思路：把作业要求/学校模板/用户信息交给 Agent；Agent 先识别课程与格式，再选可用环境（Windows 优先），实际运行实验并截图，将原始结果填入学校模板，最后逐页渲染检查才交付 DOCX。强调「不补写未提供信息、不猜身份」。
- 可借鉴之处：①「逐页渲染检查」作为交付前必做校验——FormoraReport 可在生成后用 LibreOffice 转 PDF 再检查页数与占位符残留；②「缺失信息集中询问/明确提示」对应 FormoraReport 的字段校验；③「截图来自真实操作」与本项目「插入真实截图素材」理念一致，可强化「操作截图→对应章节自动放置」。

### 3.2 Excel-to-Docx-Auto-Filler-Tool（Excel→Word 批量填充）

- 仓库：https://github.com/Puershiweilke/Excel-to-Docx-Auto-Filler-Tool
- 技术栈：Python + pandas + python-docx + openpyxl + requests + Tkinter GUI。
- 设计思路：以 Excel 数据行为单位，按 {{key}} 占位符把列值填入 Word 模板，批量生成多个 docx；支持图片链接自动下载插入、文件名模板（用数据列动态命名）、Tkinter 图形界面。
- 可借鉴之处：①「文件名模板」：从数据列生成输出文件名（学号_姓名_实验N.docx）——FormoraReport 批量生成时可加同类动态命名；②「图片链接/路径列自动插入指定位置」正是本项目「绑定截图到占位符」的现成对应；③Tkinter 简化 GUI 表明「够用即可」，FormoraReport 用 PySide6 提供更现代 UI，属合理升级。

### 3.3 LogicPaper（Excel→PDF/Word/PPT 批量引擎）

- 仓库：https://github.com/LogicPaper/LogicPaper
- 技术栈：Python 3.11 + FastAPI + Redis + Jinja2 + LibreOffice Headless + Docker；Hexagonal Architecture。
- 设计思路：结构化数据（Excel/JSON）与 Office 模板（DOCX/PPTX）或文本模板（MD/TXT）结合，用 Jinja2 策略系统渲染；异步批量处理大数据集防超时；LibreOffice 无头转 PDF；提供 API（X-API-Key）供 ERP/CRM 集成；Redis 做任务状态持久化。
- 可借鉴之处：①「异步批量 + 任务状态跟踪」：FormoraReport 批量生成可加入任务队列、进度条、失败重试；②「LibreOffice Headless 转 PDF」验证了本项目 PDF 导出路线；③「模板语法策略系统」可用 Jinja2（docxtpl 已内嵌）做条件/循环/日期/货币过滤器，增强模板表达能力；④企业级 API/无头模式可作未来 CLI/自动化扩展。

### 3.4 poi-tl（Java Word 模板引擎，成熟参照）

- 仓库：https://github.com/Sayi/poi-tl
- 技术栈：Java 1.8+ + Apache POI；逻辑无关模板引擎 + 插件体系。
- 设计思路：模板里只写标签（text/picture/table/chart/numbering/if/foreach），由数据模型渲染；标签可渲染为文本、图片、表格、图表（柱状/折线/饼图等），支持条件显隐、集合循环；插件化自定义函数可在文档任意位置执行。强调「模板不掺逻辑，风格完全保留」。
- 可借鉴之处：①「标签类型化 + 插件化」：FormoraReport 的占位符可扩展为 {{图片}}/{{图表}}/{{表格行}} 等类型，并把解析/渲染做成插件；②「条件与循环」让一个模板覆盖多组数据（表格行随数据重复）——批量实验报告刚需；③「逻辑无关」原则与 docxtemplater 一致，说明模板应保持纯净。

### 3.5 docxtemplater（行业标杆模板平台）

- 仓库：https://github.com/open-xml-templating/docxtemplater
- 技术栈：JavaScript/TypeScript；Node.js + 浏览器；模块化（核心免费 + Image/HTML/XLSX 等付费模块）。
- 设计思路：用 {占位符}、{#loop}、条件（Angular 表达式）在 DOCX/PPTX 模板中描述数据位置；模板可由非程序员编辑；以大量回归测试保证健壮；提供浏览器端与 Node 端。
- 可借鉴之处：①「模板可由非程序员编辑」：FormoraReport 的「{{字段名}}」语法已具备此优点，应继续降低模板制作门槛（可视化映射页）；②「循环表生成多列」：对本项目批量报告是强需求；③「高质量测试是立足之本」：FormoraReport 应针对页眉页脚/表格/图片锚点建立回归测试套件；④高级能力商业化（付费模块）对本项目不适用，保持全开源 MIT 是差异化卖点。

---

## 四、对 FormoraReport 的改进建议（具体可执行）

- **S1 模板锚点保真校验**：仿 project240「锚点缺失即报错」：生成前除校验缺失字段外，还校验模板中的页眉/页脚/表格/图片锚点是否存在；生成后用 LibreOffice/Word 无头转 PDF 抽查「占位符残留」「页码/页数」并提示，避免静默产出漂移文档。
- **S2 支持条件与循环语法**：仿 poi-tl / docxtemplater：在现有 {{字段}} 基础上扩展 {{#each 行数据}}...{{/each}}（表格行循环）与 {{#if 条件}} 区块，让一个模板能覆盖多组实验数据；解析层保持 docxtpl 兼容以复用其成熟实现。
- **S3 动态文件名与图片列**：仿 Excel-to-Docx：批量生成时支持「文件名模板」（如 {{学号}}_{{姓名}}_实验{{序号}}.docx）与「图片列自动绑定到指定占位符」，减少手工映射。
- **S4 批量任务队列与进度/重试**：仿 LogicPaper：把批量生成改为任务队列（线程池 + 状态文件/DB），UI 显示进度与失败项，支持单条重试；为未来 CLI/API 模式预留无头入口。
- **S5 无 AI 智能摘要**：仿 Auto_report：在无 AI 模式下提供「数据自动摘要」（描述性统计、列类型识别、自动选图）与「缺失/矛盾基础校验增强」，强化离线即能用的差异化卖点。
- **S6 模板档案（Brand Profile）**：仿 brand-docs：把每个模板解析出的占位符 schema、必填字段、风格/格式约束缓存为「模板档案」，跨会话复用、校验一致，并支持模板中心管理。
- **S7 PDF 导出两级策略**：仿 LogicPaper（本地 LibreOffice Headless）+ project240（可选 Gotenberg 服务）：提供「本地 LibreOffice 转换（默认）+ 可选容器化服务」两级导出，降低对用户已装 Word 的依赖。
- **S8 测试套件强化**：仿 docxtemplater：为复杂模板（页眉页脚、多表格、图片锚点、批量多行）建立回归测试夹具与快照对比，纳入 CI。
- **S9 许可与合规检查**：保持 MIT 默认无 AI；在 THIRD_PARTY_LICENSES 中明确 docxtpl(LGPL-2.1)/matplotlib(PSF)/PySide6(LGPL-3) 等义务；不把 Carbone/docxtemplater 高级模块/LogicPaper(CC BY-NC) 作为默认依赖，只借鉴设计思想。
- **S10 一键「实操截图→对应章节」**：仿 lab-report-autopilot：提供「按实验类型自动建议截图放置位置」的映射模板（如 数据库实验→查询结果截图放结果分析），配合手动确认，减少用户逐字段绑定成本。

---

## 五、方法与数据说明

- 检索：GitHub Search API，16 组关键词，per_page=30，共 340 个去重候选。
- 核实：对 32 个入选仓库调用 `GET /repos/{owner}/{repo}` 获取权威元数据（star/license/语言/最近提交）；对其中 14 个抓取 README 原文做功能与架构分析。
- 数据时间：2026-10-24。star 与最近提交会随时间变化，如需引用请以 GitHub 页面为准。
- 未纳入的低相关项：纯 OCR 库、LaTeX 实验模板、纯 BI 大平台、噪声/教学仓库已在筛选中排除。
- 本报告仅作调研与建议，不含虚构数据。
