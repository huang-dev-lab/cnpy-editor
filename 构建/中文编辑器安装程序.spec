# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:/黄帅钧/编程/中文编辑器_python/源码/安装程序.py'],
    pathex=[],
    binaries=[],
    datas=[('E:/黄帅钧/编程/中文编辑器_python/dist/中文编辑器.exe', 'dist'),
           ('E:/黄帅钧/编程/中文编辑器_python/资源/中文编辑器.ico', '.'),
           ('E:/黄帅钧/编程/中文编辑器_python/源码/卸载中文编辑器.bat', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='中文编辑器安装程序',
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
    icon=['E:/黄帅钧/编程/中文编辑器_python/资源/中文编辑器.ico'],
)
