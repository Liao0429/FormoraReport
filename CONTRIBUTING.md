# 贡献指南

感谢你愿意为 FormoraReport 贡献！请遵循以下约定，让协作顺畅。

## 行为准则
所有参与者必须遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 如何贡献

1. **先开 Issue**：报告 bug、提出功能、讨论设计，避免重复劳动。
2. **Fork 并创建分支**：`feature/xxx` 或 `fix/xxx`。
3. **开发**：保持代码风格一致（PEP 8，模块化，类型注解），为关键逻辑补测试。
4. **测试**：`python -m pytest tests/ -q` 必须全部通过。
5. **提交**：写清晰的提交信息；不要提交密钥、用户数据、日志、输出文件。
6. **Pull Request**：描述改动、测试结果与相关 Issue。

## 代码约定
- 核心逻辑在 `src/formora/core/`，与 UI 解耦。
- AI 相关只在 `src/formora/ai/`，无 AI 模式不依赖 AI 模块。
- 异常统一走 `formora.core.errors` 分类（user/format/dependency/bug）。
- 用户数据与配置写入 `%APPDATA%/FormoraReport/`，不入仓库。

## 提交信息规范
推荐格式：`类型: 简述`，类型如 `feat` / `fix` / `docs` / `test` / `refactor` / `chore`。