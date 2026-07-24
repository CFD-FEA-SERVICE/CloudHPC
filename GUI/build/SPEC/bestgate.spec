# -*- mode: python ; coding: utf-8 -*-

# OCC (pythonocc-core / OpenCASCADE) is imported lazily at runtime by the
# CAD tab, and its hundreds of compiled submodules + TK*.dll libraries are
# not fully discoverable by static analysis — collect the whole package
# explicitly so the frozen app ships a working GEO tab.
# Requires building inside a conda env with pythonocc-core installed
# (see .github/workflows/cloudhpc-tools.yml and build/compilation.ps1).
from PyInstaller.utils.hooks import collect_all

occ_datas, occ_binaries, occ_hidden = collect_all('OCC')

block_cipher = None


a = Analysis(['../../src/xmlreader.py'],
             pathex=[],
             binaries=occ_binaries,
             datas=occ_datas,
             hiddenimports=occ_hidden,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='bestgate',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='bestgate')
