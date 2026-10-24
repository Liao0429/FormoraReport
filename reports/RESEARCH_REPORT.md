# FormoraReport 开源项目调研与技术选型报告

> 阶段：P1（GitHub 开源调研）
> 生成时间：2026-10-22
> 方法：GitHub Search API 实际检索 12 组关键词，共抓取 **110 个去重真实仓库**（原始抓取数据含第三方 README 正文，因隐私与许可证原因**不随仓库分发**），并针对高相关核心库用 `/repos` 接口**定向核实**元数据、抓取 README 验证功能与许可证。**所有仓库、星标数、许可证、维护时间均来自 GitHub API 实际返回，无虚构。**

---

## 一、候选项目调研表（15 个经核实的真实仓库）

调研维度：用途/技术栈/许可证/维护情况/核心实现/Windows/离线/可复用模块/集成难度。

### 1. python-openxml/python-docx
- **地址**：https://github.com/python-openxml/python-docx
- **用途**：读写 Microsoft Word 2007+ (.docx) 文件。
- **技术栈**：Python（纯 Python，基于 lxml 解析 OOXML）。
- **许可证**：MIT（商业使用/修改/再分发自由，仅需保留版权声明）。
- **维护情况**：⭐5749，最近推送 2026-08，活跃维护；PyPI 最新版稳定。
- **核心实现**：直接操作 OOXML（document.xml + 样式/页眉页脚/表格等 part），提供 Document/Paragraph/Table 等对象模型。
- **Windows**：✅ 跨平台，纯 Python 无原生依赖。
- **离线**：✅ 完全本地。
- **可复用**：DOCX 解析、段落/表格/图片/样式/页眉页脚读写——**本项目的文档保真基石**。
- **集成难度**：低。**选为直接依赖**。

### 2. elapouya/python-docx-template（docxtpl）
- **地址**：https://github.com/elapouya/python-docx-template
- **用途**：把 DOCX 作为 Jinja2 模板，用占位符替换生成新文档。
- **技术栈**：Python，基于 python-docx + jinja2。
- **许可证**：**LGPL-2.1**（可商用；若以动态库/独立进程方式使用且不修改其源码，可保持闭源；本项目开源，无冲突）。
- **维护情况**：⭐2726，最近推送 2026-07，活跃。
- **核心实现**：在 Word 中把 `{{ var }}`、`{% for %}` 标签直接写进模板，解析后替换并保留原有格式、表格、图片、页眉页脚。
- **Windows**：✅ / **离线**：✅
- **可复用**：**占位符替换 + 格式保留 + 表格/图片注入**——正是本项目「原 Word 模板保真填写」的核心机制。
- **集成难度**：低。**选为直接依赖**。

### 3. jsvine/pdfplumber
- **地址**：https://github.com/jsvine/pdfplumber
- **用途**：提取 PDF 中每个字符、矩形、线条、表格、表单值。
- **技术栈**：Python，基于 pdfminer.six。
- **许可证**：MIT。
- **维护情况**：⭐10838，最近推送 2026-10，活跃。
- **核心实现**：逐对象解析 PDF，提供 `extract_text()`、`extract_tables()`、`extract_form()` 等。
- **Windows**：✅ / **离线**：✅
- **可复用**：PDF 实验要求/参考资料文本与表格提取。
- **限制**：README 明确「最适合机器生成 PDF，非扫描件」；扫描件需 OCR 前置。
- **集成难度**：低。**选为直接依赖**。

### 4. PaddlePaddle/PaddleOCR
- **地址**：https://github.com/PaddlePaddle/PaddleOCR
- **用途**：OCR 文字识别 + PP-Structure 版面分析/表格识别/关键信息抽取，支持 PDF→Word。
- **技术栈**：Python + PaddlePaddle 深度学习框架。
- **许可证**：Apache-2.0（商用友好）。
- **维护情况**：⭐91512，最近推送 2026-09，活跃。
- **核心实现**：PP-OCRv4 检测+识别，PP-StructureV2 版面复原/表格识别，CPU 可跑。
- **Windows**：✅ / **离线**：✅（本地推理）。
- **可复用**：**截图/扫描件 OCR、表格识别、版面分析**——本项目「操作截图识别」「扫描PDF OCR」「表格数据提取」可选增强。
- **风险**：PaddlePaddle 依赖体积大（数百 MB），首次导入慢。**作为可选 OCR 增强（非默认）**，MVP 先不捆绑。
- **集成难度**：中（大依赖）。

### 5. JaidedAI/EasyOCR
- **地址**：https://github.com/JaidedAI/EasyOCR
- **用途**：轻量 OCR，80+ 语言，纯 Python API。
- **许可证**：Apache-2.0。
- **维护情况**：⭐30094，最近推送 2025-12。
- **核心实现**：基于 PyTorch + 预训练 CRNN 模型。
- **Windows/离线**：✅ / ✅（模型本地加载）
- **可复用**：OCR 备选方案。**风险**：依赖 PyTorch（体积大）。MVP 不作为默认。
- **集成难度**：中。

### 6. DS4SD/docling
- **地址**：https://github.com/DS4SD/docling
- **用途**：IBM 文档解析，把 PDF/DOCX/PPTX/XLSX/图片等转换为结构化 Markdown/JSON。
- **许可证**：MIT。
- **维护情况**：⭐69350，最近推送 2026-10，活跃。
- **核心实现**：版面分析 + 阅读顺序 + 表格结构 + OCR，输出层级化 JSON/Markdown。
- **Windows/离线**：✅ / ✅（本地模型可选）
- **可复用**：**AI 模式下对复杂实验材料做语义结构化**。**风险**：依赖较重（部分模型需下载）。作为 AI 模式可选组件，默认不加载。
- **集成难度**：中高。

### 7. Unstructured-IO/unstructured
- **地址**：https://github.com/Unstructured-IO/unstructured
- **用途**：非结构化文档（PDF/HTML/DOCX/图片）分区、抽取、结构化。
- **许可证**：Apache-2.0。
- **维护情况**：⭐15589，最近推送 2026-10。
- **核心实现**：文档分区 + 元素抽取，提供 API 与本地库。
- **Windows/离线**：✅ / ⚠️ 部分功能依赖在线模型/API；纯本地需选本地解析器。
- **可复用**：AI 模式文档结构化参考。
- **集成难度**：中高；依赖复杂。**暂不采用**（与 docling 功能重叠，docling 许可证更宽松且本地化更好）。

### 8. open-xml-templating/docxtemplater
- **地址**：https://github.com/open-xml-templating/docxtemplater
- **用途**：JS 版 DOCX/PPTX 模板生成，支持占位符、循环、条件。
- **许可证**：**⚠️ 核心 MIT，但 Image/Html/Table/Styling/QrCode 等模块为付费商业模块**（GitHub 显示 NOASSERTION）。
- **维护情况**：⭐3640，最近推送 2026-10，活跃。
- **核心实现**：JS 解析 docx XML 模板。
- **Windows/离线**：✅ / ✅
- **可复用**：设计思想（占位符语法、循环表）。
- **结论**：**不采用**——高级功能需付费许可证，与开源/低成本目标冲突；docxtpl 已覆盖同等能力且开源更彻底。

### 9. atlanhq/camelot
- **地址**：https://github.com/atlanhq/camelot
- **用途**：PDF 表格提取（lattice 网格线 / stream 流式）。
- **许可证**：GitHub 显示 NOASSERTION（实际 MIT，附带 Ghostscript 依赖说明）。
- **维护情况**：⭐3705，**最近推送 2023-01，基本停止维护**。
- **核心实现**：基于 pdfminer + OpenCV，识别表格线提取。
- **Windows/离线**：✅ / ✅（但依赖 Ghostscript 处理部分 PDF）
- **可复用**：表格提取算法参考。
- **结论**：**不采用**——维护停滞且需 Ghostscript；pdfplumber 表格提取已够 MVP 使用。

### 10. jmcnamara/XlsxWriter
- **地址**：https://github.com/jmcnamara/XlsxWriter
- **用途**：写 Excel 2007+ (.xlsx)，支持图表、条件格式、数据验证。
- **许可证**：BSD-2-Clause。
- **维护情况**：⭐3985，最近推送 2026-10，活跃。
- **核心实现**：流式写入 OOXML，低内存。
- **Windows/离线**：✅ / ✅
- **可复用**：**实验数据表格与图表导出**。与 openpyxl 功能重叠，二选一。
- **结论**：**备选**。本项目读取 XLSX 用 openpyxl，写表格/图表 MVP 用 matplotlib + python-docx 即可，XlsxWriter 作为扩展。

### 11. matplotlib/matplotlib
- **地址**：https://github.com/matplotlib/matplotlib
- **用途**：数据可视化图表。
- **许可证**：Python Software Foundation License（宽松、商用友好）。
- **维护情况**：⭐23386，活跃。
- **Windows/离线**：✅ / ✅
- **可复用**：**实验数据折线/柱状/散点图生成**，输出 PNG 插入 DOCX。
- **集成难度**：低。**选为直接依赖**。

### 12. pallets/jinja2
- **地址**：https://github.com/pallets/jinja2
- **用途**：模板引擎。
- **许可证**：BSD-3-Clause。
- **维护情况**：⭐11799，活跃。
- **核心实现**：字符串/模板渲染。
- **可复用**：经 docxtpl 间接使用；也用于报告内容模板。
- **集成难度**：低。**经 docxtpl 传递依赖使用**。

### 13. Kozea/WeasyPrint
- **地址**：https://github.com/Kozea/WeasyPrint
- **用途**：HTML/CSS → PDF。
- **许可证**：BSD-3-Clause。
- **维护情况**：⭐9724，活跃。
- **Windows/离线**：✅ / ✅
- **可复用**：**导出 PDF 的备选方案**（把生成的 HTML 报告转 PDF）。
- **结论**：**备选**。MVP 先以 DOCX 为第一输出；PDF 优先用 LibreOffice 无头转换（若用户装有）或 WeasyPrint HTML 渲染。

### 14. pymupdf/PyMuPDF
- **地址**：https://github.com/pymupdf/PyMuPDF
- **用途**：PDF 渲染/提取/OCR 接口。
- **许可证**：**AGPL-3.0（⚠️ 强 copyleft，含网络服务义务）**。
- **维护情况**：⭐10964，活跃。
- **可复用**：PDF 渲染/文本提取。
- **结论**：**核心依赖不采用**（AGPL 对商业化闭源构成约束）。PDF 文本提取用 pdfplumber（MIT）替代；扫描件 OCR 用 PaddleOCR（Apache-2.0）。**如需 PDF 渲染预览，另行评估其 AGPL 义务或找替代**。

### 15. tesseract-ocr/tesseract
- **地址**：https://github.com/tesseract-ocr/tesseract
- **用途**：OCR 引擎（C++）。
- **许可证**：Apache-2.0。
- **维护情况**：⭐77109，活跃。
- **可复用**：OCR 引擎。Windows 需安装二进制或使用 `pytesseract` + 安装包。
- **结论**：**备选**。与 PaddleOCR 二选一；PaddleOCR 中文/版面/表格更强，故首选 PaddleOCR。

---

## 二、功能对照与复用决策表

| 本项目功能 | 复用的开源方案 | 集成方式 | 选择理由 | 许可证义务 |
|-----------|---------------|---------|---------|-----------|
| DOCX 模板解析/填写/保真 | python-docx | 直接依赖 | 成熟、活跃、MIT、格式保真 | 保留 MIT 版权声明 |
| 占位符替换+表格/图片注入 | docxtpl | 直接依赖 | 正是「原模板保真填写」机制 | LGPL-2.1 声明；开源项目兼容 |
| XLSX/CSV 数据读取 | openpyxl + pandas | 直接依赖 | 行业标准 | MIT / BSD |
| PDF 文本/表格提取 | pdfplumber | 直接依赖 | 轻量、MIT、机器生成 PDF 效果好 | 保留 MIT 声明 |
| 图表生成 | matplotlib | 直接依赖 | 成熟、图表类型全 | PSF 许可证 |
| OCR/截图/扫描识别（可选AI） | PaddleOCR | 可选增强（懒加载） | 中文/表格/版面强、Apache-2.0、离线 | 保留 Apache 声明 |
| AI 文档语义结构化（可选AI） | docling 或自研+兼容API | 可选增强 | MIT、可本地 | 保留 MIT 声明 |
| AI 模型接入 | OpenAI 兼容 API（用户自配） | 可选增强 | 不依赖特定厂商 | 用户密钥本地保存 |
| PDF 导出 | LibreOffice 无头 / WeasyPrint | 可选 | 视用户环境 | MPL-2.0 / BSD-3 |
| 桌面 UI | PySide6 | 直接依赖 | 现代、跨平台、LGPL 商用友好 | 保留 LGPL 声明 |
| 打包 EXE | PyInstaller | 构建 | 单文件/目录、GPL 带商用例外 | 例外允许商业用途 |

**不采用的项目及理由**：
- **docxtemplater（JS）**：高级模块付费，许可证不友好。
- **camelot**：维护停滞 + 依赖 Ghostscript。
- **unstructured**：依赖复杂、部分功能在线，与 docling 重叠。
- **PyMuPDF**：AGPL 强 copyleft，阻碍商业闭源路径。
- **EasyOCR**：依赖 PyTorch 体积大，PaddleOCR 中文更强。

---

## 三、主技术栈定案：Python 3.12 + PySide6

### 对比分析

| 方案 | 本机工具链 | 文档生态 | 打包 | 体积 | 开发效率 | 结论 |
|------|-----------|---------|------|------|---------|------|
| **Python + PySide6** | ✅ 已装 3.12 | 极强（python-docx/docxtpl/pdfplumber/openpyxl/matplotlib） | PyInstaller | 约 60–150MB | 高 | ✅ **采用** |
| C# + .NET + WPF/WinUI3 | ❌ 需装 SDK | 中（Open XML SDK、NPOI） | 单文件自包含 | 约 100–200MB | 中 | 可作未来原生版，本轮不选 |
| Tauri + Web 前端 | ❌ 需装 Rust | 依赖 Rust 侧库或 Web 库 | NSIS/MSI | 约 10–30MB | 中 | 生态较新、Rust 门槛高，本轮不选 |

### 选择理由（依据调研）
1. **文档处理生态压倒性优势**：调研的 15 个核心库中 13 个是 Python 库（MIT/BSD/Apache/LGPL 宽松许可），可直接复用，避免重造轮子。
2. **本机零额外开发工具**：Python 3.12 已装；无需安装 .NET/Rust 大型 SDK。
3. **离线/本地优先**：所有核心库纯本地运行，无云依赖，满足无 AI 模式。
4. **打包成熟**：PyInstaller 可生成独立 EXE，用户无需安装 Python。
5. **商业化许可证友好**：核心依赖均为宽松/商用友好许可（MIT/BSD/Apache/LGPL 声明式）；PySide6 为 LGPL，商用需遵守动态链接与声明要求（Qt 官方提供商业许可可消除此义务）。
6. **UI 满足「液态玻璃」参考**：PySide6 支持半透明、模糊（QtGraphicalEffects）、圆角、动画、深浅主题，兼顾高 DPI。

### 关键技术选型明细
- **UI**：PySide6（Qt6）
- **DOCX 生成/保真**：python-docx + docxtpl
- **数据读取**：openpyxl、pandas（CSV/XLSX）
- **PDF 提取**：pdfplumber
- **OCR（可选）**：PaddleOCR（懒加载）
- **图表**：matplotlib
- **AI 适配**：OpenAI 兼容 HTTP API（用户自配 base_url/model/key），密钥用系统凭据（Windows Credential Manager / 加密文件）
- **打包**：PyInstaller（--onedir 或 --onefile）
- **日志**：logging + 滚动文件
- **配置**：JSON/TOML + 加密敏感项
- **版本控制**：git（GitHub）

---

## 四、许可证风险表

| 依赖 | 许可证 | 商用风险 | 规避措施 |
|------|--------|---------|---------|
| python-docx | MIT | 无 | 保留版权声明 |
| docxtpl | LGPL-2.1 | 低 | 开源分发声明；不修改其源码则商业闭源亦可（动态链接方式） |
| pdfplumber | MIT | 无 | 保留声明 |
| openpyxl | MIT | 无 | 保留声明 |
| pandas | BSD-3 | 无 | 保留声明 |
| matplotlib | PSF | 无 | 保留声明 |
| PySide6 | LGPL-3 | 低-中 | 开源分发声明；商业闭源需 Qt 商业许可或遵守 LGPL 动态链接 |
| PyInstaller | GPL-2.0 带例外 | 低 | 例外条款允许将其用于商业应用打包 |
| PaddleOCR（可选） | Apache-2.0 | 无 | 保留声明 |
| WeasyPrint | BSD-3 | 无 | 保留声明 |

**结论**：采用 Python 技术栈的许可证组合**支持本项目开源（建议 MIT 或 Apache-2.0）**；若未来走商业闭源，需处理 PySide6（Qt）LGPL 动态链接义务（可购 Qt 商业许可）。**项目 LICENSE 在 P8 阶段依据最终依赖清单核定**。

---

## 五、已知限制（如实记录）
- PDF 文本提取只对**机器生成 PDF**可靠；扫描件需 OCR（可选增强，MVP 默认不捆绑）。
- 旧版 `.doc` 不支持（python-docx 仅 .docx）；提供提示与转换建议。
- 复杂公式（MathML/OMML）保真能力有限，MVP 以文本/图片方式处理。
- DOCX→PDF 转换依赖用户环境的 LibreOffice 或 Word COM；若均无，则仅导出 DOCX 并明确提示。

*调研数据原始文件（含第三方 README 正文）因隐私与许可证考虑已从版本库移除，未随仓库分发。*