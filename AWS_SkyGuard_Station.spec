# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/SIH73/AWS_SkyGuard_Station/desktop/app.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/SIH73/AWS_SkyGuard_Station/backend/aws-telemetry-backend.exe', 'backend'), ('D:/SIH73/AWS_SkyGuard_Station/frontend/out', 'frontend/out')],
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
    name='AWS_SkyGuard_Station',
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
