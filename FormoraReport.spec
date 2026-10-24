# -*- mode: python ; coding: utf-8 -*-
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

# 示例模板与数据随包分发，供「使用示例模板体验」按钮使用
# 注意：spec 由 PyInstaller 特殊执行，__file__ 不可用，用当前工作目录定位项目根
import os
_project_root = os.path.abspath(os.getcwd())
datas += [
    (os.path.join(_project_root, 'tests', 'samples', '实验报告模板.docx'), 'samples'),
    (os.path.join(_project_root, 'tests', 'samples', '实验数据.csv'), 'samples'),
]

# 应用本体模块：显式收集 src/formora 下全部模块，确保打进包
import glob
_src_modules = []
for _py in glob.glob(os.path.join(_project_root, 'src', 'formora', '**', '*.py'), recursive=True):
    _rel = os.path.relpath(_py, os.path.join(_project_root, 'src')).replace(os.sep, '.')[:-3]
    _src_modules.append(_rel)
hiddenimports += _src_modules

# 同时把整个 src/formora 目录作为数据打进 _internal/formora，
# 确保运行时 sys.path 指向 _internal 时能 import formora
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FormoraReport',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FormoraReport',
)
