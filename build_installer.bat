@echo off
setlocal EnableExtensions
rem ============================================================
rem  FormoraReport 安装包构建脚本（Inno Setup 6）
rem
rem  用法：
rem     双击运行，或在命令行执行 build_installer.bat
rem
rem  前置条件：
rem     1. 已安装 Inno Setup 6（https://jrsoftware.org/isinfo.php）
rem     2. 已构建 dist\FormoraReport.exe
rem        （pyinstaller --noconfirm --clean FormoraReport-onefile.spec）
rem
rem  产物：
rem     dist\FormoraReport-Setup-2.18.0.exe
rem
rem  说明：
rem     脚本按以下顺序自动定位 ISCC.exe：
rem       ① 环境变量 ISCC_PATH（指向 Inno Setup 6 安装目录）
rem       ② 常见安装位置（Program Files x86 / Program Files / LocalAppData）
rem       ③ PATH（where ISCC.exe）
rem ============================================================

set "ROOT=%~dp0"
set "ISS=%ROOT%installer.iss"
set "ISCC="

rem ---------- 定位 ISCC.exe ----------

rem ① 环境变量 ISCC_PATH
if defined ISCC_PATH (
    if exist "%ISCC_PATH%\ISCC.exe" set "ISCC=%ISCC_PATH%\ISCC.exe"
)

rem ② 常见安装位置
if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
)

rem ③ PATH 中查找
if not defined ISCC (
    for /f "delims=" %%i in ('where ISCC.exe 2^>nul') do (
        if not defined ISCC set "ISCC=%%~i"
    )
)

rem ---------- 检查环境 ----------

if not defined ISCC (
    echo [错误] 未找到 Inno Setup 6 编译器 ISCC.exe。
    echo.
    echo 请先安装 Inno Setup 6（https://jrsoftware.org/isinfo.php），
    echo 或在环境变量 ISCC_PATH 中指定 Inno Setup 6 的安装目录（如 C:\Program Files (x86)\Inno Setup 6）。
    exit /b 1
)

if not exist "%ROOT%dist\FormoraReport.exe" (
    echo [错误] 未找到程序文件: %ROOT%dist\FormoraReport.exe
    echo.
    echo 请先构建单文件程序:
    echo     pyinstaller --noconfirm --clean FormoraReport-onefile.spec
    exit /b 1
)

if not exist "%ISS%" (
    echo [错误] 未找到安装包脚本: %ISS%
    exit /b 1
)

rem ---------- 编译 ----------

echo 使用编译器: %ISCC%
echo 安装包脚本: %ISS%
echo 正在编译，请稍候...
echo.

"%ISCC%" "%ISS%"
if errorlevel 1 (
    echo.
    echo [错误] Inno Setup 编译失败，请检查上方日志。
    exit /b 1
)

echo.
echo ============================================================
echo 构建成功！
echo 安装包: %ROOT%dist\FormoraReport-Setup-2.18.0.exe
echo ============================================================

endlocal