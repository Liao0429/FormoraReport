; ============================================================
; FormoraReport Installer (NSIS)
;
; 本地构建:
;   makensis packaging\installer.nsi
;   产物: FormoraReport-Setup-<VERSION>.exe
;
; CI 自动化构建 NSIS 安装包（参考 .github/workflows/ci.yml；
; 若新增独立发布流程，建议命名为 release.yml）:
;   1. actions/setup-python + pip install pyinstaller，
;      执行 `pyinstaller --noconfirm --clean FormoraReport.spec`，
;      产出 dist/FormoraReport/ (PyInstaller onedir)。
;   2. 安装 NSIS（如 `choco install nsis`，或下载便携版并把 makensis 加入 PATH）。
;   3. 从源码读取版本号并注入:
;        $VERSION = (python -c "import sys; sys.path.insert(0,'src'); import formora; print(formora.__version__)")
;        makensis -DVERSION=$VERSION packaging\installer.nsi
;      或先设置环境变量 `FORMORA_VERSION` 再运行 makensis（NSIS 3 支持 ${env:...}）。
;   4. 用 actions/upload-artifact 上传 `FormoraReport-Setup-<VERSION>.exe`，
;      或通过 softprops/action-gh-release 附加到 GitHub Release。
; ============================================================
Unicode true
!include "MUI2.nsh"

; ===== 版本号（去硬编码） =====
; 优先从命令行/环境变量注入，未注入时回退到与 src/formora/__init__.py 同步的默认值。
; 注入方式（三选一，按优先级）:
;   A. makensis -DVERSION=2.10.0 packaging\installer.nsi
;   B. makensis -DFORMORA_VERSION=2.10.0 packaging\installer.nsi
;   C. 先设置环境变量 FORMORA_VERSION=2.10.0，再运行 makensis
; 注意: VERSION 应为 X.Y.Z 三段式（如 2.10.0），不要带前导 'v'。
!ifdef FORMORA_VERSION
  !define VERSION "${FORMORA_VERSION}"
!else
  !define /ifndef VERSION "${env:FORMORA_VERSION}"
  !if "${VERSION}" == ""
    !undef VERSION
    !define VERSION "2.10.0"
  !endif
!endif
; VIProductVersion 需要 4 段数字（X.Y.Z.W），由三段式 VERSION 补 .0 得到。
!define VERSION4 "${VERSION}.0"

Name "FormoraReport"
OutFile "FormoraReport-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\FormoraReport"
InstallDirRegKey HKLM "Software\\FormoraReport" "InstallDir"

RequestExecutionLevel admin
SetCompressor /SOLID lzma

; Version info
VIProductVersion "${VERSION4}"
VIAddVersionKey "ProductName" "FormoraReport"
VIAddVersionKey "FileDescription" "FormoraReport Installer"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "MIT License"

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Install"
  SetOutPath "$INSTDIR"
  ; ===== 分发路径（与 PyInstaller 模式对应） =====
  ; 当前工程使用 PyInstaller **onedir** 模式（FormoraReport.spec，PyInstaller 6.x 默认），
  ; 产出目录结构: dist/FormoraReport/FormoraReport.exe + dist/FormoraReport/_internal/...
  ; 因此用 `File /r "..\dist\FormoraReport\*.*"` 整目录递归打包是正确的。
  ;
  ; 若改用 **onefile** 模式（pyinstaller --onefile），产出为单一文件 dist/FormoraReport.exe，
  ; 不存在 dist/FormoraReport/ 目录，此时必须改用:
  ;     File "..\dist\FormoraReport.exe"
  ; 并删除上面的 `File /r`（onefile 运行时自解压到临时目录，首启较慢）。
  ; 两种模式二选一，勿同时打包。
  File /r "..\dist\FormoraReport\*.*"

  WriteRegStr HKLM "Software\\FormoraReport" "InstallDir" "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateShortcut "$DESKTOP\FormoraReport.lnk" "$INSTDIR\FormoraReport.exe"
  CreateDirectory "$SMPROGRAMS\FormoraReport"
  CreateShortcut "$SMPROGRAMS\FormoraReport\FormoraReport.lnk" "$INSTDIR\FormoraReport.exe"
  CreateShortcut "$SMPROGRAMS\FormoraReport\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\FormoraReport.lnk"
  RMDir /r "$SMPROGRAMS\FormoraReport"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "Software\\FormoraReport"
SectionEnd
