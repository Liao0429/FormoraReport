# FormoraReport 安装包构建说明（Inno Setup）

本文档介绍如何在本机构建 FormoraReport 的 Windows 一键安装包。

## 1. 产物概览

| 文件 | 说明 |
|---|---|
| `installer.iss` | Inno Setup 6 安装脚本（本项目使用 Inno Setup 而非 NSIS） |
| `build_installer.bat` | Windows 一键构建脚本，自动定位 `ISCC.exe` 并编译 |
| `dist\FormoraReport-Setup-2.18.0.exe` | 构建产物：最终安装包 |

> 安装包内打包的是**单文件版** `dist\FormoraReport.exe`
> （由 `pyinstaller --noconfirm --clean FormoraReport-onefile.spec` 生成）。

## 2. 前置条件

- **操作系统**：Windows 10 / 11（64 位）
- **Inno Setup 6**（建议 6.3 或更高版本，脚本使用了 `x64compatible`、`CloseApplications` 等特性）
- **已构建的程序文件**：`dist\FormoraReport.exe`（若缺失，先执行下方命令构建）：

```bat
pyinstaller --noconfirm --clean FormoraReport-onefile.spec
```

## 3. 安装 Inno Setup 6

### 方式一：官网下载（推荐）

1. 打开官网 <https://jrsoftware.org/isinfo.php>
2. 下载最新版 Inno Setup 6 安装程序（如 `innosetup-6.x.x.exe`）
3. 双击运行，一路“下一步”即可（默认安装到 `C:\Program Files (x86)\Inno Setup 6`）

### 方式二：包管理器

```bat
:: winget
winget install JRSoftware.InnoSetup

:: 或 Chocolatey
choco install innosetup
```

安装完成后，可执行以下命令验证编译器是否可用：

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?
```

## 4. 构建安装包

### 4.1 一键构建（推荐）

在项目根目录双击 `build_installer.bat`，或在命令行执行：

```bat
cd /d H:\FormoraReport
build_installer.bat
```

脚本会自动按以下顺序定位 `ISCC.exe`：

1. 环境变量 `ISCC_PATH`（若设置，指向 Inno Setup 6 安装目录）
2. 常见安装位置：
   - `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
   - `C:\Program Files\Inno Setup 6\ISCC.exe`
   - `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`
3. 系统 `PATH`（`where ISCC.exe`）

编译成功后会显示安装包路径；若失败会给出明确错误原因（如未安装 Inno Setup、
缺少 `dist\FormoraReport.exe` 等）。

### 4.2 手动编译

如果不想使用批处理，也可以直接用 ISCC 编译：

```bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### 4.3 编译产物

编译成功后，安装包输出到：

```
H:\FormoraReport\dist\FormoraReport-Setup-2.18.0.exe
```

> `dist` 目录已在 `.gitignore` 中忽略，安装包二进制不会进入版本库。

## 5. 安装包行为

运行 `FormoraReport-Setup-2.18.0.exe` 后：

- **安装目录**：默认 `C:\Program Files\FormoraReport`
  （安装时可选“仅为当前用户安装”，此时安装到 `%LOCALAPPDATA%\Programs\FormoraReport`，无需管理员权限）
- **开始菜单**：创建 `FormoraReport` 程序组，含程序快捷方式与“卸载”快捷方式（卸载快捷方式可取消勾选）
- **桌面快捷方式**：默认勾选创建，可在安装向导中取消
- **卸载项**：自动注册到 Windows“设置 → 应用 → 已安装的应用”
- **安装后运行**：向导最后一步默认勾选“运行 FormoraReport”，点击“完成”即启动程序

### 静默安装 / 卸载

```bat
:: 静默安装（无界面，不重启，不创建桌面图标）
FormoraReport-Setup-2.18.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /TASKS=""

:: 静默卸载
"%ProgramFiles%\FormoraReport\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

## 6. 升级版本号

发布新版本时，修改 `installer.iss` 顶部的版本定义：

```iss
#define MyAppVersion "2.18.0"
```

同时更新 `build_installer.bat` 中的产物文件名（两处 `FormoraReport-Setup-2.18.0.exe`）
和本文档中的路径示例，然后重新运行 `build_installer.bat` 即可。

## 7. 常见问题

**Q：提示“未找到 Inno Setup 6 编译器 ISCC.exe”**

A：说明未安装 Inno Setup 6，或安装目录不在脚本搜索范围内。
安装后若仍报错，请设置环境变量 `ISCC_PATH` 指向 Inno Setup 6 安装目录，例如：

```bat
setx ISCC_PATH "C:\Program Files (x86)\Inno Setup 6"
```

**Q：提示“未找到程序文件 dist\FormoraReport.exe”**

A：先执行 `pyinstaller --noconfirm --clean FormoraReport-onefile.spec` 构建程序。

**Q：安装时提示程序正在运行**

A：安装脚本已启用 `CloseApplications`，会自动关闭正在运行的 FormoraReport
后再继续安装。

**Q：编译时提示 `x64compatible` 或 `CloseApplicationsFilter` 不被识别**

A：Inno Setup 版本过旧，请升级到 6.3 或更高版本（官网下载最新版即可）。