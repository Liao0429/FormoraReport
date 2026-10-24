; FormoraReport installer (NSIS)
; Build: makensis installer.nsi
Unicode true
!include "MUI2.nsh"

Name "FormoraReport"
OutFile "FormoraReport-Setup-2.3.0.exe"
InstallDir "$PROGRAMFILES64\FormoraReport"
InstallDirRegKey HKLM "Software\\FormoraReport" "InstallDir"

RequestExecutionLevel admin
SetCompressor /SOLID lzma

; Version info
VIProductVersion "2.3.0.0"
VIAddVersionKey "ProductName" "FormoraReport"
VIAddVersionKey "FileDescription" "FormoraReport Installer"
VIAddVersionKey "ProductVersion" "2.3.0"
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
  File /r "..\dist\FormoraReport\*.*"

  WriteRegStr HKLM "Software\FormoraReport" "InstallDir" "$INSTDIR"
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
  DeleteRegKey HKLM "Software\FormoraReport"
SectionEnd