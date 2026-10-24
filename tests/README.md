# 测试基础设施

本目录存放 FormoraReport 的自动化测试与测试基础设施。

## 快速开始

```bash
# 安装依赖（含开发/测试工具）
pip install -r requirements-dev.txt

# 运行全部测试（Windows 下 UI 测试会自动 offscreen）
pytest

# 只跑单元测试（跳过 UI 冒烟）
pytest -m "not ui"

# 带覆盖率运行
coverage run -m pytest
coverage report -m
```

## 配置

- `pytest.ini`（项目根）：测试发现路径、`src` 导入路径、markers、addopts、告警过滤。
- `.coveragerc`（项目根）：覆盖率统计范围与报告格式。
- `tests/conftest.py`：共享夹具（样例文件、Config 工厂、任务状态工厂、QApplication）。

## 目录组织

```
tests/
├── conftest.py               # 共享夹具与路径设置
├── README.md                 # 本文档
├── samples/                  # 真实样例（模板 DOCX + 实验数据 CSV，缺失时自动生成）
├── test_ai_client*.py        # AI 客户端：URL 校验、请求/响应解析（离线 mock）
├── test_ai_workflow.py       # AI 结果落盘映射
├── test_animations.py        # UI 动画降级行为
├── test_app_state.py         # 应用状态
├── test_chart*.py            # 图表生成
├── test_config*.py           # 配置/DPAPI
├── test_core.py              # 核心集成测试（模板/数据/映射/生成/校验）
├── test_data_reader*.py      # 数据读取
├── test_errors.py            # 异常体系
├── test_generator*.py        # 报告生成
├── test_history*.py          # 历史记录
├── test_logging_setup*.py    # 日志
├── test_mapper*.py           # 字段映射
├── test_models*.py           # 数据模型
├── test_pdf_exporter.py      # PDF 导出（离线 mock LibreOffice/Word）
├── test_report_reader.py     # 报告文本读取
├── test_report_service*.py   # 报告服务
├── test_services.py          # 服务层集成
├── test_template_parser*.py  # 模板解析
├── test_ui.py                # UI 冒烟（子进程）
├── test_v21.py               # 2.1 版本逻辑
├── test_v211.py              # 2.1.1 版本逻辑
├── test_v23.py               # 2.3 版本逻辑
├── test_v24.py               # 2.4 版本逻辑
└── test_window_effects.py    # 窗口系统效果降级
```

带 `*` 后缀的是同主题的补充单元测试文件；`test_*.py` 命名由 pytest 自动发现。

## Markers

| Marker        | 含义                                        | 示例命令                    |
|---------------|---------------------------------------------|-----------------------------|
| `ui`          | UI 冒烟测试（需 Qt，offscreen 运行）          | `pytest -m "not ui"`        |
| `integration` | 使用真实样例并生成输出的集成测试              | `pytest -m integration`     |
| `slow`        | 运行较慢的测试                                | `pytest -m "not slow"`      |
| `network`     | 涉及真实网络请求（测试中默认被 mock）          | `pytest -m network`         |
| `dpapi`       | 仅 Windows DPAPI 相关                        | `pytest -m dpapi`           |

新增测试如需使用 marker，先检查 `pytest.ini` 中是否已注册；未注册的 marker 在
`--strict-markers` 下会直接报错。

## 编写约定

- 不要修改业务代码（`src/`）来迁就测试；测试只覆盖既有行为。
- 新测试直接 `from formora... import ...`，无需手写 `sys.path.insert`（`pytest.ini` 的
  `pythonpath = src` 已处理，`conftest.py` 再兜底）。
- 网络、LibreOffice、Word COM、DPAPI 等外部依赖一律用 `monkeypatch` mock，保持离线可跑。
- 输出文件写入 `tmp_path` 临时目录，不污染 `tests/output`。
- 需要样例模板/数据时使用 `template_path` / `data_path` 夹具。
- 需要构造完整任务状态时使用 `make_task_state` 夹具。

## 覆盖率

`.coveragerc` 已配置：

- `source = formora`：只统计业务包。
- `omit`：UI 页面与入口（需要真实 Qt 交互，暂不纳入统计）。
- `branch = True`：分支覆盖率。

本地生成 HTML 报告：`coverage html`，结果在 `htmlcov/`（已被 .gitignore 忽略）。
