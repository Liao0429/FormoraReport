# FormoraReport 开源前隐私与安全检查报告

- 检查时间：2026-10-24
- 检查范围：`H:\FormoraReport` 全部跟踪代码、配置、文档、测试样例、Git 历史
- 仓库状态：`Liao0429/FormoraReport`（GitHub **PUBLIC**，历史已推送）

## 一、检查方法

| 项目 | 方法 |
|------|------|
| 代码/配置敏感信息扫描 | 对全部跟踪文件正则扫描 API 密钥、密码、token、私钥、`.env`、个人路径、内网 IP、邮箱、手机号 |
| `.gitignore` 覆盖 | 逐条核对常见敏感文件/生成物/密钥文件 |
| 依赖漏洞 | `pip-audit -r requirements.txt` 与 `pip-audit`（已安装环境） |
| Git 历史泄露 | `git log --all -p` + 敏感正则全文扫描历史 |
| 测试样例 | 读取 `tests/samples/*.docx` / `*.csv` 内容，检查是否含个人真实数据 |

## 二、扫描结果

### 2.1 当前跟踪树（本报告修复后）

**未发现**：

- 硬编码 API 密钥 / 密码 / token / 私钥 / `.env` 文件
- 用户本人的内网 IP、邮箱（git 提交作者邮箱已改用 GitHub noreply 匿名地址）
- 手机号、学号等个人数据
- 测试样例均为模板占位符（`{{姓名}}`、`{{学号}}`）与合成数据（`样本A/B/C/D`）

**AI 密钥处理符合安全实践**：`src/formora/services/config.py` 使用 Windows DPAPI 加密存储 `api_key_enc`；`src/formora/ai/client.py` 仅运行时从配置读取；测试使用脱敏占位符 `sk-tes...-123`。

### 2.2 发现并已修复的问题

| # | 严重度 | 问题 | 处理 |
|---|--------|------|------|
| 1 | **高** | `reports/github_candidates_raw.csv`（512KB）被 git 跟踪，含**第三方仓库完整 README 正文**（SQL 注入/渗透测试命令、冒犯性内容、内网 IP `192.168.1.1`、第三方个人 LinkedIn 链接）。`docs/ANALYSIS.md` 原判断其“无 README 正文”不准确 | `git rm --cached` 停止跟踪并加入 `.gitignore`（本地保留）；同步修正 `docs/ANALYSIS.md` 与 `reports/RESEARCH_REPORT.md` 中对它的引用 |
| 2 | **中** | `docs/ANALYSIS.md` 曾包含本机用户名路径 | 已替换为 `%USERPROFILE%\...` 脱敏 |
| 3 | **低** | `.gitignore` 未覆盖安装器二进制与证书/覆盖率文件 | 新增 `packaging/*.exe`、`*.pem`、`*.ppk`、`.env.*`、`.coverage`、`htmlcov/`、`.tox/`、`.mypy_cache/`、`.ruff_cache/` |
| 4 | 已解决 | 早期提交中的 `reports/github_raw/*.json`、`reports/readmes/*.md`（同 CSV 的第三方原始内容） | 前序重构（`d7cb992`）已 `git rm`，本报告确认 HEAD 不再跟踪 |

### 2.3 依赖漏洞

`pip-audit -r requirements.txt`：**No known vulnerabilities found**
`pip-audit`（.venv 已安装环境）：**No known vulnerabilities found**

运行时依赖（python-docx/docxtpl/openpyxl/pandas/pdfplumber/matplotlib/Pillow/PySide6-Essentials）与开发依赖（pytest/PyInstaller/psutil）均无已知漏洞。

### 2.4 Git 历史提示（需决策，非阻塞）

仓库已公开且历史已推送。**历史提交 `5fbcc5e`、`d7cb992` 中仍包含**：

- 早期版本 `reports/github_raw/*.json`、`reports/readmes/*.md`（第三方原始 README，含冒犯性/渗透内容与内网 IP）
- 旧版 `docs/DECISIONS.md` 中的个人称呼（已清除）

当前 HEAD 已全部清除，但这些内容仍在公开历史中。**彻底清除需重写历史**（见下）。GitHub 公开身份 `Liao0429` 与提交邮箱为作者的开源身份，不属于泄露（当前提交已改用 noreply 匿名邮箱）。

## 三、可选历史重写命令（由仓库所有者决定执行）

> 重写会改变全部提交 SHA，可能影响已 fork/克隆的仓库；执行前请确认无协作者依赖旧历史。

```bash
# 1. 安装 git-filter-repo
pip install git-filter-repo
# 或 下载 https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo

# 2. 重写：从全部历史移除第三方原始调研文件与个人称呼
cd /h/FormoraReport
git filter-repo \
  --invert-paths \
  --path reports/github_raw/ \
  --path reports/readmes/ \
  --path reports/github_candidates_raw.csv

# 3. 强制推送（会改写远端历史）
git remote add origin https://github.com/Liao0429/FormoraReport.git
git push --force --all origin
```

## 四、验证结果

- ✅ 修复后对全部跟踪文件扫描：**未命中**任何密钥/密码/token/私钥/内网 IP/个人路径/手机号/个人中文名
- ✅ `.gitignore` 已覆盖 `.env*`、密钥、证书、打包产物、第三方原始数据、覆盖率与缓存
- ✅ `tests/samples/*` 为纯模板/合成数据
- ✅ 依赖审计无已知漏洞
- ✅ HEAD 已无 `reports/github_raw/`、`reports/readmes/`、`github_candidates_raw.csv` 跟踪

## 五、结论

**当前仓库（HEAD）不存在未脱敏的敏感信息，满足开源要求。**
剩余风险仅为**已公开历史**中的第三方原始抓取内容与旧个人称呼，是否重写历史由仓库所有者决定。