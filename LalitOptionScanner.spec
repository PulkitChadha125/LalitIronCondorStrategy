# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('xtspythonclientapisdk', 'xtspythonclientapisdk'), ('config.ini', '.'), ('Credentials.csv', '.'), ('TradeSettings.csv', '.')]
binaries = []
hiddenimports = ['selenium', 'pyotp', 'flask', 'pandas', 'requests', 'websocket', 'websocket-client', 'python-socketio', 'python-engineio', 'bidict', 'six', 'urllib3', 'certifi', 'chardet', 'idna', 'configparser', 'json', 'logging', 'datetime', 'time', 'traceback', 'sys', 'csv', 'threading', 'queue']
tmp_ret = collect_all('xtspythonclientapisdk')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app.py'],
    pathex=[],
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
    a.binaries,
    a.datas,
    [],
    name='LalitOptionScanner',
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
