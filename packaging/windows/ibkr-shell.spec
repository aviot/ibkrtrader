# PyInstaller spec for a double-clickable Windows GUI build.

import os
from pathlib import Path

ROOT = Path(os.environ['IBKR_SHELL_ROOT']).resolve()
WINDOWS_PACKAGING = ROOT / 'packaging' / 'windows'
ICON = WINDOWS_PACKAGING / 'ibkr-shell.ico'
VERSION_INFO = WINDOWS_PACKAGING / 'version_info.txt'

block_cipher = None


a = Analysis(
    [str(ROOT / 'launch_gui.pyw')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ibkr-shell',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON),
    version=str(VERSION_INFO),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ibkr-shell',
)
