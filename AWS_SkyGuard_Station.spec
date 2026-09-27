# -*- mode: python ; coding: utf-8 -*-
import os

project_dir = os.path.abspath(SPECPATH) if 'SPECPATH' in locals() else os.path.abspath('.')
app_py = os.path.join(project_dir, 'desktop', 'app.py')
backend_exe = os.path.join(project_dir, 'backend', 'aws-telemetry-backend.exe')
frontend_out = os.path.join(project_dir, 'frontend', 'out')

a = Analysis(
    [app_py],
    pathex=[project_dir],
    binaries=[],
    datas=[(backend_exe, 'backend'), (frontend_out, 'frontend/out')],
    hiddenimports=[
        'clr',
        'clr_loader',
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'webview.platforms.mshtml',
        'json',
        'traceback',
        'winreg',
    ],
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
