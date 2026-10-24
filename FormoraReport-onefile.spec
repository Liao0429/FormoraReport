# -*- mode: python ; coding: utf-8 -*-
# onefile 单文件 exe 打包配置：下载一个 FormoraReport.exe 即可运行
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('matplotlib')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('docxtpl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# 示例模板与数据随包分发
import os
_project_root = os.path.abspath(os.getcwd())
datas += [
    (os.path.join(_project_root, 'tests', 'samples', '实验报告模板.docx'), 'samples'),
    (os.path.join(_project_root, 'tests', 'samples', '实验数据.csv'), 'samples'),
]

# 应用本体模块
import glob
_src_modules = []
for _py in glob.glob(os.path.join(_project_root, 'src', 'formora', '**', '*.py'), recursive=True):
    _rel = os.path.relpath(_py, os.path.join(_project_root, 'src')).replace(os.sep, '.')[:-3]
    _src_modules.append(_rel)
hiddenimports += _src_modules

datas += [(os.path.join(_project_root, 'src', 'formora'), 'formora')]

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# onefile：exe 直接包含全部 binaries/datas，不产生 _internal 目录
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FormoraReport',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
