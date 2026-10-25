; ============================================================
; FormoraReport Windows 一键安装包 —— Inno Setup 6 脚本
;
; 前置条件:
;   - Inno Setup 6.3+（官网: https://jrsoftware.org/isinfo.php）
;   - 已构建单文件产物 dist\FormoraReport.exe
;     （pyinstaller --noconfirm --clean FormoraReport-onefile.spec）
;
; 构建方式（二选一）:
;   A. 双击 / 命令行运行 build_installer.bat（自动定位 ISCC.exe）
;   B. 手动执行:
;        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;
; 产物:
;   dist\FormoraReport-Setup-2.18.0.exe
;
; 安装行为:
;   - 默认安装到 {autopf}\FormoraReport（管理员为 Program Files，
;     普通用户可选安装到 %LOCALAPPDATA%\Programs\FormoraReport）
;   - 创建“开始”菜单快捷方式（默认）
;   - 可选创建桌面快捷方式（默认勾选）
;   - 可选创建“开始”菜单卸载快捷方式（默认勾选）
;   - 自动注册 Windows“应用和功能”卸载项
;   - 安装完成后可勾选立即运行程序（默认勾选）
; ============================================================

#define MyAppName "FormoraReport"
#define MyAppVersion "2.18.0"
#define MyAppVersion4 "2.18.0.0"
#define MyAppPublisher "FormoraReport Project"
#define MyAppURL "https://github.com/Liao0429/FormoraReport"
#define MyAppExeName "FormoraReport.exe"

[Setup]
; 稳定的应用标识（卸载/升级均依赖此 GUID，勿随意修改）
AppId={{C2BD4D26-19ED-4705-9E66-02302A34C53D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases

; 安装目录：{autopf} 在管理员安装时解析为 Program Files，
; 普通用户安装时解析为 %LOCALAPPDATA%\Programs
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 卸载相关
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; 平台：仅 64 位 Windows 10/11（与 README 的 Windows Requirements 一致）
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; 允许用户在“所有用户 / 当前用户”之间选择，避免强制 UAC
PrivilegesRequiredOverridesAllowed=dialog

; 安装/升级前若程序正在运行则先关闭
CloseApplications=force
CloseApplicationsFilter={#MyAppExeName}

; 产物
OutputDir=dist
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}

; 压缩与外观
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; 文件版本信息
VersionInfoVersion={#MyAppVersion4}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=MIT License

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; 桌面快捷方式（可选，默认勾选）
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; 开始菜单“卸载”快捷方式（可选，默认勾选）
Name: "uninstallicon"; Description: "创建“开始”菜单卸载快捷方式"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 单文件模式：直接打包 dist\FormoraReport.exe
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单（始终创建）
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; 开始菜单卸载入口（可选）
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Tasks: uninstallicon
; 桌面快捷方式（可选）
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后运行（默认勾选，静默安装时不执行）
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent