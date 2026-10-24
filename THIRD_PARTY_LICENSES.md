# 第三方依赖与许可证清单

FormoraReport 基于以下开源组件构建。所有许可证均允许本项目（MIT）分发使用；其中 LGPL/GPL 类依赖以独立库方式使用并保留声明。如需商业闭源分发，请特别留意 PySide6（Qt）LGPL 的动态链接义务（可购买 Qt 商业许可）。

## 运行时依赖（Python）

| 依赖 | 用途 | 许可证 | 说明 |
|------|------|--------|------|
| python-docx | DOCX 读写 | MIT | |
| docxtpl | 模板占位符替换/保真 | LGPL-2.1 | 以独立库方式使用，不修改其源码 |
| openpyxl | XLSX 读写 | MIT | 官方源码托管于 Heptapod |
| pandas | 表格数据处理 | BSD-3-Clause | |
| pdfplumber | PDF 文本/表格提取 | MIT | |
| matplotlib | 数据图表 | PSF License | |
| Pillow | 图像处理 | HPND (PIL) | |
| PySide6 (Essentials) | 桌面 UI | LGPL-3 / GPL-3 / 商业 | 以动态链接使用；商业闭源需注意 |
| jinja2 | 模板引擎（经 docxtpl） | BSD-3-Clause | |

## 构建/开发依赖

| 依赖 | 用途 | 许可证 |
|------|------|--------|
| PyInstaller | 打包 EXE | GPL-2.0（含商业例外） |
| pytest | 测试 | MIT |

## OCR / PDF 导出（可选增强，未默认捆绑）

| 组件 | 用途 | 许可证 |
|------|------|--------|
| PaddleOCR | OCR/版面/表格识别（可选） | Apache-2.0 |
| LibreOffice | DOCX→PDF 转换（可选，外部程序） | MPL-2.0 |

## 调研参考项目（未直接合并代码，仅作设计参考）

| 项目 | 许可证 | 参考点 |
|------|--------|--------|
| python-docx (MIT) | MIT | 直接依赖 |
| docxtpl (LGPL-2.1) | LGPL-2.1 | 直接依赖 |
| docling (MIT) | MIT | AI 文档结构化设计参考 |
| docxtemplater (核心 MIT，高级模块付费) | 核心 MIT | 因付费模块未采用 |
| camelot (MIT) | MIT | 表格提取参考，未采用（维护停滞） |

> 本项目遵循各许可证的署名与再分发义务。若你分发包含这些组件的产物，请保留相应版权与许可证声明。