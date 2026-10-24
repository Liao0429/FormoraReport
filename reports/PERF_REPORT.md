# FormoraReport 性能基准报告

> 生成时间: 2026-10-22
> 方法: 真实样例（tests/samples），Python 3.14.7，本机 i5-10400F / 32GB
> 说明: 未虚构数据，可在本机复现（python scripts/benchmark.py）

| 指标 | 结果 |
|------|------|
| 样本 | 实验报告模板.docx + 实验数据.csv |
| 模板解析 | 95.1 ms |
| 数据读取 | 313.6 ms |
| 单文档生成（含图表） | 164.7 ms |
| 批量生成 100 份 | 4657.5 ms（平均 46.6 ms/份） |
| 进程内存(WorkingSet) | 159.5 MB |
