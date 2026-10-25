# -*- mode: python ; coding: utf-8 -*-
# onefile 单文件 exe 打包配置：下载一个 FormoraReport.exe 即可运行
#
# 体积优化（相对旧版）：
# 1. 不再 collect_all(pandas/matplotlib/pdfplumber/docxtpl/openpyxl) —— 官方 hook 自动收集：
#    - PyInstaller 内置 hook-matplotlib：收集 mpl-data（字体、stylelib）
#    - _pyinstaller_hooks_contrib hook-pdfminer：收集 pdfminer cmap
#    - _pyinstaller_hooks_contrib hook-tzdata：收集 tzdata（pandas zoneinfo 需要）
#    - _pyinstaller_hooks_contrib hook-openpyxl / hook-win32com：对应数据与依赖
# 2. hiddenimports 跳过 formora.api（FastAPI 服务模块，桌面端不加载）
# 3. excludes 排除 FastAPI 栈（fastapi/starlette/uvicorn/pydantic 及传递依赖）与开发/测试依赖
# 4. 构建后裁剪：a.datas 只保留 zh_CN/en 的 Qt 翻译；a.binaries 剔除
#    opengl32sw.dll/libEGL.dll/libGLESv2.dll/d3compiler_47.dll

import glob
import os

datas = []
binaries = []
hiddenimports = []

_project_root = os.path.dirname(os.path.abspath(SPEC))

# 示例模板与数据随包分发（打包版从 sys._MEIPASS/samples 读取）
datas += [
    (os.path.join(_project_root, 'tests', 'samples', '实验报告模板.docx'), 'samples'),
    (os.path.join(_project_root, 'tests', 'samples', '实验数据.csv'), 'samples'),
]

# 应用本体模块：显式列出 src/formora 下除 api 外的全部模块（api 为 FastAPI 服务，桌面端不用）
_src_modules = []
for _py in glob.glob(os.path.join(_project_root, 'src', 'formora', '**', '*.py'), recursive=True):
    _rel = os.path.relpath(_py, os.path.join(_project_root, 'src')).replace(os.sep, '.')[:-3]
    if _rel == 'formora.api':
        continue  # 跳过 FastAPI 服务模块
    _src_modules.append(_rel)
hiddenimports += _src_modules

# 源码随包分发（不含 api.py 与 __pycache__，避免把 FastAPI 模块和缓存字节码带进产物）
for _root, _dirs, _files in os.walk(os.path.join(_project_root, 'src', 'formora')):
    _dirs[:] = [d for d in _dirs if d != '__pycache__']
    for _f in _files:
        if _f.endswith('.py') and _f != 'api.py':
            _abs = os.path.join(_root, _f)
            _dest = os.path.relpath(os.path.dirname(_abs), os.path.join(_project_root, 'src'))
            datas.append((_abs, _dest))

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # FastAPI / API 服务栈（桌面端核心功能不需要）
        'fastapi',
        'starlette',
        'uvicorn',
        'pydantic',
        'python_multipart',
        'email_validator',
        'orjson',
        'httptools',
        'uvloop',
        'websockets',
        'watchfiles',
        'anyio',
        'sniffio',
        'httpcore',
        'httpx',
        'h11',
        'click',
        # 开发/测试依赖
        'pytest',
        'pytest_cov',
        'coverage',
        'ruff',
        'mypy',
        'IPython',
        'prompt_toolkit',
        'pygments',
        'rich',
        'setuptools',
        'pip',
        # 注意：cryptography 不能排除 —— pdfminer.six 20260107 在 pdfminer/pdfdocument.py
        # 顶层硬导入 cryptography.hazmat（无 try/except 回退），排除会导致 PDF 解析崩溃。
        # 保留后由 pdfminer 导入链自动收集（约 11.9MB，含 cffi/pycparser）。
        # 标准库 GUI 框架（项目用 PySide6）
        'tkinter',
    ],
    noarchive=False,
    optimize=0,
)

# ---- 构建后体积裁剪 ----

# 1) Qt 翻译只保留简体中文与英文
def _keep_qt_translation(_dest):
    _base = os.path.basename(_dest)
    if not _base.endswith('.qm'):
        return True
    _low = _base.lower()
    return _low.endswith('_zh_cn.qm') or _low.endswith('_en.qm')


a.datas = [_d for _d in a.datas if _keep_qt_translation(_d[1])]

# 2) 剔除 Qt 软件渲染/OpenGL 辅助 DLL（桌面 raster/offscreen 渲染不需要）
_BAD_DLLS = {'opengl32sw.dll', 'libegl.dll', 'libglesv2.dll', 'd3compiler_47.dll'}
a.binaries = [_b for _b in a.binaries if os.path.basename(_b[0]).lower() not in _BAD_DLLS]

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
