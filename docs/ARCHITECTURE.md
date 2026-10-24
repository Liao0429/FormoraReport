# FormoraReport 系统架构

> 阶段：P2 技术选型与系统架构
> 依据：`reports/RESEARCH_REPORT.md`（P1 调研）

## 一、模块图（分层）

```
┌─────────────────────────────────────────────────────────────┐
│  UI 层 (PySide6)                                            │
│  主窗口 · 首页 · 文档导入 · 模板编辑/字段映射 · 报告生成 ·     │
│  结果预览 · 模板中心 · AI设置 · 设置中心 · 主题(浅/深)         │
├─────────────────────────────────────────────────────────────┤
│  应用服务层                                                  │
│  TaskService(任务编排) · TemplateService(模板管理) ·           │
│  HistoryService(历史记录) · ConfigService(配置/密钥) ·       │
│  LogService(日志/异常分类)                                   │
├─────────────────────────────────────────────────────────────┤
│  文档解析层                                                  │
│  TemplateParser(DOCX占位符/章节/表格识别)                     │
│  DataReader(CSV/XLSX/TXT/PDF) · OCRAdapter(可选)             │
├─────────────────────────────────────────────────────────────┤
│  模板识别与字段映射层                                         │
│  FieldDetector(标题/目的/环境/步骤/数据/结果/问题/结论)        │
│  FieldMapper(列↔字段映射 + 校验)                              │
├─────────────────────────────────────────────────────────────┤
│  数据处理与图表层                                             │
│  DataProcessor(统计) · ChartGenerator(matplotlib→PNG)        │
├─────────────────────────────────────────────────────────────┤
│  文档生成与导出层                                             │
│  ReportGenerator(docxtpl/python-docx) · PdfExporter           │
├─────────────────────────────────────────────────────────────┤
│  AI 适配层（可选，独立进程/线程，默认不加载）                  │
│  AiClient(OpenAI兼容) · AiExtractor(结构化抽取) ·             │
│  AiReviewer(缺失/矛盾检查) · 来源追踪                         │
├─────────────────────────────────────────────────────────────┤
│  本地任务与历史记录层 · 配置/日志/异常处理层                   │
└─────────────────────────────────────────────────────────────┘
```

## 二、数据流（无 AI 模式核心链路）

```
导入模板(DOCX) ──► TemplateParser ──► 占位符/章节/表格清单
导入数据(CSV/XLSX/TXT/PDF) ──► DataReader ──► 结构化数据(DataFrame/文本)
        │
        ▼
   FieldMapper：字段 ↔ 数据列映射（自动+可手动修正）
        │
        ▼
   ReportGenerator(docxtpl 填充 + matplotlib 图表插入)
        │
        ▼
   预览（可编辑字段值）→ 重新生成 → 导出 DOCX / PDF(可选)
        │
        ▼
   Validator：缺失字段/空数据/错误格式 → 明确提示
```

## 三、核心数据结构（草稿）

```python
class TemplateInfo:
    path: Path
    placeholders: list[str]      # 检测到的 {{var}}
    sections: dict[str, list]    # 章节名 -> 段落/表格
    tables: list[TableInfo]

class FieldMapping:
    template_field: str          # 如 实验名称
    source_column: str | None    # 数据列名 / 常量 / 文本
    source_type: Literal["column","constant","text","chart","image"]
    value: Any                 # 预览/确认后的实际值

class ReportTask:
    id: str
    name: str
    template_path: Path
    data_source: DataSource
    mappings: list[FieldMapping]
    status: Literal["draft","mapping","generating","preview","done","failed"]
    logs: list[TaskLog]
    output_path: Path | None

class TaskLog:
    level: Literal["info","warning","error","success"]
    category: Literal["user","format","dependency","bug"]
    message: str
```

## 四、错误分类与处理策略

| 类别 | 示例 | 处理 |
|------|------|------|
| 用户错误 | 文件不存在/格式不支持/必填字段缺失 | 明确提示 + 引导 |
| 文档格式错误 | DOCX损坏/CSV乱码/模板无占位符 | 提示 + 建议转换 |
| 外部依赖错误 | LibreOffice缺失/OCR模型未装 | 提示降级方案 |
| 程序缺陷 | 未知异常 | 记录堆栈 + 用户可复制日志 |

统一日志：`logging` + 滚动文件 `logs/formora.log`；UI 显示摘要，详情可导出。

## 五、MVP 里程碑（P4）
1. TemplateParser：解析 DOCX 占位符与章节（可用）。
2. DataReader：CSV/XLSX/TXT/PDF 文本读取。
3. FieldMapper：自动映射 + 手动编辑。
4. ReportGenerator：docxtpl 填充 + 图表插入，输出可打开 DOCX。
5. Validator：缺失/空值/异常提示。
6. UI：导入→映射→预览→生成→导出 全流程。
7. 模板管理、批量处理、历史记录、基础动效。

## 六、AI 模式设计（P5，与核心隔离）
- 独立模块 `ai/`，仅在用户启用时导入。
- 接口：`extract_fields(materials) -> list[FieldCandidate]`，`review(content) -> list[Issue]`。
- 每个 AI 生成值带 `source`（依据段落/文件）与 `confidence`；无依据标「待补充/待确认」。
- 所有 AI 输出必须经用户逐项批准后才能进入导出。

## 七、数据与隐私
- 用户数据默认只在本地处理；AI 模式仅在用户明确操作时发送必要内容。
- 配置存 `%APPDATA%/FormoraReport/config.json`；API 密钥用 Windows DPAPI 加密。
- 临时文件在 `%LOCALAPPDATA%/Temp/FormoraReport`，退出清理。
- 仓库不含任何用户实验数据、密钥、机器特定路径。