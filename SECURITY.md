# 安全策略

## 支持的版本

| 版本 | 支持状态 |
|------|----------|
| 最新 Release（v0.x） | ✅ 受支持 |
| 历史 Release | ⚠️ 尽力而为 |

## 隐私承诺

- **无 AI 模式**：所有文件仅在本机处理，不联网、不上传。
- **AI 模式**：仅在用户主动点击「AI 辅助填写」时，把当前任务需要的字段名与素材文本发送到用户自配的 API；不静默上传。
- **API 密钥**：使用 Windows DPAPI（CryptProtectData）加密后存储于 `%APPDATA%/FormoraReport/config.json`，不明文落盘，不写入日志。
- **日志**：仅记录操作摘要与错误类别，不包含文档正文、密钥或完整用户数据。

## 报告安全漏洞

请**不要**在公开 Issue 中提交敏感信息（密钥、真实实验数据、个人文件）。

发现安全漏洞请通过 [GitHub Security Advisories](https://github.com/Liao0429/FormoraReport/security/advisories/new) 私有报告，或在 Issue 中说明「存在安全漏洞」并等待私信。

## 数据与文件安全

- 用户数据只写入 `%APPDATA%/FormoraReport/` 与用户选择的输出目录。
- 临时文件位于系统临时目录，退出时清理。
- 仓库 `.gitignore` 排除日志、输出、密钥、用户数据与机器特定路径。
- 发布前会对依赖进行许可证与已知漏洞核查。

## 依赖安全

- 第三方依赖清单与许可证见 `THIRD_PARTY_LICENSES.md`。
- CI 会运行测试与静态检查；重大依赖更新需评审。